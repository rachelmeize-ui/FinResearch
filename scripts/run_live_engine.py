"""Real external services in an isolated database. Never authorizes/calls a model."""
import os,sys,json,time,uuid,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
OUT=ROOT/'test-results/engine-v3';OUT.mkdir(parents=True,exist_ok=True)
os.environ['FINRESEARCH_DB']=str(OUT/('live-'+uuid.uuid4().hex[:8]+'.sqlite3'));os.environ['FINRESEARCH_TEST_MODE']='0'
import store,server,engine,research_pipeline
store.init();results=[]
cases=[('A','贵州茅台','五粮液','financial','比较2023—2025年收入增长、盈利和资产负债结构'),('B','网易','','financial','研究2023—2025年网易财务表现与币种口径'),('C','米哈游','网易','financial','比较2023—2025年两家游戏企业的产品组合、商业模式、主要市场和风险'),('extra','美的集团','','financial','研究2024—2025年收入增长与盈利能力')]
if len(sys.argv)>1:cases=[c for c in cases if c[0] in sys.argv[1:]]
for label,a,b,kind,q in cases:
 start=time.monotonic();t=server.create_task(dict(title=label+'｜通用引擎真实外部验收',company_a=a,company_b=b,question=q,dimensions=['收入与增长','盈利能力','资产与负债'],start_year=2023 if label!='extra' else 2024,end_year=2025,research_type=kind))
 if label=='extra':
  with store.db() as c:engine.meta_update(c,t['id'],entity_selections={a:'cninfo:000333'})
 print('START',label,t['id'],flush=True)
 error=''
 try:research_pipeline.run(t['id'],'live-direct',False)
 except Exception as e:error=str(e);traceback.print_exc()
 t=server.api('GET','/api/tasks/'+t['id']);(OUT/(label+'-task.json')).write_text(json.dumps(t,ensure_ascii=False,indent=2),encoding='utf-8')
 result=dict(case=label,id=t['id'],seconds=round(time.monotonic()-start,2),rows=len(t['datasets'][-1]['rows']) if t['datasets'] else 0,coverage=t['coverage'],documents=len(t['documents']),attempts=t['attempts'],effective_type=t['meta'].get('effective_type'),business_cards=len(t['meta'].get('business_cards',[])),error=error,model_runs=len(t['model_runs']))
 results.append(result);print(json.dumps({k:v for k,v in result.items() if k not in ['attempts','coverage']},ensure_ascii=True),flush=True)
(OUT/'live-results.json').write_text(json.dumps(dict(database=os.environ['FINRESEARCH_DB'],results=results),ensure_ascii=False,indent=2),encoding='utf-8')
