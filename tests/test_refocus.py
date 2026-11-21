import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import store,server,engine,reporting,public_data,finance

class RefocusTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{'FINRESEARCH_DB':str(Path(self.tmp.name)/'prod.sqlite3'),'FINRESEARCH_TEST_MODE':'0'});self.env.start();store.init()
 def tearDown(self):self.env.stop();self.tmp.cleanup()
 def task(self):return server.create_task(dict(title='真实财报研究',company_a='600519',company_b='000858',question='比较收入增长和盈利',dimensions=['收入与增长','盈利能力','资产与负债']))
 def test_codes_resolve_to_company(self):
  t=self.task();self.assertEqual(t['company_a'],'贵州茅台');self.assertEqual(t['company_b'],'五粮液')
 def test_simulation_not_allowed_in_production(self):
  t=self.task()
  with self.assertRaisesRegex(ValueError,'模拟数据'):server.import_data(t['id'],'bad.csv',[{'data_kind':'模拟数据'}])
  with self.assertRaisesRegex(ValueError,'模拟案例'):server.api('POST','/api/demo',{})
  self.assertFalse(store.detail(t['id'])['datasets'])
 def test_production_requires_source(self):
  t=self.task()
  with self.assertRaisesRegex(ValueError,'HTTPS出处'):server.import_data(t['id'],'bad.csv',[{'data_kind':'公开资料待核验','source':'虚构网址'}])
 def test_home_has_no_development_data(self):
  state=server.api('GET','/api/state');self.assertNotIn('operations',state);self.assertNotIn('releases',state)
 def test_old_simulated_task_preserved_but_hidden(self):
  t=self.task()
  with store.db() as c:engine.meta_update(c,t['id'],visibility='archived_test')
  self.assertFalse(server.api('GET','/api/state')['tasks']);self.assertEqual(store.detail(t['id'])['id'],t['id'])
 def test_missing_key_does_not_call_network(self):
  with patch('engine.config',return_value=dict(key='',base_url='https://api.deepseek.com',model='test')),patch('urllib.request.urlopen') as net:
   with self.assertRaises(ValueError):engine.launch(self.task()['id'],'model')
   net.assert_not_called()
 def test_no_consent_does_not_call_network(self):
  with patch('engine.config',return_value=dict(key='test-key',base_url='https://api.deepseek.com',model='test')),patch('urllib.request.urlopen') as net:
   with self.assertRaises(ValueError):engine.launch(self.task()['id'],'model')
   net.assert_not_called()
 def test_unknown_company_does_not_return_fake(self):
  with self.assertRaisesRegex(ValueError,'不会生成替代数据'):public_data.collect_company('未知公司')
 def test_download_failure_returns_error(self):
  import urllib.error
  with patch('urllib.request.urlopen',side_effect=urllib.error.URLError('blocked')):
   with self.assertRaisesRegex(ValueError,'下载失败'):public_data.download(public_data.CATALOG['贵州茅台'],refresh=True)
 def test_column_extractor_does_not_use_current_liabilities(self):
  values,quote=public_data.extract_pair('流动负债合计 80.00 70.00\n负债合计 100.00 90.00','liabilities');self.assertEqual(values,['100.00','90.00'])
 def test_ai_duplicate_pair_rejected(self):
  t=self.task();row=dict(company='贵州茅台',dimension='收入与增长',text='测试',quote='a'*20,source_id='x')
  with self.assertRaises(ValueError):engine.validate_model_output(t,[row,row],[])
 def test_stale_ai_excluded_after_new_dataset(self):
  t=self.task();t['datasets']=[{'id':'new','rows':[]}];t['meta']['active_source_ids']=['s'];t['model_runs']=[dict(status='succeeded',dataset_id='old',source_ids=['s'],research_id='r')];t['research']=[dict(id='r',cells=[{'text':'旧研究'}])]
  state=reporting.state(t);self.assertTrue(state['ai_stale']);self.assertIsNone(state['ai'])
 def test_stale_ai_excluded_after_sources_change(self):
  t=self.task();t['datasets']=[{'id':'d','rows':[]}];t['meta']['active_source_ids']=['new'];t['model_runs']=[dict(status='succeeded',dataset_id='d',source_ids=['old'],research_id='r')]
  self.assertTrue(reporting.state(t)['ai_stale'])
 def test_metric_metadata_survives_standardization(self):
  from test_core import row
  raw=row(company='贵州茅台',source='https://example.com/report',data_kind='公开资料待核验',provenance={'revenue':{'page':10}})
  rows,_=finance.analyze([raw],['贵州茅台','五粮液']);self.assertEqual(rows[0]['provenance']['revenue']['page'],10)
 def test_real_collection_workflow_registers_sources_and_metadata(self):
  for entry in public_data.CATALOG.values():
   if not (public_data.ROOT/'data/public-reports'/entry['filename']).with_suffix('.meta.json').exists():self.skipTest('真实年报快照未下载')
  t=self.task();engine.legacy_collect_job(t['id'],'direct-real-snapshot-check',False)
  t=store.detail(t['id']);self.assertEqual(len(t['sources']),6);self.assertEqual(len(t['meta']['collection']),2)
  self.assertEqual(t['meta']['engine_state'],'财务分析就绪');self.assertEqual(len(t['datasets'][-1]['rows']),4)
 def test_new_source_clears_completed_ai_badge(self):
  t=self.task()
  with store.db() as c:engine.meta_update(c,t['id'],engine_state='AI研究初稿已生成')
  t=server.api('POST','/api/tasks/'+t['id']+'/sources',dict(company='贵州茅台',dimension='收入与增长',title='年报原文补充',url=public_data.CATALOG['贵州茅台']['url'],content='其中：营业收入 40 170,899,152,276.34 147,693,604,994.14',data_kind='公开资料待核验'))
  self.assertIn('待更新',t['meta']['engine_state'])

class RealSnapshotTests(unittest.TestCase):
 """Real locally downloaded PDF snapshots. No synthetic financial fixture here."""
 def test_real_pdf_metric_values(self):
  expected={
   '贵州茅台':{'2023':['147693604994.14','11867273851.78','77521476277.80','272699660092.25','49043190797.43'],'2024':['170899152276.34','13789482367.98','89334728025.90','298944579918.70','56933264798.10']},
   '五粮液':{'2023':['83272067317.19','20157143952.21','31520777582.15','165432981684.75','33083608497.58'],'2024':['89175178322.70','20461423083.74','33193460484.32','188252218704.17','51857424971.48']}}
  for company,entry in public_data.CATALOG.items():
   if not (public_data.ROOT/'data/public-reports'/entry['filename']).with_suffix('.meta.json').exists():self.skipTest('真实披露快照未下载，不代用模拟数据')
   result=public_data.collect_company(company,refresh=False)
   for row in result['rows']:
    self.assertEqual([row[k] for k in finance.MONEY],expected[company][row['year']])
    self.assertTrue(all(p['sha256']==result['meta']['sha256'] for p in row['provenance'].values()))

if __name__=='__main__':unittest.main()
