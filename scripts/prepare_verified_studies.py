"""Create reviewable real studies through the normal local API; no model endpoint."""
import json,time,urllib.request
from pathlib import Path
BASE='http://127.0.0.1:8530';OUT=Path('test-results/engine-v3');OUT.mkdir(exist_ok=True)
def api(path,body=None):
 req=urllib.request.Request(BASE+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
ids={};reports=[]
for key,a,b,question in [('A','贵州茅台','五粮液','比较2023—2025年两家公司的收入增长、盈利能力与资产负债结构，并核查披露版本差异。'),('B','网易','','研究2023—2025年网易财务表现，核对20-F与SEC XBRL的年度和CNY口径。'),('C','米哈游','网易','比较2023—2025年两家游戏企业的产品组合、商业模式、主要市场及风险，缺失公开证据时明确标注。')]:
 t=api('/api/tasks',dict(title=a+((' vs '+b) if b else '')+'｜2023—2025真实资料研究',company_a=a,company_b=b,question=question,start_year=2023,end_year=2025,dimensions=['收入与增长','盈利能力','资产与负债'],research_type='financial'))
 id=t['id'];ids[key]=id;api('/api/tasks/'+id+'/collect',dict(refresh=False));print('Started',key,id,flush=True)
 for _ in range(600):
  t=api('/api/tasks/'+id)
  if t['jobs'] and not any(j['status']=='running' for j in t['jobs']):break
  time.sleep(.2)
 assert t['jobs'][-1]['status']=='succeeded',t['jobs'][-1].get('error')
 assert len(t['model_runs'])==0
 if key in ['A','B']:assert t['coverage']['complete'];assert len(t['datasets'][-1]['rows'])==(6 if key=='A' else 3)
 else:assert t['meta']['effective_type']=='business';assert not t['datasets']
 reports.append(dict(case=key,id=id,url=BASE+'/#research/'+id,type=t['meta']['effective_type'],rows=len(t['datasets'][-1]['rows']) if t['datasets'] else 0,documents=len(t['documents']),newModelCalls=0))
assert api('/api/engine')['authorized_calls_remaining']==0
(OUT/'production-studies.json').write_text(json.dumps(dict(ids=ids,studies=reports),ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(reports,ensure_ascii=True))
