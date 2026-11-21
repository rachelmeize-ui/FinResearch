"""Independent read-only verification of downloaded real financial study."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from openpyxl import load_workbook
import store,engine
root=Path(__file__).resolve().parents[1];out=root/'test-results/refocus'
p=Path(sys.argv[1]) if len(sys.argv)>1 else out/('regression.xlsx' if (out/'regression.xlsx').exists() else 'real-research.xlsx')
v=load_workbook(p,data_only=True);formula=load_workbook(p,data_only=False);s=v['财务分析'];checks=[]
def check(name,test):
 assert test,name
 checks.append(name)
check('6 expected worksheets',set(v.sheetnames)=={'财务分析','研究结论','数据来源','核验问题','处理日志','计算说明'})
check('4 real company-year rows',s.max_row==5)
check('Moutai 2024 revenue',abs(s['C3'].value-1708.9915227634)<1e-8)
check('Consolidated net income, not parent-only profit',abs(s['E3'].value-893.347280259)<1e-8)
check('Wuliangye consolidated profit',abs(s['E5'].value-331.9346048432)<1e-8)
check('Revenue year-on-year',abs(s['K3'].value-(170899152276.34/147693604994.14-1))<1e-12)
check('Native Excel formula retained',formula['财务分析']['H3'].value=='=(C3-D3)/C3')
check('20 metric provenance rows',v['数据来源'].max_row==21)
check('Original currency and units',v['数据来源']['E2'].value=='元' and v['数据来源']['F2'].value=='CNY')
check('Original disclosures retained','static.cninfo.com.cn' in v['数据来源']['I2'].value)
check('PDF actual page index',v['数据来源']['H2'].value==63)
check('Real model attribution','deepseek-flash' in '\n'.join(str(c.value) for row in v['计算说明'] for c in row))
check('No synthetic financial label',not any(c.value=='模拟数据' for sheet in v for row in sheet for c in row))
check('No formula error cells',not any(c.data_type=='e' for sheet in v for row in sheet for c in row))
with store.db() as c:
 calls=[dict(r) for r in c.execute('SELECT model,status FROM model_runs')]
check('Only one authorized real model request',len(calls)==1 and calls[0]['status']=='succeeded')
check('No authorization automatically replenished',engine.readiness()['authorized_calls_remaining']==0)
report=dict(checks=len(checks),passed=len(checks),items=checks,source_file=str(p),native_excel_recalculation='not tested',real_model_calls=len(calls))
destination=root/'test-results/ui-redesign/export-verification.json' if len(sys.argv)>1 else out/'export-verification.json'
destination.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=True))
