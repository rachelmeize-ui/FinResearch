import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
import business_research as br
import entities
from source_io import SourceError

class BusinessDiscoveryTests(unittest.TestCase):
 def test_source_entry_matches_security_identity_not_input_name(self):
  results=[dict(category='港股',code='00700',orgId='tencent',zwjc='腾讯控股'),dict(category='港股',code='01698',orgId='music',zwjc='腾讯音乐-SW')]
  with patch('entities.json_fetch',return_value=(results,dict(url='https://example.com/identity',sha256='fixture'))):
   candidates=entities.identify('腾讯')['candidates']
  self.assertIn('tencent.com',candidates[0]['website']);self.assertNotIn('website',candidates[1])

 def test_official_annual_links_exclude_wrong_year_interim_and_external_host(self):
  doc=dict(final_url='https://issuer.example/reports/',url='https://issuer.example/reports/',sha256='index-hash',links=[
   ('/a.pdf','2024 年度报告'),('/b.pdf','2025 中期报告'),('/c.pdf','2026 Annual Report'),
   ('https://evil.example/a.pdf','2025 Annual Report'),('/d.pdf','2025 Annual Report')])
  links=br.report_links(doc,[2024,2025],['issuer.example'])
  self.assertEqual([l['year'] for l in links],[2024,2025]);self.assertEqual(links[1]['url'],'https://issuer.example/d.pdf')

 def test_downloaded_pdf_wrong_cover_year_is_not_accepted(self):
  link=dict(url='https://issuer.example/a.pdf',title='2025年度报告',year=2025,discovery_url='index',discovery_sha256='hash')
  with patch('business_research.fetch',return_value=(b'%PDF-test',dict(sha256='fixture'))),patch('annual_reports.pages_from_pdf',return_value=['2024 年度报告']):
   with self.assertRaisesRegex(SourceError,'封面年度'):br.report_document(link,'主体')

 def test_reports_have_longer_bounded_download_window(self):
  link=dict(url='https://issuer.example/a.pdf',title='2025年度报告',year=2025,discovery_url='index',discovery_sha256='hash')
  with patch('business_research.fetch',return_value=(b'%PDF-test',dict(sha256='fixture')) ) as fetch,patch('annual_reports.pages_from_pdf',return_value=['2025 年度报告']):
   doc=br.report_document(link,'主体')
  self.assertEqual(fetch.call_args.kwargs['timeout'],240);self.assertEqual(doc['report_year'],2025)

 def test_garbled_chinese_uses_separate_parser_and_checks_chinese_year(self):
  link=dict(url='https://issuer.example/a.pdf',title='2025年度报告',year=2025,discovery_url='index',discovery_sha256='hash')
  text='二零二五年年報\n公司在全球市場提供遊戲產品與服務。'
  with tempfile.TemporaryDirectory() as td,patch('source_io.CACHE',Path(td)),patch('business_research.fetch',return_value=(b'%PDF-test',dict(sha256='fixture'))),patch('annual_reports.pages_from_pdf',return_value=['\u025a\u0f67\u025a\u029e']),patch('pdfplumber.open') as parser:
   page=parser.return_value.__enter__.return_value;page.pages=[type('Page',(),{'extract_text':lambda self:text})()]
   doc=br.report_document(link,'主体')
   self.assertEqual(doc['text_parser'],'pdfplumber/pdfminer');self.assertEqual(doc['page_blocks'][0]['text'],text)
   self.assertTrue((Path(td)/'fixture.business-pages-v2.json').exists())

 def test_missing_domain_and_unrelated_search_are_explicit(self):
  rss=b'<rss><channel><item><title>Unrelated page</title><link>https://unrelated.example/</link></item></channel></rss>'
  with patch('business_research.fetch',return_value=(rss,dict(url='https://search.example/'))):
   docs,result=br.discover(dict(name='未知官网企业'),'研究产品结构',[2024,2025])
  self.assertEqual(docs,[]);self.assertEqual(result['search']['status'],'未发现可信官方结果')
  self.assertEqual(result['failures'][0]['stage'],'官网定位');self.assertFalse(result['search']['results'][0]['accepted'])

 def test_call_to_action_is_not_product_evidence(self):
  doc=dict(id='x',company='A',content='了解更多腾讯为消费者及企业提供的产品与服务，以及我们对未来的规划。',url='https://issuer.example/',kind='official_web')
  self.assertFalse(any(c['quote'] for c in br.evidence_cards([doc],'比较产品',['A'])))

 def test_chinese_report_evidence_retains_exact_quote_page_and_year(self):
  text='公司通过全球游戏发行服务满足不同市场的玩家需求。'
  doc=dict(id='real-shaped-fixture',company='A',content=text,page_blocks=[dict(page=9,text=text)],url='https://issuer.example/a.pdf',kind='official_report',report_year=2025,date_scope='2025年度报告')
  cards=br.evidence_cards([doc],'比较产品和市场',['A']);card=next(c for c in cards if c['dimension']=='主要市场')
  self.assertEqual(card['quote'],text);self.assertEqual(card['page'],9);self.assertEqual(card['report_year'],2025);self.assertTrue(card['url'].endswith('#page=9'));self.assertIn('官方原文',card['kind'])
  number_doc={**doc,'content':'公司营业收入2025年达到999999万元，游戏市场份额为90%。','page_blocks':[]}
  self.assertFalse(any(c['quote'] for c in br.evidence_cards([number_doc],'比较游戏产品',['A'])))

if __name__=='__main__':unittest.main()
