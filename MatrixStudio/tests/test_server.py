import asyncio
import base64
import importlib.util
import io
import os
import json
import struct
import av
from pathlib import Path
import tempfile
import unittest

from aiohttp import web, FormData
from PIL import Image
from aiohttp.test_utils import TestClient, TestServer


class StudioTest(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def video_fixture(color, frames=32, fps=8):
        buffer = io.BytesIO()
        with av.open(buffer, mode='w', format='mp4') as container:
            stream = container.add_stream('libx264', rate=fps)
            stream.width = stream.height = 128
            stream.pix_fmt = 'yuv420p'
            for index in range(frames):
                frame = av.VideoFrame.from_image(Image.new('RGB', (128, 128), color))
                frame.pts = index
                for packet in stream.encode(frame):
                    container.mux(packet)
            for packet in stream.encode():
                container.mux(packet)
        return buffer.getvalue()

    async def asyncSetUp(self):
        self.folder = tempfile.TemporaryDirectory()
        previous = os.environ.get('MATRIX_STUDIO_DATA_DIR')
        os.environ['MATRIX_STUDIO_DATA_DIR'] = self.folder.name
        try:
            spec = importlib.util.spec_from_file_location('studio_test', Path(__file__).resolve().parents[1] / 'server.py')
            self.studio = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.studio)
        finally:
            if previous is None:
                os.environ.pop('MATRIX_STUDIO_DATA_DIR')
            else:
                os.environ['MATRIX_STUDIO_DATA_DIR'] = previous
        # Keep unrelated tests away from real local GPU backends.
        self.studio.DB.execute("INSERT OR REPLACE INTO studio_settings (key,value) VALUES ('release_gpu_after_job','0')")
        self.studio.DB.commit()
        self.app = self.studio.create_app()
        self.client = TestClient(TestServer(self.app), headers={'Host': '127.0.0.1:7880'})
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        self.folder.cleanup()

    def stored_action_clip(self, color=(80,80,80), **extra):
        rid, cid = self.studio.uuid.uuid4().hex, self.studio.uuid.uuid4().hex
        params = dict(kind='video',engine='comfy',family='wan14b',profile='fast',adapter='motion_fix',
            action_lora='none',frames=81,fps=16,interpolation=1,width=128,height=128,seed=7,
            steps=4,cfg=1,shift=5,negative='',input_image='fixture.png',preset='sparring',**extra)
        content = self.video_fixture(color,81,16)
        (self.studio.OUTPUT/(rid+'.mp4')).write_bytes(content)
        with self.studio.DB:
            self.studio.DB.execute('INSERT INTO chats (id,title,created) VALUES (?,?,?)',(cid,'Fixture',1))
            self.studio.DB.execute('INSERT INTO renders (id,chat_id,prompt,params,status,detail,image,created) VALUES (?,?,?,?,?,?,?,?)',
                (rid,cid,'Boxing',json.dumps(params),'done','Done','/outputs/'+rid+'.mp4',1))
        return rid,params,content


    async def test_action_continuation_and_assembly_preserve_boundary_and_duration(self):
        rid,params,content = self.stored_action_clip()
        captured=[]
        async def fake_render(app,row,p):
            captured.append(p)
            return content
        self.studio.render_comfy=fake_render
        response=await self.client.post('/api/video/continue',json={'source_id':rid})
        self.assertEqual(response.status,200)
        next_id=(await response.json())['id']
        await asyncio.wait_for(self.app['queue'].join(),timeout=5)
        self.assertEqual(captured[0]['seed'],params['seed']+1)
        self.assertEqual(captured[0]['continuation_of'],rid)
        source=self.studio.last_action_frame(self.studio.OUTPUT/(rid+'.mp4'))
        with Image.open(self.studio.INPUTS/captured[0]['input_image']) as image:
            self.assertEqual(image.convert('RGB').tobytes(),source.tobytes())
        response=await self.client.post('/api/video/assemble',json={'first_id':rid,'second_id':next_id})
        self.assertEqual(response.status,200)
        assembled=await response.json()
        with av.open(str(self.studio.OUTPUT/(assembled['id']+'.mp4'))) as container:
            fps=float(container.streams.video[0].average_rate)
            frames=list(container.decode(video=0))
        self.assertEqual((len(frames),fps),(161,32))
        self.assertGreaterEqual(len(frames)/fps,5)
        row=self.studio.rows('SELECT * FROM renders WHERE id=?',(assembled['id'],))[0]
        meta=json.loads(row['params'])
        self.assertEqual(meta['backend'],'action_edit')
        self.assertEqual(meta['interpolation'],1)
        self.assertEqual(meta['source_ids'],[rid,next_id])


    async def test_action_edit_rejects_missing_source_and_unrelated_reference(self):
        response=await self.client.post('/api/video/continue',json={'source_id':'../invalid'})
        self.assertEqual(response.status,400)
        first,params,content=self.stored_action_clip()
        second,_,_=self.stored_action_clip(continuation_of=first)
        Image.new('RGB',(128,128),'white').save(self.studio.INPUTS/'fixture.png')
        response=await self.client.post('/api/video/assemble',json={'first_id':first,'second_id':second})
        self.assertEqual(response.status,400)
        self.assertEqual(len(self.studio.rows('SELECT * FROM renders')),2)


    async def test_invalid_prompt_does_not_create_chat(self):
        result = await self.client.post('/api/generate', json={'prompt': ' ', 'engine': 'qwen'})
        self.assertEqual(result.status, 400)
        self.assertEqual(await (await self.client.get('/api/chats')).json(), [])

    async def test_remote_origin_and_engine_are_rejected(self):
        result = await self.client.post('/api/settings', json={}, headers={'Origin': 'https://external.example'})
        self.assertEqual(result.status, 403)
        result = await self.client.post('/api/settings', json={'comfy': 'http://external.example', 'automatic': 'http://127.0.0.1:7860'})
        self.assertEqual(result.status, 400)
        self.assertFalse((Path(self.folder.name) / 'engines.json').exists())

    async def test_automatic_job_saves_image_prompt_and_seed(self):
        png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aC9sAAAAASUVORK5CYII=')
        captured = []

        async def txt2img(request):
            captured.append(await request.json())
            return web.json_response({'images': [base64.b64encode(png).decode()]})

        fake = web.Application()
        fake.router.add_post('/sdapi/v1/txt2img', txt2img)
        async with TestServer(fake) as engine:
            self.studio.CONFIG['automatic'] = str(engine.make_url('')).rstrip('/')
            response = await self.client.post('/api/generate', json={'prompt': 'A little green planet', 'engine': 'automatic',
                'model': 'test-model', 'seed': 123, 'steps': 20, 'cfg': 7})
            self.assertEqual(response.status, 200)
            job = await response.json()
            await asyncio.wait_for(self.app['queue'].join(), timeout=5)
            render = (await (await self.client.get('/api/renders?chat=' + job['chat'])).json())[0]
            self.assertEqual(render['status'], 'done')
            self.assertEqual(render['params']['seed'], 123)
            self.assertEqual(render['prompt'], 'A little green planet')
            self.assertEqual(captured[0]['cfg_scale'], 7)
            self.assertEqual(captured[0]['override_settings']['sd_model_checkpoint'], 'test-model')
            downloaded = await self.client.get(render['image'])
            self.assertEqual(await downloaded.read(), png)
            self.assertEqual(len(await (await self.client.get('/api/chats')).json()), 1)

    async def test_engine_failure_keeps_prompt_for_retry(self):
        async def fail(*args):
            raise ValueError('Motor no disponible')
        self.studio.render_qwen = fail
        response = await self.client.post('/api/generate', json={'prompt': 'A forest', 'engine': 'qwen'})
        job = await response.json()
        await asyncio.wait_for(self.app['queue'].join(), timeout=3)
        render = (await (await self.client.get('/api/renders?chat=' + job['chat'])).json())[0]
        self.assertEqual(render['status'], 'error')
        self.assertEqual(render['detail'], 'Motor no disponible')
        self.assertEqual(render['prompt'], 'A forest')

    async def test_comfy_image_metadata_is_not_sent_as_query_parameters(self):
        sockets = []

        async def websocket(request):
            ws = web.WebSocketResponse()
            await ws.prepare(request)
            sockets.append(ws)
            async for _ in ws:
                pass
            return ws

        async def prompt(request):
            await sockets[0].send_json({'type': 'executing', 'data': {'prompt_id': 'test-prompt', 'node': None}})
            return web.json_response({'prompt_id': 'test-prompt'})

        async def history(request):
            return web.json_response({'test-prompt': {'outputs': {'7': {'images': [{
                'filename': 'image.png', 'subfolder': 'MatrixStudio', 'type': 'output',
                'metadata': {'kind': 'image', 'width': 512, 'height': 512}}]}}}})

        async def view(request):
            self.assertEqual(dict(request.query), {'filename': 'image.png', 'subfolder': 'MatrixStudio', 'type': 'output'})
            return web.Response(body=b'generated-image', content_type='image/png')

        fake = web.Application()
        fake.router.add_get('/ws', websocket)
        fake.router.add_post('/prompt', prompt)
        fake.router.add_get('/history/test-prompt', history)
        fake.router.add_get('/view', view)
        async with TestServer(fake) as engine:
            self.studio.CONFIG['comfy'] = str(engine.make_url('')).rstrip('/')
            response = await self.client.post('/api/generate', json={'prompt': 'A valley', 'engine': 'comfy', 'model': 'sdxl'})
            job = await response.json()
            await asyncio.wait_for(self.app['queue'].join(), timeout=5)
            render = (await (await self.client.get('/api/renders?chat=' + job['chat'])).json())[0]
            self.assertEqual(render['status'], 'done')
            self.assertEqual(await (await self.client.get(render['image'])).read(), b'generated-image')

    async def test_delete_and_undo_preserve_chat_and_image_independently(self):
        async def render(*args):
            return b'image-to-restore'
        self.studio.render_qwen = render
        job = await (await self.client.post('/api/generate', json={'prompt': 'A forest', 'engine': 'qwen'})).json()
        await asyncio.wait_for(self.app['queue'].join(), timeout=3)
        image = self.studio.OUTPUT / (job['id'] + '.png')
        self.assertTrue(image.exists())
        self.assertEqual((await self.client.post(f"/api/renders/{job['id']}/delete", json={})).status, 200)
        self.assertFalse(image.exists())
        self.assertEqual(await (await self.client.get('/api/renders')).json(), [])
        chat = await (await self.client.get('/api/renders?chat=' + job['chat'])).json()
        self.assertEqual(chat[0]['status'], 'deleted')
        self.assertIsNone(chat[0]['image'])
        self.assertEqual((await self.client.post(f"/api/renders/{job['id']}/restore", json={})).status, 200)
        self.assertEqual(image.read_bytes(), b'image-to-restore')
        self.assertEqual((await self.client.post(f"/api/chats/{job['chat']}/delete", json={})).status, 200)
        self.assertEqual(await (await self.client.get('/api/chats')).json(), [])
        self.assertEqual(len(await (await self.client.get('/api/renders')).json()), 1)
        self.assertEqual((await self.client.post(f"/api/chats/{job['chat']}/restore", json={})).status, 200)
        self.assertEqual(len(await (await self.client.get('/api/chats')).json()), 1)

    async def test_chat_cannot_be_deleted_during_generation(self):
        started, finish = asyncio.Event(), asyncio.Event()
        async def render(*args):
            started.set()
            await finish.wait()
            return b'image'
        self.studio.render_qwen = render
        job = await (await self.client.post('/api/generate', json={'prompt': 'A forest', 'engine': 'qwen'})).json()
        await asyncio.wait_for(started.wait(), timeout=3)
        try:
            result = await self.client.post(f"/api/chats/{job['chat']}/delete", json={})
            self.assertEqual(result.status, 409)
            self.assertEqual(len(await (await self.client.get('/api/chats')).json()), 1)
        finally:
            finish.set()
            await asyncio.wait_for(self.app['queue'].join(), timeout=3)

    async def test_variations_have_distinct_seeds_and_continue_after_one_failure(self):
        seen = []
        active = 0
        async def render(app, row, params):
            nonlocal active
            active += 1
            self.assertEqual(active, 1)
            seen.append(params['seed'])
            await asyncio.sleep(0)
            active -= 1
            if params['seed'] == 0:
                raise ValueError('Un fallo en una variación')
            return b'variation'
        self.studio.render_qwen = render
        response = await self.client.post('/api/generate', json={'prompt': 'A forest', 'engine': 'qwen', 'count': 3, 'seed': 2147483647})
        self.assertEqual(response.status, 200)
        batch = await response.json()
        await asyncio.wait_for(self.app['queue'].join(), timeout=3)
        renders = await (await self.client.get('/api/renders?chat=' + batch['chat'])).json()
        self.assertEqual(seen, [2147483647, 0, 1])
        self.assertEqual([r['id'] for r in renders], batch['ids'])
        self.assertEqual([r['status'] for r in renders], ['done', 'error', 'done'])
        self.assertTrue(all(r['prompt'] == 'A forest' for r in renders))
        self.assertEqual(len(await (await self.client.get('/api/chats')).json()), 1)

    async def test_invalid_variation_count_does_not_create_jobs(self):
        for count in (0, 9, 2.5, True):
            response = await self.client.post('/api/generate', json={'prompt': 'A forest', 'engine': 'qwen', 'count': count})
            self.assertEqual(response.status, 400)
        self.assertEqual(await (await self.client.get('/api/chats')).json(), [])

    async def test_local_video_upload_generation_download_and_undo(self):
        self.studio.ROOT = Path(self.folder.name)
        for model in self.studio.WAN_MODELS:
            target = self.studio.ROOT / 'Data/Models' / model['folder'] / Path(model['file']).name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b'test-model')
        sockets, graphs = [], []
        async def websocket(request):
            ws = web.WebSocketResponse()
            await ws.prepare(request)
            sockets.append(ws)
            async for _ in ws:
                pass
            return ws
        async def upload(request):
            part = await (await request.multipart()).next()
            self.assertEqual(part.name, 'image')
            self.assertTrue((await part.read()).startswith(b'\x89PNG'))
            return web.json_response({'name': 'local-input.png', 'subfolder': ''})
        async def prompt(request):
            graphs.append((await request.json())['prompt'])
            await sockets[0].send_json({'type': 'executing', 'data': {'prompt_id': 'video-test', 'node': None}})
            return web.json_response({'prompt_id': 'video-test'})
        async def history(request):
            return web.json_response({'video-test': {'outputs': {'save': {'images': [{'filename': 'movie.mp4', 'subfolder': 'MatrixStudio', 'type': 'output'}]}}}})
        async def view(request):
            return web.Response(body=b'local-mp4', content_type='video/mp4')
        fake = web.Application()
        fake.router.add_get('/ws', websocket)
        fake.router.add_post('/upload/image', upload)
        fake.router.add_post('/prompt', prompt)
        fake.router.add_get('/history/video-test', history)
        fake.router.add_get('/view', view)
        image = io.BytesIO()
        Image.new('RGB', (32, 32), 'green').save(image, format='PNG')
        form = FormData()
        form.add_field('image', image.getvalue(), filename='input.png', content_type='image/png')
        source = await (await self.client.post('/api/video/input', data=form)).json()
        async with TestServer(fake) as engine:
            self.studio.CONFIG['comfy'] = str(engine.make_url('')).rstrip('/')
            response = await self.client.post('/api/video/generate', json={'input_image': source['name'], 'prompt': 'The leaves move in the wind', 'width': 256, 'height': 256, 'frames': 9})
            self.assertEqual(response.status, 200)
            job = await response.json()
            await asyncio.wait_for(self.app['queue'].join(), timeout=5)
            render = (await (await self.client.get('/api/renders?chat=' + job['chat'])).json())[0]
            self.assertEqual(render['status'], 'done')
            self.assertEqual(render['params']['kind'], 'video')
            self.assertTrue(render['image'].endswith('.mp4'))
            self.assertEqual(await (await self.client.get(render['image'])).read(), b'local-mp4')
            self.assertEqual(graphs[0]['conditioning']['inputs']['length'], 9)
            self.assertEqual(graphs[0]['save']['inputs']['format.codec'], 'h264')
            self.assertEqual(graphs[0]['low_sample']['inputs']['add_noise'], 'disable')
            await self.client.post(f"/api/renders/{job['id']}/delete", json={})
            self.assertFalse((self.studio.OUTPUT / (job['id'] + '.mp4')).exists())
            await self.client.post(f"/api/renders/{job['id']}/restore", json={})
            self.assertEqual((self.studio.OUTPUT / (job['id'] + '.mp4')).read_bytes(), b'local-mp4')

    async def test_video_does_not_accept_arbitrary_local_paths(self):
        response = await self.client.post('/api/video/generate', json={'input_image': '../studio.db', 'prompt': 'Move slowly'})
        self.assertEqual(response.status, 400)
        self.assertEqual(await (await self.client.get('/api/chats')).json(), [])

    async def test_mesh_preserves_alpha_fetches_glb_and_supports_delete_undo(self):
        self.studio.ROOT = Path(self.folder.name)
        for model in self.studio.TRELLIS_MODELS:
            target = self.studio.ROOT / 'Data/Models' / model['folder'] / Path(model['file']).name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b'test-model')
        sockets, graphs = [], []
        async def websocket(request):
            ws = web.WebSocketResponse()
            await ws.prepare(request)
            sockets.append(ws)
            async for _ in ws:
                pass
            return ws
        async def upload(request):
            part = await (await request.multipart()).next()
            with Image.open(io.BytesIO(await part.read())) as image:
                self.assertEqual(image.mode, 'RGBA')
                self.assertEqual(image.getpixel((0, 0))[3], 80)
            return web.json_response({'name': 'object.png', 'subfolder': ''})
        async def prompt(request):
            graphs.append((await request.json())['prompt'])
            await sockets[0].send_json({'type': 'execution_success', 'data': {'prompt_id': 'mesh-test'}})
            return web.json_response({'prompt_id': 'mesh-test'})
        async def history(request):
            return web.json_response({'mesh-test': {'outputs': {'save': {
                'images': [{'filename': 'preview.png', 'type': 'output'}],
                '3d': [{'filename': 'object.glb', 'subfolder': '3d', 'type': 'output'}]}}}})
        async def view(request):
            self.assertEqual(request.query['filename'], 'object.glb')
            return web.Response(body=b'glTF-test-model', content_type='model/gltf-binary')
        fake = web.Application()
        fake.router.add_get('/ws', websocket)
        fake.router.add_post('/upload/image', upload)
        fake.router.add_post('/prompt', prompt)
        fake.router.add_get('/history/mesh-test', history)
        fake.router.add_get('/view', view)
        image = io.BytesIO()
        Image.new('RGBA', (32, 32), (0, 150, 0, 80)).save(image, format='PNG')
        form = FormData()
        form.add_field('image', image.getvalue(), filename='input.png', content_type='image/png')
        source = await (await self.client.post('/api/3d/input', data=form)).json()
        async with TestServer(fake) as engine:
            self.studio.CONFIG['comfy'] = str(engine.make_url('')).rstrip('/')
            response = await self.client.post('/api/3d/generate', json={'input_image': source['name'], 'name': 'My object', 'mode': 'color', 'steps': 8})
            self.assertEqual(response.status, 200)
            job = await response.json()
            await asyncio.wait_for(self.app['queue'].join(), timeout=5)
            render = (await (await self.client.get('/api/renders?chat=' + job['chat'])).json())[0]
            self.assertEqual(render['status'], 'done')
            self.assertEqual(render['params']['kind'], 'mesh')
            self.assertTrue(render['image'].endswith('.glb'))
            self.assertEqual(await (await self.client.get(render['image'])).read(), b'glTF-test-model')
            self.assertEqual(graphs[0]['save']['class_type'], 'SaveGLB')
            self.assertEqual(graphs[0]['material']['class_type'], 'PaintMesh')
            await self.client.post(f"/api/renders/{job['id']}/delete", json={})
            self.assertFalse((self.studio.OUTPUT / (job['id'] + '.glb')).exists())
            await self.client.post(f"/api/renders/{job['id']}/restore", json={})
            self.assertEqual((self.studio.OUTPUT / (job['id'] + '.glb')).read_bytes(), b'glTF-test-model')

    async def test_mesh_rejects_paths_outside_reference_images(self):
        response = await self.client.post('/api/3d/generate', json={'input_image': '../studio.db'})
        self.assertEqual(response.status, 400)
        self.assertEqual(await (await self.client.get('/api/chats')).json(), [])

    def write_checkpoint(self, name, channels):
        folder = self.studio.ROOT / 'Data/Models/StableDiffusion'
        folder.mkdir(parents=True, exist_ok=True)
        header = json.dumps({'model.diffusion_model.input_blocks.1.1.transformer_blocks.0.attn2.to_k.weight':
            {'shape': [320, channels], 'dtype': 'F16', 'data_offsets': [0, 0]}}).encode()
        (folder / name).write_bytes(struct.pack('<Q', len(header)) + header)

    async def test_animatediff_only_accepts_sd15_checkpoints(self):
        self.studio.ROOT = Path(self.folder.name)
        self.write_checkpoint('sd15.safetensors', 768)
        self.write_checkpoint('sdxl.safetensors', 2048)
        self.assertEqual(self.studio.sd15_checkpoints(), ['sd15.safetensors'])
        response = await self.client.post('/api/animatediff/generate', json={'prompt': 'A robot walks', 'model': 'sdxl.safetensors'})
        self.assertEqual(response.status, 400)
        self.assertEqual(await (await self.client.get('/api/chats')).json(), [])

    async def test_animatediff_text_and_reference_use_motion_module_and_distinct_latent_paths(self):
        self.studio.ROOT = Path(self.folder.name)
        self.write_checkpoint('sd15.safetensors', 768)
        motion = self.studio.ROOT / 'Data/Models/AnimateDiff' / self.studio.ANIMATEDIFF_NAMES['motion']
        motion.parent.mkdir(parents=True)
        motion.write_bytes(b'test-motion')
        sockets, graphs = [], []
        async def websocket(request):
            ws = web.WebSocketResponse()
            await ws.prepare(request)
            sockets.append(ws)
            async for _ in ws:
                pass
            return ws
        async def upload(request):
            part = await (await request.multipart()).next()
            self.assertTrue((await part.read()).startswith(b'\x89PNG'))
            return web.json_response({'name': 'reference.png', 'subfolder': ''})
        async def prompt(request):
            graphs.append((await request.json())['prompt'])
            await sockets[-1].send_json({'type': 'execution_success', 'data': {'prompt_id': 'ad-test'}})
            return web.json_response({'prompt_id': 'ad-test'})
        history_reads = 0
        async def history(request):
            nonlocal history_reads
            history_reads += 1
            if history_reads == 1:
                return web.json_response({})
            return web.json_response({'ad-test': {'outputs': {'save': {'images': [{'filename': 'animation.mp4', 'type': 'output'}]}}}})
        async def view(request):
            return web.Response(body=b'animatediff-mp4', content_type='video/mp4')
        fake = web.Application()
        fake.router.add_get('/ws', websocket)
        fake.router.add_post('/upload/image', upload)
        fake.router.add_post('/prompt', prompt)
        fake.router.add_get('/history/ad-test', history)
        fake.router.add_get('/view', view)
        async with TestServer(fake) as engine:
            self.studio.CONFIG['comfy'] = str(engine.make_url('')).rstrip('/')
            payload = {'prompt': 'A robot walks', 'model': 'sd15.safetensors', 'frames': 8, 'seed': 123, 'denoise': 0.55}
            response = await self.client.post('/api/animatediff/generate', json=payload)
            self.assertEqual(response.status, 200)
            text_job = await response.json()
            await asyncio.wait_for(self.app['queue'].join(), timeout=5)
            text_render = (await (await self.client.get('/api/renders?chat=' + text_job['chat'])).json())[0]
            self.assertEqual(text_render['status'], 'done')
            self.assertEqual(text_render['params']['backend'], 'animatediff')
            self.assertEqual(graphs[0]['motion']['class_type'], 'ADE_AnimateDiffLoaderGen1')
            self.assertEqual(graphs[0]['latent']['class_type'], 'EmptyLatentImage')
            self.assertEqual(graphs[0]['latent']['inputs']['batch_size'], 8)
            self.assertEqual(graphs[0]['sample']['inputs']['denoise'], 1.0)
            self.assertEqual(await (await self.client.get(text_render['image'])).read(), b'animatediff-mp4')
            image = io.BytesIO()
            Image.new('RGB', (32, 32), 'green').save(image, format='PNG')
            form = FormData()
            form.add_field('image', image.getvalue(), filename='reference.png', content_type='image/png')
            source = await (await self.client.post('/api/animatediff/input', data=form)).json()
            response = await self.client.post('/api/animatediff/generate', json={**payload, 'input_image': source['name']})
            self.assertEqual(response.status, 200)
            await asyncio.wait_for(self.app['queue'].join(), timeout=5)
            self.assertEqual(graphs[1]['latent']['class_type'], 'RepeatLatentBatch')
            self.assertEqual(graphs[1]['latent']['inputs']['amount'], 8)
            self.assertEqual(graphs[1]['sample']['inputs']['denoise'], 0.55)

    async def test_animatediff_camera_lora_requires_installed_v2_and_preserves_settings(self):
        self.studio.ROOT = Path(self.folder.name)
        self.write_checkpoint('sd15.safetensors', 768)
        for model in self.studio.ANIMATEDIFF_MODELS:
            if 'checkpoint' in model['key']:
                continue
            target = self.studio.ROOT / 'Data/Models' / model['folder'] / Path(model['file']).name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b'weights')
        graphs = []
        async def render(app, row, params):
            graphs.append(self.studio.animatediff_workflow(params, row['prompt']))
            return b'camera-video'
        self.studio.render_comfy = render
        payload = {'prompt': 'Two athletes sparring', 'model': 'sd15.safetensors',
                   'motion_model': self.studio.ANIMATEDIFF_NAMES['motion_v2'],
                   'motion_lora': self.studio.ANIMATEDIFF_NAMES['camera_zoom_out'],
                   'motion_lora_strength': 0.25, 'motion_scale': 0.85,
                   'interpolation': 3,
                   'sampler': 'dpmpp_2m', 'scheduler': 'karras'}
        response = await self.client.post('/api/animatediff/generate', json=payload)
        self.assertEqual(response.status, 200)
        await asyncio.wait_for(self.app['queue'].join(), timeout=5)
        self.assertEqual(graphs[0]['camera_lora']['inputs']['strength'], 0.25)
        self.assertEqual(graphs[0]['motion']['inputs']['motion_lora'], ['camera_lora', 0])
        self.assertEqual(graphs[0]['motion_scale']['inputs']['float_val'], 0.85)
        self.assertEqual(graphs[0]['sample']['inputs']['sampler_name'], 'dpmpp_2m')
        self.assertEqual(graphs[0]['sample']['inputs']['scheduler'], 'karras')
        self.assertEqual(graphs[0]['interpolate']['inputs']['multiplier'], 3)
        self.assertEqual(graphs[0]['video']['inputs']['images'], ['interpolate', 0])
        self.assertEqual(graphs[0]['video']['inputs']['fps'], 24)
        before = len(await (await self.client.get('/api/chats')).json())
        for invalid in ({'motion_model': self.studio.ANIMATEDIFF_NAMES['motion']},
                        {'motion_lora': '../outside.ckpt'}, {'motion_lora_strength': 1.1},
                        {'motion_scale': 0.1}, {'sampler': 'unknown'}, {'interpolation': 4}, {'interpolation': True}):
            response = await self.client.post('/api/animatediff/generate', json={**payload, **invalid})
            self.assertEqual(response.status, 400)
        self.assertEqual(len(await (await self.client.get('/api/chats')).json()), before)

    async def test_realistic_vision_requires_and_routes_its_vae_for_text_and_reference(self):
        self.studio.ROOT = Path(self.folder.name)
        name = self.studio.ANIMATEDIFF_NAMES['realistic_checkpoint']
        self.write_checkpoint(name, 768)
        payload = {'prompt': 'Two athletes sparring', 'model': name}
        response = await self.client.post('/api/animatediff/generate', json=payload)
        self.assertEqual(response.status, 400)
        for key, folder in (('motion', 'AnimateDiff'), ('realistic_vae', 'VAE')):
            target = self.studio.ROOT / 'Data/Models' / folder / self.studio.ANIMATEDIFF_NAMES[key]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b'weights')
        graphs = []
        async def render(app, row, params):
            for image in (None, 'reference.png'):
                graphs.append(self.studio.animatediff_workflow(params, row['prompt'], image))
            return b'video'
        self.studio.render_comfy = render
        response = await self.client.post('/api/animatediff/generate', json={'prompt': payload['prompt']})
        self.assertEqual(response.status, 200)
        await asyncio.wait_for(self.app['queue'].join(), timeout=5)
        self.assertEqual(graphs[0]['checkpoint']['inputs']['ckpt_name'], name)
        self.assertEqual(graphs[0]['vae']['inputs']['vae_name'], self.studio.ANIMATEDIFF_NAMES['realistic_vae'])
        self.assertEqual(graphs[0]['decode']['inputs']['vae'], ['vae', 0])
        self.assertEqual(graphs[1]['encode']['inputs']['vae'], ['vae', 0])

    async def test_montage_120_seconds_encodes_exact_duration_and_distinct_scenes(self):
        self.studio.ROOT = Path(self.folder.name)
        self.write_checkpoint('sd15.safetensors', 768)
        motion = self.studio.ROOT / 'Data/Models/AnimateDiff' / self.studio.ANIMATEDIFF_NAMES['motion']
        motion.parent.mkdir(parents=True)
        motion.write_bytes(b'motion')
        fixtures = [self.video_fixture('red'), self.video_fixture('blue')]
        seen = []
        async def render(app, row, params):
            seen.append((params['seed'], row['prompt']))
            graph = self.studio.animatediff_workflow(params, row['prompt'])
            self.assertEqual(graph['noise']['inputs']['noise_type'], 'FreeNoise')
            self.assertEqual(graph['context']['inputs']['context_overlap'], 8)
            return fixtures[(params['seed'] - 100) % 2]
        self.studio.render_comfy = render
        response = await self.client.post('/api/animatediff/generate', json={
            'prompt': 'Two athletes', 'model': 'sd15.safetensors', 'width': 128, 'height': 128,
            'frames': 32, 'fps': 8, 'interpolation': 1, 'seed': 100,
            'duration_seconds': 120, 'count': 2, 'scene_prompts': ['They raise their guard.', 'They exchange a punch.']})
        self.assertEqual(response.status, 200)
        job = await response.json()
        await asyncio.wait_for(self.app['queue'].join(), timeout=30)
        results = await (await self.client.get('/api/renders?chat=' + job['chat'])).json()
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r['status'] == 'done' for r in results))
        result = results[0]
        self.assertEqual(result['status'], 'done', result['detail'])
        self.assertEqual([seed for seed, _ in seen], list(range(100, 160)))
        self.assertIn('raise their guard', seen[0][1])
        self.assertIn('exchange a punch', seen[1][1])
        with av.open(str(self.studio.OUTPUT / (job['id'] + '.mp4'))) as video:
            self.assertEqual(float(video.streams.video[0].average_rate), 8)
            frames = list(video.decode(video=0))
        self.assertEqual(len(frames), 960)
        self.assertGreater(frames[0].to_image().getpixel((64, 64))[0], 200)
        self.assertGreater(frames[32].to_image().getpixel((64, 64))[2], 200)
        self.assertEqual(result['params']['segment_count'], 30)
        with av.open(str(self.studio.OUTPUT / (job['ids'][1] + '.mp4'))) as video:
            self.assertEqual(sum(1 for _ in video.decode(video=0)), 960)

    async def test_montage_resume_reuses_completed_scene_and_rejects_invalid_duration(self):
        self.studio.ROOT = Path(self.folder.name)
        self.write_checkpoint('sd15.safetensors', 768)
        motion = self.studio.ROOT / 'Data/Models/AnimateDiff' / self.studio.ANIMATEDIFF_NAMES['motion']
        motion.parent.mkdir(parents=True)
        motion.write_bytes(b'motion')
        fixture = self.video_fixture('green')
        calls = []
        async def render(app, row, params):
            calls.append(params['seed'])
            if calls == [5, 6]:
                raise ValueError('Engine stopped')
            return fixture
        self.studio.render_comfy = render
        payload = {'prompt': 'Athletes', 'model': 'sd15.safetensors', 'width': 128, 'height': 128,
                   'frames': 32, 'fps': 8, 'interpolation': 1, 'seed': 5, 'duration_seconds': 8}
        for invalid in (-1, 121, 2.5, True):
            response = await self.client.post('/api/animatediff/generate', json={**payload, 'duration_seconds': invalid})
            self.assertEqual(response.status, 400)
        response = await self.client.post('/api/animatediff/generate', json={**payload, 'scene_prompts': ['x' * 2001]})
        self.assertEqual(response.status, 400)
        self.assertEqual(await (await self.client.get('/api/chats')).json(), [])
        job = await (await self.client.post('/api/animatediff/generate', json=payload)).json()
        await asyncio.wait_for(self.app['queue'].join(), timeout=10)
        failed = (await (await self.client.get('/api/renders?chat=' + job['chat'])).json())[0]
        self.assertEqual(failed['status'], 'error')
        self.assertTrue((self.studio.VIDEO_PROJECTS / job['id'] / '001.mp4').is_file())
        self.assertEqual((await self.client.post('/api/renders/' + job['id'] + '/resume', json={})).status, 200)
        await asyncio.wait_for(self.app['queue'].join(), timeout=10)
        done = (await (await self.client.get('/api/renders?chat=' + job['chat'])).json())[0]
        self.assertEqual(done['status'], 'done', done['detail'])
        self.assertEqual(calls, [5, 6, 6])
        self.assertEqual((await self.client.post('/api/renders/' + job['id'] + '/resume', json={})).status, 400)

    def test_wan_quality_profiles_and_5b_use_matching_models_and_samplers(self):
        p = {'width': 640, 'height': 384, 'frames': 81, 'fps': 16, 'seed': 1,
             'negative': '', 'steps': 40, 'cfg': 3.5, 'shift': 3.0, 'profile': 'quality'}
        graph = self.studio.video_workflow(p, 'Athletes sparring', 'reference.png')
        self.assertNotIn('high_lora', graph)
        self.assertEqual(graph['high_sample']['inputs']['end_at_step'], 10)
        self.assertEqual(graph['low_sample']['inputs']['start_at_step'], 10)
        self.assertEqual(graph['low_sample']['inputs']['end_at_step'], 40)
        self.assertEqual(graph['high_sample']['inputs']['cfg'], 3.5)
        self.assertEqual(graph['high_sample']['inputs']['sampler_name'], 'uni_pc')
        fast = self.studio.video_workflow({**p, 'profile': 'fast', 'steps': 4, 'cfg': 1, 'shift': 5}, 'Athletes', 'reference.png')
        self.assertIn('high_lora', fast)
        self.assertEqual(fast['high_sample']['inputs']['sampler_name'], 'euler')
        self.assertEqual(fast['low_sample']['inputs']['sampler_name'], 'euler')
        self.assertEqual(fast['high_sample']['inputs']['end_at_step'], 2)
        native = self.studio.video_workflow({**p, 'family': 'wan5b', 'fps': 24, 'cfg': 5, 'shift': 8, 'steps': 20}, 'Athletes', 'reference.png')
        self.assertEqual(native['latent']['class_type'], 'Wan22ImageToVideoLatent')
        self.assertEqual(native['vae']['inputs']['vae_name'], self.studio.WAN5B_NAMES['vae'])
        self.assertEqual(native['shift']['inputs']['shift'], 8)
        self.assertEqual(native['sample']['inputs']['cfg'], 5)
        self.assertEqual(native['sample']['inputs']['steps'], 20)
        self.assertEqual(native['video']['inputs']['fps'], 24)

    async def test_video_status_does_not_require_acceleration_loras_for_native_profile(self):
        self.studio.ROOT = Path(self.folder.name)
        for model in self.studio.WAN_MODELS:
            if model['key'].startswith('lora_'):
                continue
            target = self.studio.ROOT / 'Data/Models' / model['folder'] / Path(model['file']).name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b'model')
        status = await (await self.client.get('/api/video/status')).json()
        family = next(f for f in status['families'] if f['id'] == 'wan14b')
        self.assertTrue(family['ready'])
        self.assertFalse(family['fast_ready'])
        native = next(p for p in status['presets'] if p['id'] == 'action_native')
        self.assertTrue(native['ready'])
        motion = next(p for p in status['presets'] if p['id'] == 'action_motion')
        self.assertFalse(motion['ready'])


    def test_wan_rife_keeps_base_frames_and_at_least_five_seconds(self):
        for family, frames, fps in (('wan14b', 81, 16), ('wan5b', 121, 24)):
            p = {'family': family, 'profile': 'fast', 'width': 256, 'height': 256,
                 'frames': frames, 'fps': fps, 'steps': 4, 'cfg': 1, 'shift': 5,
                 'negative': '', 'seed': 1, 'interpolation': 2}
            graph = self.studio.video_workflow(p, 'Boxing', 'reference.png')
            self.assertEqual(graph['interpolate']['class_type'], 'FrameInterpolate')
            self.assertEqual(graph['interpolate']['inputs']['multiplier'], 2)
            self.assertEqual(graph['video']['inputs']['images'], ['interpolate', 0])
            self.assertEqual(graph['video']['inputs']['fps'], fps * 2)
            latent = graph['latent'] if family == 'wan5b' else graph['conditioning']
            self.assertEqual(latent['inputs']['length'], frames)
            self.assertGreaterEqual(((frames - 1) * 2 + 1) / (fps * 2), 5)


    def test_action_presets_use_matching_experts_and_vae(self):
        from action_profiles import PRESETS, NAMES, prepare_action, validate_adapters
        for preset in PRESETS:
            data = prepare_action({'preset': preset['id']})
            p = {**data, 'negative': '', 'seed': 1, 'fps': 24 if data['family'] == 'wan5b' else 16}
            validate_adapters(p)
            graph = self.studio.video_workflow(p, data['prompt'], 'reference.png')
            if p['width'] * p['height'] > 512 * 512:
                self.assertEqual(graph['decode']['class_type'], 'VAEDecodeTiled')
                self.assertGreaterEqual(graph['decode']['inputs']['temporal_size'] // 4, (p['frames'] - 1) // 4 + 1)
            else:
                self.assertEqual(graph['decode']['class_type'], 'VAEDecode')
                self.assertNotIn('temporal_size', graph['decode']['inputs'])
            if data['family'] == 'wan5b':
                self.assertEqual(graph['vae']['inputs']['vae_name'], self.studio.WAN5B_NAMES['vae'])
                self.assertEqual(graph['action_lora']['inputs']['lora_name'], NAMES['punch'])
                self.assertEqual(graph['shift']['inputs']['model'], ['action_lora', 0])
            else:
                self.assertEqual(graph['vae']['inputs']['vae_name'], self.studio.WAN_NAMES['vae'])
                if data['adapter'] == 'motion_fix':
                    for phase in ('high', 'low'):
                        self.assertEqual(graph[phase + '_lora']['inputs']['lora_name'], NAMES['motion_fix_' + phase])
                if data['action_lora'] == 'kungfu':
                    for phase in ('high', 'low'):
                        self.assertEqual(graph[phase + '_action']['inputs']['lora_name'], NAMES['kungfu_' + phase])
                        self.assertEqual(graph[phase + '_action']['inputs']['model'], [phase + '_lora', 0])


    async def test_action_presets_reject_unknown_or_mismatched_family(self):
        for payload in ({'preset': 'not-a-preset'}, {'preset': 'punch', 'family': 'wan14b'}):
            response = await self.client.post('/api/video/generate', json=payload)
            self.assertEqual(response.status, 400)
        self.assertEqual(await (await self.client.get('/api/chats')).json(), [])


    def test_action_adapters_reject_cross_architecture_or_invalid_strength(self):
        from action_profiles import validate_adapters
        for params in (
            {'family': 'wan14b', 'profile': 'fast', 'action_lora': 'punch'},
            {'family': 'wan5b', 'profile': 'balanced', 'action_lora': 'kungfu'},
            {'family': 'wan14b', 'profile': 'balanced', 'adapter': 'motion_fix'},
            {'family': 'wan14b', 'profile': 'fast', 'action_strength': float('nan')},
            {'family': 'wan14b', 'profile': 'fast', 'action_lora': '../arbitrary.safetensors'},
        ):
            with self.assertRaises(ValueError):
                validate_adapters(params)


    async def test_wan_and_animatediff_batch_videos_have_unique_seeds_and_shared_chat(self):
        self.studio.ROOT = Path(self.folder.name)
        self.write_checkpoint('sd15.safetensors', 768)
        for model in self.studio.WAN_MODELS + self.studio.ANIMATEDIFF_MODELS:
            if model['key'] == 'checkpoint':
                continue
            target = self.studio.ROOT / 'Data/Models' / model['folder'] / Path(model['file']).name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b'model')
        async def render(app, row, params):
            return b'mp4-variation'
        self.studio.render_comfy = render
        image = io.BytesIO()
        Image.new('RGB', (32, 32), 'green').save(image, format='PNG')
        form = FormData()
        form.add_field('image', image.getvalue(), filename='reference.png', content_type='image/png')
        source = await (await self.client.post('/api/video/input', data=form)).json()
        for endpoint in ('video/generate', 'animatediff/generate'):
            payload = {'prompt': 'A leaf moving in the wind', 'input_image': source['name'], 'model': 'sd15.safetensors', 'count': 5, 'seed': 2147483647}
            response = await self.client.post('/api/' + endpoint, json=payload)
            self.assertEqual(response.status, 200)
            batch = await response.json()
            await asyncio.wait_for(self.app['queue'].join(), timeout=5)
            renders = await (await self.client.get('/api/renders?chat=' + batch['chat'])).json()
            self.assertEqual(len(renders), 5)
            self.assertEqual(batch['count'], 5)
            self.assertEqual([r['id'] for r in renders], batch['ids'])
            self.assertEqual([r['params']['seed'] for r in renders], [2147483647, 0, 1, 2, 3])
            self.assertEqual([r['params']['batch_index'] for r in renders], [1, 2, 3, 4, 5])
            self.assertTrue(all(r['status'] == 'done' and r['image'].endswith('.mp4') for r in renders))
        before = len(await (await self.client.get('/api/chats')).json())
        for count in (0, 6, 2.5, True):
            response = await self.client.post('/api/animatediff/generate', json={**payload, 'count': count})
            self.assertEqual(response.status, 400)
        self.assertEqual(len(await (await self.client.get('/api/chats')).json()), before)


if __name__ == '__main__':
    unittest.main()
