"""Read saved output independently with openpyxl; never creates workbooks."""
import json
from pathlib import Path
from openpyxl import load_workbook
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'test-results'/'download.xlsx'
values=load_workbook(path,data_only=True)
formulas=load_workbook(path,data_only=False)
s=values['财务分析']
assert len(values.sheetnames)==5
assert abs(s['H2'].value-.8)<1e-10
assert abs(s['I2'].value-.4)<1e-10
assert abs(s['K3'].value-.15)<1e-10
assert formulas['财务分析']['H2'].value=='=(C2-D2)/C2'
assert values['资料比较']['F2'].value=='https://example.invalid/synthetic-task'
assert '模拟数据' in s['A1'].value
assert isinstance(values['处理日志']['A2'].value,str)
for sheet in values:
    for r in sheet:
        for c in r:assert c.data_type!='e',(sheet.title,c.coordinate,c.value)
report={'checks':9,'passed':9,'reader':'openpyxl, read-only verification','native_excel_recalculation':'not tested','sheets':values.sheetnames,'values':{'gross_margin':s['H2'].value,'net_margin':s['I2'].value,'revenue_yoy':s['K3'].value}}
(ROOT/'test-results'/'export-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
