import unittest,tempfile,os,json
from unittest.mock import patch
from pathlib import Path
import annual_reports,entities,research_pipeline,source_io,business_research,store,server,engine
class EngineTests(unittest.TestCase):
 def test_download_retains_immutable_content_version(self):
  class Response:
   headers={'Content-Type':'application/pdf'}
   def __init__(self,raw):self.raw=raw
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def geturl(self):return 'https://example.com/report.pdf'
   def read1(self,n):raw=self.raw;self.raw=b'';return raw
  with tempfile.TemporaryDirectory() as td,patch.object(source_io,'CACHE',Path(td)),patch('source_io.safe_url'),patch('source_io.urllib.request.build_opener') as opener:
   opener.return_value.open.return_value=Response(b'%PDF-first-public-version')
   raw,first=source_io.fetch('https://example.com/report.pdf',refresh=True)
   opener.return_value.open.return_value=Response(b'%PDF-updated-public-version')
   _,second=source_io.fetch('https://example.com/report.pdf',refresh=True)
   self.assertNotEqual(first['filename'],second['filename']);self.assertEqual((Path(td)/first['filename']).read_bytes(),raw)
 def test_ambiguous_entity_never_picks_first(self):
  with self.assertRaisesRegex(ValueError,'多个候选'):entities.choose(dict(exact=False,candidates=[dict(id='a'),dict(id='b')]))
  self.assertEqual(entities.choose(dict(exact=False,candidates=[dict(id='a'),dict(id='b')]),'b')['id'],'b')
 def test_private_identity_not_listed(self):
  e=entities.choose(entities.identify('米哈游'));self.assertFalse(e['listed']);self.assertNotIn('financial',e['research_scope'])
 def test_public_url_rejects_private_network(self):
  for url in ['http://example.com','https://127.0.0.1/','https://user:secret@example.com/']:
   with self.assertRaises(ValueError):source_io.safe_url(url)
 def test_revision_history_not_silently_lost(self):
  def r(value,year):return dict(company='A',year=2024,revenue=value,source='https://example.com/'+str(year),provenance={'revenue':dict(report_year=year,column_kind='比较数')})
  chosen,changes=research_pipeline.consolidate([r('100',2024),r('90',2025)],['A'],[2024])
  self.assertEqual(chosen[0]['revenue'],'90');self.assertEqual(len(changes),1);self.assertEqual(len(chosen[0]['provenance']['revenue']['versions']),2)
 def test_navigation_words_not_business_evidence(self):
  docs=[dict(id='x',company='A',content='Skip to main navigation\nTECH OTAKUS SAVE THE WORLD',url='https://example.com',kind='official_web')]
  self.assertFalse(any(c['quote'] for c in business_research.evidence_cards(docs,'比较产品和商业模式',['A'])))
 def test_unverified_financial_numbers_not_business_facts(self):
  d=dict(id='x',company='米哈游',content='某第三方估计米哈游游戏营业收入2025年达到999999万元，市场份额为90%。',url='https://example.com',kind='public_web')
  self.assertFalse(any(c['quote'] for c in business_research.evidence_cards([d],'比较游戏产品',['米哈游'])))
 def test_empty_and_scanned_pdf_not_success(self):
  with self.assertRaises(ValueError):annual_reports.pages_from_pdf(b'not a pdf',{'sha256':'test-only'})
 def test_single_company_task_and_research_type_persist(self):
  with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,FINRESEARCH_DB=str(Path(td)/'t.sqlite')):
   store.init();t=server.create_task(dict(title='单公司',company_a='网易',company_b='',question='2023—2025年研究',start_year=2023,end_year=2025,dimensions=['业务'],research_type='business'))
   self.assertEqual(store.detail(t['id'])['meta']['research_type'],'business');self.assertEqual(t['company_b'],'')
 def test_business_query_drives_source_search(self):
  with patch('business_research.fetch',side_effect=source_io.SourceError('offline')):
   docs,attempt=business_research.discover(dict(name='A',website='https://example.com'), '研究产品结构',[2024,2025])
   self.assertIn('研究产品结构',attempt['search']['query']);self.assertEqual(attempt['search']['status'],'检索服务不可用');self.assertEqual(docs,[])

class RealAdapterSnapshots(unittest.TestCase):
 """Downloaded real documents only; no synthetic finance values stand in for integration."""
 def test_business_report_is_not_an_empty_financial_report(self):
  import reporting
  file=Path(__file__).resolve().parents[1]/'test-results/engine-v3/C-task.json'
  if not file.exists():self.skipTest('真实业务来源尚未获取')
  report=reporting.markdown(json.loads(file.read_text(encoding='utf-8')))
  self.assertIn('企业业务比较',report);self.assertIn('原文摘录，非AI推论',report);self.assertNotIn('财务数据与指标',report)
 def test_all_eight_real_a_share_reports_use_same_parser(self):
  base=Path(__file__).resolve().parents[1]/'test-results/engine-v3';count=0
  for name in ['A-task.json','extra-task.json']:
   file=base/name
   if not file.exists():self.skipTest('真实外部资料尚未获取')
   t=json.loads(file.read_text(encoding='utf-8'))
   for d in t['documents']:
    if d['kind']!='annual_pdf':continue
    pages=json.loads((source_io.CACHE/(d['sha256']+'.pages.json')).read_text(encoding='utf-8'))
    result=annual_reports.extract_cn(pages,d,d['company'],[2023,2024,2025])
    self.assertTrue(result['rows']);self.assertEqual(set(result['rows'][0]['provenance']),set(annual_reports.LABELS));count+=1
  self.assertEqual(count,8)
