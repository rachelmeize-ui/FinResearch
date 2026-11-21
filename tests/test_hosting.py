import base64
import http.client
import io
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import hosting
import server
import store
import exporter
from openpyxl import load_workbook


class HostingTests(unittest.TestCase):
    def test_remote_start_fails_without_private_access_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            hosting.validate('127.0.0.1')
            with self.assertRaises(ValueError): hosting.validate('0.0.0.0')
        with patch.dict(os.environ, {'FINRESEARCH_PUBLIC_ORIGIN':'https://research.example.com','FINRESEARCH_ACCESS_PASSWORD':'short'}, clear=True):
            with self.assertRaises(ValueError): hosting.validate('0.0.0.0')

    def test_remote_host_auth_origin_and_health(self):
        env = {'FINRESEARCH_PUBLIC_ORIGIN':'https://research.example.com','FINRESEARCH_ACCESS_PASSWORD':'a'*32}
        with patch.dict(os.environ, env):
            hosting.validate('0.0.0.0')
            httpd = server.ThreadingHTTPServer(('127.0.0.1',0), server.Handler)
            thread = threading.Thread(target=httpd.serve_forever, daemon=True); thread.start()
            def request(path, authorization='', method='GET', origin='', host='research.example.com'):
                conn=http.client.HTTPConnection('127.0.0.1',httpd.server_port,timeout=5)
                headers={'Host':host, 'Authorization':authorization}
                if origin: headers['Origin']=origin
                conn.request(method,path,headers=headers)
                response=conn.getresponse();status=response.status;data=response.read();conn.close()
                return status,data
            try:
                self.assertEqual(request('/')[0],401)
                self.assertEqual(request('/api/state')[0],401)
                self.assertEqual(request('/healthz')[0],200)
                good='Basic '+base64.b64encode(('owner:'+env['FINRESEARCH_ACCESS_PASSWORD']).encode()).decode()
                self.assertEqual(request('/',good)[0],200)
                self.assertEqual(request('/api/state','Basic invalid')[0],401)
                self.assertEqual(request('/',good,host='attacker.example')[0],403)
                self.assertEqual(request('/api/tasks',good,'POST','https://attacker.example')[0],403)
            finally:
                httpd.shutdown();httpd.server_close();thread.join(timeout=5)

    def test_persistent_directory_preserves_research_between_connections(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, {'FINRESEARCH_DATA_DIR':td,'FINRESEARCH_TEST_MODE':'0'}):
            with patch.dict(os.environ, {}, clear=False):
                previous=os.environ.pop('FINRESEARCH_DB',None)
                try:
                    store.init()
                    t=server.create_task(dict(title='持久化',company_a='网易',company_b='',question='公开资料',dimensions=['业务'],research_type='business'))
                    store.init()
                    self.assertEqual(store.detail(t['id'])['title'],'持久化')
                    self.assertTrue((Path(td)/'workspace.sqlite3').is_file())
                finally:
                    if previous is not None: os.environ['FINRESEARCH_DB']=previous

    def test_server_excel_preserves_formula_results_and_untrusted_text(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, {'FINRESEARCH_DB':str(Path(td)/'test.sqlite3'),'FINRESEARCH_TEST_MODE':'1','FINRESEARCH_EXCEL_BACKEND':'portable'}):
            store.init()
            t=server.create_task(dict(title='=1+1',company_a='A',company_b='',question='测试',dimensions=['盈利能力'],start_year=2023,end_year=2024))
            rows=[dict(company='A',year=y,revenue=r,cost=30,net_profit=20,assets=200,liabilities=80,unit='亿元',currency='CNY',period='年度',scope='合并',source='https://example.com/test',data_kind='模拟数据') for y,r in [(2023,100),(2024,120)]]
            t=server.import_data(t['id'],'test.csv',rows)
            raw=exporter.excel(t)
            values=load_workbook(io.BytesIO(raw),data_only=True);formulas=load_workbook(io.BytesIO(raw),data_only=False)
            self.assertEqual(len(values.sheetnames),6)
            self.assertAlmostEqual(values['财务分析']['H2'].value,.7)
            self.assertAlmostEqual(values['财务分析']['K3'].value,.2)
            self.assertEqual(formulas['财务分析']['H2'].value,'=(C2-D2)/C2')
            self.assertEqual(formulas['计算说明']['B2'].data_type,'s')
            self.assertEqual(formulas['计算说明']['B2'].value,'=1+1')
