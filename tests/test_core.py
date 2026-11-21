import base64
import copy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import finance
import server
import store
import research

def row(**kw):
    return dict(company='A',year='2024',period='年度',scope='合并',currency='CNY',unit='亿元',revenue='100',cost='30',net_profit='20',assets='200',liabilities='80',source='人为构造的测试夹具',data_kind='模拟数据',**kw) if not kw else {**row(),**kw}

class DBTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{'FINRESEARCH_DB':str(Path(self.temp.name)/'test.sqlite3'),'FINRESEARCH_TEST_MODE':'1'});self.env.start();store.init()
    def tearDown(self):self.env.stop();self.temp.cleanup()
    def task(self):return server.create_task(dict(title='测试任务',company_a='A',company_b='B',question='测试口径',dimensions=['盈利能力','收入']))
    def imported(self):
        t=self.task();return server.import_data(t['id'],'test.csv',[row(),row(company='B')])

class RegressionTests(DBTest):
    def test_bootstrap_seeds_real_requirements(self):
        server.seed();server.seed()
        with store.db() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM operations').fetchone()[0],3)
    def test_same_second_import_restores_latest_batch(self):
        t=self.task()
        with patch('server.now',return_value='2026-11-21T12:00:00+00:00'),patch('server.uid',side_effect=['zz-older','log1','aa-newer','log2']):
            server.import_data(t['id'],'older.csv',[row()])
            newest=server.import_data(t['id'],'newer.csv',[row(revenue='150')])
        self.assertEqual(newest['datasets'][-1]['name'],'newer.csv')
    def test_reopening_issue_reopens_completed_task(self):
        t=self.task();t=server.import_data(t['id'],'test.csv',[row(),row(company='B',year='2023'),row(company='B',revenue='')])
        for i in t['issues']:server.api('PATCH','/api/issues/'+i['id'],dict(status='已忽略',note='测试任务，保留无效行且不纳入指标'))
        t=server.api('POST','/api/tasks/'+t['id']+'/complete',{})
        self.assertEqual(t['status'],'已完成')
        server.api('PATCH','/api/issues/'+t['issues'][0]['id'],dict(status='处理中',note='需要重新回查'))
        self.assertEqual(store.detail(t['id'])['status'],'待核验')

class FinancialTests(unittest.TestCase):
    def test_expected_metrics(self):
        r,issues=finance.analyze([row()],['A','B']);self.assertFalse(issues)
        self.assertAlmostEqual(r[0]['gross_margin'],.7);self.assertAlmostEqual(r[0]['net_margin'],.2);self.assertAlmostEqual(r[0]['debt_ratio'],.4)
    def test_unit_conversion_and_yoy(self):
        r,_=finance.analyze([row(year='2023',unit='万元',revenue='1000000',cost='300000',net_profit='200000',assets='2000000',liabilities='800000'),row(revenue='120')],['A','B'])
        self.assertEqual(r[0]['revenue'],100);self.assertAlmostEqual(r[1]['revenue_yoy'],.2)
    def test_gap_year_not_yoy(self):
        r,_=finance.analyze([row(year='2022'),row()],['A','B']);self.assertIsNone(r[1]['revenue_yoy'])
    def test_duplicate_all_rows_excluded(self):
        r,i=finance.analyze([row(),row(revenue='120')],['A','B']);self.assertEqual(sum(x['code']=='duplicate' for x in i),2);self.assertTrue(all(x['gross_margin'] is None for x in r))
    def test_losses_are_valid(self):
        r,i=finance.analyze([row(net_profit='-10')],['A','B']);self.assertTrue(r[0]['valid']);self.assertEqual(r[0]['net_margin'],-.1)
    def test_invalid_inputs_are_not_zero(self):
        for key,value in [('revenue',''),('revenue','abc'),('assets','0'),('revenue','0'),('unit','美元'),('currency','USD'),('period','半年'),('scope','母公司'),('year','2024Q1'),('revenue','NaN'),('revenue','inf'),('cost','-1'),('company','C')]:
            with self.subTest(key=key,value=value):
                r,i=finance.analyze([row(**{key:value})],['A','B']);self.assertTrue(i);self.assertFalse(r[0]['valid']);self.assertIsNone(r[0]['gross_margin'])
    def test_liabilities_exceed_assets_is_warning(self):
        r,i=finance.analyze([row(liabilities='210')],['A','B']);self.assertTrue(r[0]['valid']);self.assertIn('range',[x['code'] for x in i])
    def test_ratio_reconciliation(self):
        r,i=finance.analyze([row(net_margin='0.99')],['A','B']);self.assertIn('ratio_mismatch',[x['code'] for x in i])
    def test_invalid_reported_ratio(self):
        r,i=finance.analyze([row(net_margin='oops')],['A','B']);self.assertIn('type',[x['code'] for x in i])
    def test_number_formats(self):
        self.assertEqual(finance.number('1,000'),1000);self.assertEqual(finance.number('(12.3)'),-finance.number('12.3'))
    def test_parse_csv_chinese_aliases(self):
        r=finance.parse_file('a.csv',(server.ROOT/'examples/template.csv').read_bytes());self.assertIn('revenue',r[0])
    def test_reject_unknown_file(self):
        with self.assertRaises(ValueError):finance.parse_file('a.xls',b'bad')
    def test_reject_missing_columns(self):
        with self.assertRaises(ValueError):finance.parse_file('a.csv',b'company,year\nA,2024')
    def test_reject_duplicate_headers(self):
        with self.assertRaises(ValueError):finance.parse_file('a.csv',b'company,company\nA,B')
    def test_reject_empty_csv(self):
        with self.assertRaises(ValueError):finance.parse_file('a.csv',(','.join(finance.FIELDS)+'\n').encode())
    def test_xlsx_read_and_formulas_not_executed(self):
        # Read-only input fixture uses the stdlib ZIP/XML container, not spreadsheet authoring libraries.
        import zipfile
        from xml.sax.saxutils import escape
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:
            z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/></Types>')
            z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
            z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Input" sheetId="1" r:id="r1"/></sheets></workbook>')
            z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
            data=[finance.FIELDS,[row().get(k,'') for k in finance.FIELDS]]
            xml=''.join('<row r="%d">'%i+''.join('<c t="inlineStr"><is><t>'+escape(str(v))+'</t></is></c>' for v in r)+'</row>' for i,r in enumerate(data,1))
            z.writestr('xl/worksheets/sheet1.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+xml+'</sheetData></worksheet>')
        rows=finance.parse_file('test.xlsx',out.getvalue());self.assertEqual(rows[0]['company'],'A')

class APITests(DBTest):
    def test_create_import_read(self):
        t=self.imported();self.assertEqual(t['status'],'分析就绪');self.assertEqual(len(store.detail(t['id'])['datasets']),1)
    def test_no_auto_completion(self):self.assertNotEqual(self.imported()['status'],'已完成')
    def test_import_csv_api(self):
        t=self.task();content=(','.join(finance.FIELDS)+'\n'+','.join(str(row()[k]) for k in finance.FIELDS)).encode()
        t=server.api('POST','/api/tasks/'+t['id']+'/import',{'name':'a.csv','content':base64.b64encode(content).decode()});self.assertEqual(len(t['datasets']),1)
    def test_broken_import_preserves_data(self):
        t=self.imported()
        with self.assertRaises(ValueError):server.api('POST','/api/tasks/'+t['id']+'/import',{'name':'a.csv','content':'not base64!'})
        self.assertEqual(len(store.detail(t['id'])['datasets']),1)
    def test_note_is_required_and_status_validated(self):
        t=self.task();t=server.import_data(t['id'],'bad.csv',[row(revenue='')]);i=t['issues'][0]
        with self.assertRaises(ValueError):server.api('PATCH','/api/issues/'+i['id'],{'status':'已解决','note':''})
        with self.assertRaises(ValueError):server.api('PATCH','/api/issues/'+i['id'],{'status':'随便','note':'测试'})
    def test_issue_state_and_log_survive_new_connection(self):
        t=self.task();t=server.import_data(t['id'],'bad.csv',[row(revenue='')]);i=t['issues'][0]
        server.api('PATCH','/api/issues/'+i['id'],{'status':'处理中','note':'回查原始资料'})
        store.init();t=store.detail(t['id']);self.assertEqual(t['issues'][0]['note'],'回查原始资料');self.assertTrue(any(x['entity']=='issue' for x in t['audit']))
    def test_cannot_complete_unhandled_issues(self):
        t=self.task();t=server.import_data(t['id'],'bad.csv',[row(revenue='')])
        with self.assertRaises(ValueError):server.api('POST','/api/tasks/'+t['id']+'/complete',{})
    def test_cannot_complete_without_data(self):
        t=self.task()
        with self.assertRaises(ValueError):server.api('POST','/api/tasks/'+t['id']+'/complete',{})
    def test_cannot_complete_all_invalid_rows_even_if_ignored(self):
        t=self.task();t=server.import_data(t['id'],'bad.csv',[row(revenue='')])
        for i in t['issues']:server.api('PATCH','/api/issues/'+i['id'],{'status':'已忽略','note':'保留测试记录'})
        with self.assertRaises(ValueError):server.api('POST','/api/tasks/'+t['id']+'/complete',{})
    def test_valid_completion(self):
        t=self.imported();t=server.api('POST','/api/tasks/'+t['id']+'/complete',{});self.assertEqual(t['status'],'已完成')
    def test_cannot_complete_when_one_company_has_no_valid_data(self):
        t=self.task();server.import_data(t['id'],'one-company.csv',[row()])
        with self.assertRaises(ValueError):server.api('POST','/api/tasks/'+t['id']+'/complete',{})
    def test_unknown_task(self):
        with self.assertRaises(ValueError):store.detail('not-here')
    def test_same_company_rejected(self):
        with self.assertRaises(ValueError):server.create_task(dict(title='t',company_a='A',company_b='a',question='q',dimensions=['x']))
    def test_operation_create_edit_persists(self):
        b=dict(kind='反馈',title='测试反馈',persona='首次使用者',pain='测试',story='模拟任务',priority='P1',acceptance='可以导出',status='待评估',feature='export',synthetic=True)
        ident=server.operation(b)['id'];server.operation({**b,'status':'已完成'},ident)
        with store.db() as c:
            r=dict(c.execute('SELECT * FROM operations WHERE id=?',(ident,)).fetchone());self.assertEqual(r['status'],'已完成');self.assertEqual(r['synthetic'],1)
    def test_bad_priority_rejected(self):
        with self.assertRaises(ValueError):server.operation(dict(kind='需求',title='a',priority='P9',status='待评估'))
    def test_sources_and_research(self):
        t=self.task();t=server.api('POST','/api/tasks/'+t['id']+'/sources',dict(company='A',dimension='盈利能力',title='测试资料',url='https://example.invalid/synthetic',content='这是明确标注的模拟资料正文，不是真实公司公告。',data_kind='模拟数据'))
        t=server.api('POST','/api/tasks/'+t['id']+'/research',{})
        self.assertEqual(len(t['research'][0]['cells']),4);self.assertEqual(t['research'][0]['cells'][0]['status'],'待核实')
        cells=t['research'][0]['cells'];self.assertTrue(any(x['status']=='资料不足' for x in cells))
        rid=t['research'][0]['id']
        with self.assertRaises(ValueError):server.api('POST','/api/tasks/'+t['id']+'/review',dict(research_id=rid,index=0,status='人工已确认',text='核对结果',confirmed=False))
        t=server.api('POST','/api/tasks/'+t['id']+'/review',dict(research_id=rid,index=0,status='人工已确认',text='核对结果',confirmed=True))
        self.assertEqual(t['research'][0]['cells'][0]['status'],'人工已确认')
    def test_unknown_source_company_rejected(self):
        t=self.task()
        with self.assertRaises(ValueError):server.api('POST','/api/tasks/'+t['id']+'/sources',dict(company='C',dimension='收入',title='标题',url='https://example.invalid',content='模拟正文',data_kind='模拟数据'))
    def test_source_scheme_rejected(self):
        t=self.task()
        with self.assertRaises(ValueError):server.api('POST','/api/tasks/'+t['id']+'/sources',dict(company='A',dimension='收入',title='标题',url='javascript:alert(1)',content='模拟正文',data_kind='模拟数据'))
    def test_report_contains_source_kind_and_formulas(self):
        report=server.markdown(self.imported());self.assertIn('模拟数据',report);self.assertIn('人为构造',report);self.assertIn('合并净利润',report)
    def test_ai_disabled_before_network(self):
        with patch.dict(os.environ,{'FINRESEARCH_ENABLE_AI':'0'}),patch('urllib.request.urlopen') as f:
            with self.assertRaises(ValueError):research.generate(self.task(),True)
            f.assert_not_called()
    def test_quote_exact_match_guard(self):
        self.assertTrue(research.quote_matches('这是一段至少十二个字的完整原文','前缀这是一段至少十二个字的完整原文后缀'));self.assertFalse(research.quote_matches('这是编造的至少十二个字原文','真实来源没有这句话'))

if __name__=='__main__':unittest.main(verbosity=2)
