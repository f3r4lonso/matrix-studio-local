import asyncio
import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import av
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
import test_server


class QueueControlTest(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = test_server.StudioTest.asyncSetUp
    asyncTearDown = test_server.StudioTest.asyncTearDown
    video_fixture = staticmethod(test_server.StudioTest.video_fixture)

    async def until(self, predicate):
        async with asyncio.timeout(5):
            while not predicate():
                await asyncio.sleep(0.01)

    async def generate(self, count=1, engine='comfy', seed=23):
        response = await self.client.post('/api/generate', json={
            'prompt':'A blue ceramic vase', 'engine':engine, 'model':'fixture',
            'width':512, 'height':512, 'steps':8, 'cfg':1, 'seed':seed, 'count':count})
        self.assertEqual(response.status,200)
        return await response.json()

    async def test_pause_holds_new_jobs_and_double_resume_does_not_duplicate(self):
        calls=[]
        async def render(app,row,p):
            calls.append(p['seed'])
            return b'fixture'
        self.studio.render_comfy=render
        await self.client.post('/api/queue/pause',json={})
        job=await self.generate(3)
        await asyncio.sleep(.05)
        self.assertEqual(calls,[])
        status=await (await self.client.get('/api/queue/status')).json()
        self.assertEqual(status['queued'],3)
        await self.client.post('/api/queue/resume',json={})
        await self.client.post('/api/queue/resume',json={})
        await asyncio.wait_for(self.app['queue'].join(),5)
        self.assertEqual(calls,[23,24,25])
        self.assertEqual(len(self.studio.rows("SELECT id FROM renders WHERE status='done'")),3)

    async def test_pause_allows_current_job_to_finish_without_starting_next(self):
        first=asyncio.Event();finish=asyncio.Event();calls=[]
        async def render(app,row,p):
            calls.append(row['id'])
            if len(calls)==1:
                first.set();await finish.wait()
            return b'fixture'
        self.studio.render_comfy=render
        job=await self.generate(2);await first.wait()
        await self.client.post('/api/queue/pause',json={})
        finish.set()
        await self.until(lambda:self.app.get('active_id') is None)
        self.assertEqual(calls,[job['ids'][0]])
        self.assertEqual(self.studio.rows('SELECT status FROM renders WHERE id=?',(job['ids'][1],))[0]['status'],'queued')
        await self.client.post('/api/queue/resume',json={})
        await asyncio.wait_for(self.app['queue'].join(),5)
        self.assertEqual(calls,job['ids'])

    async def test_stop_keeps_seed_and_resumes_interrupted_item_before_following_jobs(self):
        started=asyncio.Event();calls=[]
        async def render(app,row,p):
            calls.append((row['id'],p['seed']))
            if len(calls)==1:
                started.set();await asyncio.Event().wait()
            return b'fixture'
        self.studio.render_comfy=render
        job=await self.generate(2);await started.wait()
        await self.client.post('/api/queue/stop',json={})
        await self.until(lambda:not self.app.get('stopping') and self.app.get('active_id') is None)
        states=self.studio.rows('SELECT status FROM renders ORDER BY rowid')
        self.assertEqual([r['status'] for r in states],['paused','queued'])
        await self.client.post('/api/queue/resume',json={})
        await asyncio.wait_for(self.app['queue'].join(),5)
        self.assertEqual(calls,[(job['ids'][0],23),(job['ids'][0],23),(job['ids'][1],24)])

    async def test_resume_is_blocked_until_backend_acknowledges_stop(self):
        started=asyncio.Event();acknowledged=asyncio.Event()
        async def render(app,row,p):
            app['execution']={'engine':'comfy'};started.set()
            await asyncio.Event().wait()
        async def stop(app,execution):await acknowledged.wait()
        self.studio.render_comfy=render;self.studio.stop_owned_comfy=stop
        await self.generate();await started.wait()
        response=await self.client.post('/api/queue/stop',json={})
        self.assertTrue((await response.json())['stopping'])
        response=await self.client.post('/api/queue/resume',json={})
        self.assertEqual(response.status,400)
        acknowledged.set()
        await self.until(lambda:not self.app.get('stopping') and self.app.get('active_id') is None)
        self.assertEqual(self.studio.rows('SELECT status FROM renders')[0]['status'],'paused')

    async def test_failed_stop_keeps_live_job_running_and_reports_the_problem(self):
        started=asyncio.Event();finished=asyncio.Event()
        async def render(app,row,p):
            app['execution']={'engine':'comfy'};started.set();await finished.wait();return b'complete'
        async def stop(app,execution):raise ValueError('No task-level interrupt available')
        self.studio.render_comfy=render;self.studio.stop_owned_comfy=stop
        await self.generate();await started.wait()
        await self.client.post('/api/queue/stop',json={})
        await self.until(lambda:not self.app.get('stopping'))
        state=await (await self.client.get('/api/queue/status')).json()
        self.assertTrue(state['paused']);self.assertIn('task-level',state['error'])
        self.assertEqual(self.studio.rows('SELECT status FROM renders')[0]['status'],'running')
        finished.set();await asyncio.wait_for(self.app['queue'].join(),5)
        self.assertEqual(self.studio.rows('SELECT status FROM renders')[0]['status'],'done')

    async def test_queue_and_interrupted_job_survive_server_restart(self):
        await self.client.post('/api/queue/pause',json={})
        job=await self.generate(2)
        self.studio.update(job['ids'][0],status='running')
        await self.client.close()
        previous=os.environ.get('MATRIX_STUDIO_DATA_DIR')
        os.environ['MATRIX_STUDIO_DATA_DIR']=self.folder.name
        try:
            spec=importlib.util.spec_from_file_location('queue_restart',Path(__file__).resolve().parents[1]/'server.py')
            self.studio=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.studio)
        finally:
            if previous is None:os.environ.pop('MATRIX_STUDIO_DATA_DIR')
            else:os.environ['MATRIX_STUDIO_DATA_DIR']=previous
        calls=[]
        async def render(app,row,p):calls.append(row['id']);return b'fixture'
        self.studio.render_comfy=render
        self.app=self.studio.create_app()
        self.client=TestClient(TestServer(self.app),headers={'Host':'127.0.0.1:7880'})
        await self.client.start_server()
        state=await (await self.client.get('/api/queue/status')).json()
        self.assertTrue(state['paused']);self.assertEqual(state['paused_jobs'],1)
        self.assertEqual(calls,[])
        await self.client.post('/api/queue/resume',json={})
        await asyncio.wait_for(self.app['queue'].join(),5)
        self.assertEqual(calls,job['ids'])

    async def test_comfy_stop_deletes_only_owned_pending_or_interrupts_owned_running(self):
        for pending in (True,False):
            own=[1,'our-prompt',{}, {'client_id':'our-client'},[]]
            other=[2,'other-prompt',{}, {'client_id':'other-client'},[]]
            current={'queue_running':[other] if pending else [own], 'queue_pending':[own] if pending else [other]}
            commands=[]
            async def queue(request):return web.json_response(current)
            async def delete(request):
                body=await request.json();commands.append(('delete',body))
                current['queue_pending']=[x for x in current['queue_pending'] if x[1] not in body['delete']]
                return web.Response()
            async def interrupt(request):
                body=await request.json();commands.append(('interrupt',body))
                current['queue_running']=[x for x in current['queue_running'] if x[1]!=body['prompt_id']]
                return web.Response()
            engine=web.Application();engine.router.add_get('/queue',queue);engine.router.add_post('/queue',delete);engine.router.add_post('/interrupt',interrupt)
            async with TestServer(engine) as server:
                await self.studio.stop_owned_comfy(self.app,{'engine':'comfy','url':str(server.make_url('')).rstrip('/'),'client_id':'our-client','prompt_id':None if pending else 'our-prompt'})
            self.assertEqual(commands,[('delete',{'delete':['our-prompt']})] if pending else [('interrupt',{'prompt_id':'our-prompt'})])
            self.assertIn(other,current['queue_running']+current['queue_pending'])

    async def test_forge_stop_waits_for_our_task_and_never_interrupts_an_unowned_task(self):
        for already_done in (False,True):
            requests=[];interrupted=[]
            async def progress(request):
                body=await request.json();self.assertEqual(body['id_task'],'task(matrix-owned)');requests.append(body)
                if already_done or interrupted:return web.json_response({'active':False,'queued':False,'completed':True})
                return web.json_response({'active':len(requests)>1,'queued':len(requests)==1,'completed':False})
            async def interrupt(request):interrupted.append(True);return web.json_response({})
            engine=web.Application();engine.router.add_post('/internal/progress',progress);engine.router.add_post('/sdapi/v1/interrupt',interrupt)
            async with TestServer(engine) as server:
                await self.studio.stop_owned_automatic(self.app,{'url':str(server.make_url('')).rstrip('/'),'task_id':'task(matrix-owned)'})
            self.assertEqual(len(interrupted),0 if already_done else 1)

    async def test_stopped_montage_reuses_completed_scene(self):
        content=self.video_fixture('blue',81,16);second=asyncio.Event();calls=[]
        async def render(app,row,p):
            calls.append(p['seed'])
            if len(calls)==2:second.set();await asyncio.Event().wait()
            return content
        self.studio.render_comfy=render
        params=dict(kind='video',engine='comfy',family='wan14b',frames=81,fps=16,width=128,height=128,seed=31)
        self.studio.configure_montage(params,{'duration_seconds':6})
        response=self.studio.enqueue_video_batch(self.app,'Fixed camera',params,'Test',1)
        job=json.loads(response.body);await second.wait()
        first=self.studio.VIDEO_PROJECTS/job['id']/'001.mp4';self.assertTrue(first.is_file())
        await self.client.post('/api/queue/stop',json={})
        await self.until(lambda:not self.app.get('stopping') and self.app.get('active_id') is None)
        await self.client.post('/api/queue/resume',json={})
        await asyncio.wait_for(self.app['queue'].join(),5)
        self.assertEqual(calls,[31,32,32])
        with av.open(str(self.studio.OUTPUT/(job['id']+'.mp4'))) as container:
            fps=float(container.streams.video[0].average_rate);frames=list(container.decode(video=0))
        self.assertEqual(len(frames)/fps,6)

    async def test_qwen_stop_terminates_only_the_active_owned_subprocess(self):
        started=asyncio.Event();ended=asyncio.Event()
        class Process:
            returncode=None
            async def wait(self):await ended.wait();return self.returncode
            def terminate(self):self.returncode=-15;ended.set()
        proc=Process()
        async def create(*args,**kwargs):started.set();return proc
        self.studio.QFILES=[]
        for index in range(4):
            path=Path(self.folder.name)/str(index);path.write_bytes(b'x');self.studio.QFILES.append(path)
        self.studio.QWEN=Path(self.folder.name)
        with patch.object(self.studio.asyncio,'create_subprocess_exec',new=create):
            job=await self.generate(engine='qwen');await started.wait()
            await self.client.post('/api/queue/stop',json={})
            await self.until(lambda:proc.returncode is not None and not self.app.get('stopping'))
        self.assertEqual(proc.returncode,-15)
        await self.until(lambda:self.app.get('active_id') is None)
        self.assertEqual(self.studio.rows('SELECT status FROM renders WHERE id=?',(job['id'],))[0]['status'],'paused')
