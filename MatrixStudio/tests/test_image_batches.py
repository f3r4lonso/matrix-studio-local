import asyncio
import json
from pathlib import Path
from aiohttp.test_utils import TestClient, TestServer
import test_server
import test_queue_controls
import unittest


class ImageBatchTest(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = test_server.StudioTest.asyncSetUp
    asyncTearDown = test_server.StudioTest.asyncTearDown
    until = test_queue_controls.QueueControlTest.until

    def payload(self):
        return {'name':'Arte', 'prompts':[{'name':'Bosque','prompt':'A forest'},
            {'name':'Ciudad','prompt':'A city'}, {'name':'Mar','prompt':'The sea'}],
            'settings':{'engine':'comfy','model':'fixture','seed':123}}

    async def submit(self, data=None):
        response = await self.client.post('/api/image-batches',json=data or self.payload())
        self.assertEqual(response.status,200,await response.text())
        return await response.json()

    async def test_atomic_validation_rejects_entire_file(self):
        for value in [None,{},[],{'name':'Invalid','prompts':[]},
                      {**self.payload(),'prompts':[{'prompt':'Valid'},{'prompt':''}]},
                      {**self.payload(),'settings':{'engine':'comfy','model':'fixture','cfg':float('nan')}},
                      {**self.payload(),'settings':{'engine':'comfy','model':'fixture','width':512.5}}]:
            response=await self.client.post('/api/image-batches',json=value)
            self.assertEqual(response.status,400,await response.text())
            self.assertEqual(self.studio.rows('SELECT id FROM renders'),[])
            self.assertEqual(self.studio.rows('SELECT id FROM image_batches'),[])

    async def test_order_names_one_image_per_entry_and_idempotent_import(self):
        calls=[]
        async def render(app,row,p):
            calls.append((row['prompt'],p['item_name'],p['batch_index'],p['seed']))
            return b'image'
        self.studio.render_comfy=render
        batch=await self.submit()
        await asyncio.wait_for(self.app['queue'].join(),5)
        duplicate=await self.submit()
        self.assertTrue(duplicate['existing'])
        self.assertEqual(batch['id'],duplicate['id'])
        self.assertEqual(calls,[('A forest','Bosque',1,123),('A city','Ciudad',2,124),('The sea','Mar',3,125)])
        report=await (await self.client.get('/api/image-batches')).json()
        self.assertEqual(report[0]['done'],3)
        conversation=await (await self.client.get('/api/renders?chat='+batch['chat'])).json()
        self.assertEqual([r['params']['item_name'] for r in conversation],['Bosque','Ciudad','Mar'])
        self.assertEqual([i['index'] for i in report[0]['items']],[1,2,3])

    async def test_error_blocks_next_and_continue_retries_without_repeating_done(self):
        calls=[]
        async def render(app,row,p):
            calls.append(p['batch_index'])
            if calls==[1,2]:raise ValueError('Test engine failure')
            return b'image'
        self.studio.render_comfy=render
        await self.submit()
        await self.until(lambda:len(calls)==2 and self.app.get('active_id') is None)
        self.assertFalse(self.app['queue_gate'].is_set())
        self.assertEqual(calls,[1,2])
        await self.client.post('/api/queue/resume',json={})
        await asyncio.wait_for(self.app['queue'].join(),5)
        self.assertEqual(calls,[1,2,2,3])
        self.assertEqual(len(self.studio.rows("SELECT id FROM renders WHERE status='done'")),3)

    async def test_stop_resume_retries_current_with_same_seed(self):
        calls=[];started=asyncio.Event()
        async def render(app,row,p):
            calls.append((p['batch_index'],p['seed']))
            if len(calls)==1:
                started.set();await asyncio.Event().wait()
            return b'image'
        self.studio.render_comfy=render
        await self.submit();await started.wait()
        await self.client.post('/api/queue/stop',json={})
        await self.until(lambda:not self.app.get('stopping'))
        await self.client.post('/api/queue/resume',json={})
        await self.client.post('/api/queue/resume',json={})
        await asyncio.wait_for(self.app['queue'].join(),5)
        self.assertEqual(calls,[(1,123),(1,123),(2,124),(3,125)])

    async def test_pause_and_restart_restore_progress_and_duplicate_detection(self):
        calls=[]
        async def render(app,row,p):
            calls.append(p['batch_index'])
            if p['batch_index']==1:self.studio.pause_generation_queue(app)
            return b'image'
        self.studio.render_comfy=render
        batch=await self.submit()
        await self.until(lambda:calls==[1] and self.app.get('active_id') is None)
        await self.client.close()
        import os,importlib.util
        previous=os.environ.get('MATRIX_STUDIO_DATA_DIR')
        os.environ['MATRIX_STUDIO_DATA_DIR']=self.folder.name
        try:
            spec=importlib.util.spec_from_file_location('batch_restart',Path(__file__).resolve().parents[1]/'server.py')
            self.studio=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.studio)
        finally:
            if previous is None:os.environ.pop('MATRIX_STUDIO_DATA_DIR',None)
            else:os.environ['MATRIX_STUDIO_DATA_DIR']=previous
        async def restored(app,row,p):calls.append(p['batch_index']);return b'image'
        self.studio.render_comfy=restored
        self.app=self.studio.create_app()
        self.client=TestClient(TestServer(self.app),headers={'Host':'127.0.0.1:7880'})
        await self.client.start_server()
        self.assertFalse(self.app['queue_gate'].is_set())
        duplicate=await self.submit();self.assertEqual(duplicate['id'],batch['id'])
        await self.client.post('/api/queue/resume',json={})
        await asyncio.wait_for(self.app['queue'].join(),5)
        self.assertEqual(calls,[1,2,3])

    async def test_repeated_prompts_remain_distinct_and_random_seeds_are_saved(self):
        await self.client.post('/api/queue/pause',json={})
        data=self.payload();data['prompts']=['Same prompt','Same prompt'];data['settings']['seed']=-1
        batch=await self.submit(data);saved=self.studio.rows('SELECT params FROM renders ORDER BY rowid')
        self.assertEqual(len(saved),2)
        seeds=[json.loads(row['params'])['seed'] for row in saved]
        self.assertTrue(all(0<=seed<=2147483647 for seed in seeds))
        duplicate=await self.submit(data);self.assertEqual(duplicate['id'],batch['id'])
        self.assertEqual([json.loads(row['params'])['seed'] for row in self.studio.rows('SELECT params FROM renders ORDER BY rowid')],seeds)

    async def test_pokemon_list_preserves_metadata_negative_and_file_order(self):
        await self.client.post('/api/queue/pause',json={})
        entries=[{'numero':25,'numero_pokedex':'#025','nombre':'Pikachu','prompt':'Real animal Pikachu','negative_prompt':'cartoon, toy'},
                 {'numero':1,'numero_pokedex':'#001','nombre':'Bulbasaur','prompt':'Real animal Bulbasaur','negative_prompt':''}]
        response=await self.submit({'document':entries,'settings':self.payload()['settings']})
        stored=self.studio.rows('SELECT prompt,params FROM renders ORDER BY rowid')
        params=[json.loads(row['params']) for row in stored]
        self.assertEqual([p['item_name'] for p in params],['Pikachu','Bulbasaur'])
        self.assertEqual([p['numero'] for p in params],[25,1])
        self.assertEqual([p['numero_pokedex'] for p in params],['#025','#001'])
        self.assertEqual([p['negative'] for p in params],['cartoon, toy',''])
        progress=await (await self.client.get('/api/image-batches')).json()
        self.assertEqual(progress[0]['items'][0]['numero_pokedex'],'#025')

    async def test_single_pokemon_object_and_bad_negative_are_atomic(self):
        await self.client.post('/api/queue/pause',json={})
        record={'numero':25,'numero_pokedex':'#025','nombre':'Pikachu','prompt':'Real living animal','negative_prompt':'toy'}
        result=await self.submit({'document':record,'settings':self.payload()['settings']})
        self.assertEqual(result['count'],1)
        result2=await self.submit({'document':record,'settings':self.payload()['settings']})
        self.assertTrue(result2['existing'])
        bad={'document':[record,{**record,'negative_prompt':3}], 'settings':self.payload()['settings']}
        response=await self.client.post('/api/image-batches',json=bad)
        self.assertEqual(response.status,400)
        self.assertEqual(len(self.studio.rows('SELECT id FROM renders')),1)
