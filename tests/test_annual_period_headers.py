"""Synthetic parser fixtures, not financial research or production data."""
import unittest
import annual_reports

class AnnualPeriodHeaders(unittest.TestCase):
    def pages(self):
        return ['合并资产负债表\n2020年12月31日 2019年12月31日\n单位：元\n资产总计 200.00 180.00\n负债合计 50.00 45.00\n母公司资产负债表',
                '合并利润表\n单位：元\n项目 本期发生额 上期发生额\n其中：营业收入 100.00 90.00\n其中：营业成本 40.00 35.00\n五、净利润 20.00 18.00\n母公司利润表']
    def doc(self,title):
        return dict(report_year=2020,title=title,url='https://example.com/synthetic.pdf',sha256='synthetic-only',id='synthetic-only',downloaded_at='test')
    def test_current_prior_header_binds_to_verified_annual_report(self):
        result=annual_reports.extract_cn(self.pages(),self.doc('测试主体2020年年度报告'),'测试主体',[2019,2020])
        self.assertEqual(result['rows'][0]['revenue'],'100.00')
        self.assertEqual(result['rows'][1]['year'],'2019')
        self.assertIn('2020/2019',result['rows'][0]['provenance']['net_profit']['column_rule'])
    def test_quarterly_title_does_not_authorize_annual_mapping(self):
        with self.assertRaises(annual_reports.SourceError):
            annual_reports.extract_cn(self.pages(),self.doc('测试主体2020年第三季度报告'),'测试主体',[2019,2020])
