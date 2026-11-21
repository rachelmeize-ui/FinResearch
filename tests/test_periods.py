import unittest
from unittest.mock import patch
import periods,engine,reporting

def task(question='比较2023—2025年',years=(2023,2024)):
    return dict(company_a='A',company_b='B',question=question,dimensions=['收入'],meta={},datasets=[dict(id='d',rows=[dict(company=c,year=y,valid=True) for c in ['A','B'] for y in years])],model_runs=[],research=[],sources=[],active_issues=[])

class PeriodTests(unittest.TestCase):
    def test_question_range_and_single_year(self):
        for text in ['2023-2025','2023—2025','2023年至2025年','2023到2025']:
            self.assertEqual(periods.requested(text),[2023,2024,2025])
        self.assertEqual(periods.requested('分析2025年'),[2025])
    def test_explicit_years_and_invalid_range(self):
        self.assertEqual(periods.requested('2023—2024',dict(start_year=2023,end_year=2025)),[2023,2024,2025])
        for body in [dict(start_year=2025,end_year=2023),dict(start_year='abc',end_year=2025),dict(start_year=2000,end_year=2050)]:
            with self.assertRaises(ValueError):periods.requested('',body)
    def test_legacy_question_infers_requested_years_without_mutation(self):
        t=task();t['meta']['period']='2023—2024'
        c=periods.coverage(t)
        self.assertEqual(c['requested_period'],'2023—2025');self.assertEqual(c['actual_period'],'2023—2024')
        self.assertFalse(c['complete']);self.assertIn('A缺少2025',c['message']);self.assertEqual(t['meta'],{'period':'2023—2024'})
    def test_each_company_needs_each_year(self):
        t=task(years=(2023,2024,2025));t['datasets'][0]['rows']=[r for r in t['datasets'][0]['rows'] if not (r['company']=='B' and r['year']==2025)]
        c=periods.coverage(t);self.assertFalse(c['complete']);self.assertEqual(c['companies'][1]['missing_years'],[2025])
    def test_invalid_rows_do_not_fill_gap_and_new_batch_replaces_coverage(self):
        t=task();t['datasets'][0]['rows'].append(dict(company='A',year=2025,valid=False))
        self.assertFalse(periods.coverage(t)['complete'])
        t['datasets'].append(task(years=(2023,2024,2025))['datasets'][0]);self.assertTrue(periods.coverage(t)['complete'])
        self.assertEqual(periods.coverage(t)['actual_period'],'2023—2025')
    def test_empty_data_is_not_a_fixed_period(self):
        t=task();t['datasets']=[];c=periods.coverage(t)
        self.assertEqual(c['actual_period'],'尚未取得');self.assertEqual(c['status'],'待获取')
    def test_model_blocked_before_network_or_budget(self):
        with patch('engine.detail',return_value=task()),patch('engine.config') as config:
            with self.assertRaisesRegex(ValueError,'缺少2025'):engine.model_job('id','job')
            config.assert_not_called()
    def test_report_carries_gap_and_dynamic_years(self):
        t=task();t['title']='期间测试'
        with patch('engine.financial_summary',return_value=[]):
            s=reporting.state(t)
        self.assertIn('缺少2025',s['cautions'][0]);self.assertEqual(s['coverage']['requested_period'],'2023—2025')
        with patch('engine.financial_summary',return_value=[]):
            complete=reporting.state(task(years=(2023,2024,2025)))
        self.assertEqual(complete['coverage']['actual_period'],'2023—2025');self.assertFalse(any('2023—2024' in c for c in complete['cautions']))
