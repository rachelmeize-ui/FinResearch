"""Evidence pipeline: entity -> source discovery -> document -> structured facts -> report.
No model calls occur in this module. All task inputs drive live adapter queries.
"""
import json,re
from decimal import Decimal
import annual_reports,sec_reports,business_research,entities,periods,store
from source_io import SourceError
from store import db,uid,now,dumps,detail,log
TYPES={'financial':'上市公司财务与基本面研究','business':'企业竞品与业务比较','industry':'行业与市场研究'}
def save_document(ident,doc):
 doc={**doc,'record_id':uid()}
 with db() as c:c.execute('INSERT INTO research_documents VALUES(?,?,?,?)',(doc['record_id'],ident,dumps(doc),now()))
 return doc
def attempt(ident,payload):
 payload={**payload,'time':now()}
 with db() as c:c.execute('INSERT INTO research_attempts VALUES(?,?,?,?)',(uid(),ident,dumps(payload),now()))
def consolidate(rows,companies,years):
 """Prefer newest disclosure; preserve every original value and flag changed comparisons."""
 groups={};versions=[]
 for r in rows:groups.setdefault((r['company'],int(r['year'])),[]).append(r)
 selected=[]
 for key,variants in groups.items():
  variants.sort(key=lambda r:max(p.get('report_year',key[1]) for p in r['provenance'].values()),reverse=True)
  chosen=variants[0]
  for k,p in chosen['provenance'].items():
   history=[dict(value=v[k],source=v['source'],report_year=v['provenance'][k].get('report_year'),column_kind=v['provenance'][k].get('column_kind'),document_id=v['provenance'][k].get('document_id')) for v in variants]
   changed=len({Decimal(str(h['value'])) for h in history})>1
   p.update(versions=history,restatement='跨披露版本数值发生变化，需人工核对重述或口径原因' if changed else '已比对版本一致' if len(history)>1 else '单一披露版本，尚无交叉版本比较')
   if changed:versions.append(dict(company=key[0],year=key[1],field=k,versions=history))
  selected.append(chosen)
 return sorted(selected,key=lambda r:(companies.index(r['company']),int(r['year']))),versions
def run(ident,job_id,refresh=False):
 import engine,server
 t=detail(ident);years=t['meta'].get('requested_years') or periods.requested(t['question']);kind=t['meta'].get('research_type','financial')
 names=[x for x in [t['company_a'],t['company_b']] if x];resolved=[];selected=t['meta'].get('entity_selections',{})
 def progress(stage):
  with db() as c:c.execute('UPDATE jobs SET stage=? WHERE id=?',(stage,job_id))
 for name in names:
  progress('识别研究主体：'+name)
  try:
   if kind=='industry':result=dict(query=name,candidates=[dict(id='industry:'+name,name=name,legal_name=None,market='行业主题',listed=None,website='',identity_note='行业主题，不按上市公司财务报表处理')],exact=True)
   else:result=entities.identify(name,refresh)
   with db() as c:
    current=detail(ident)['meta'].get('entity_candidates',{});current[name]=result
    engine.meta_update(c,ident,entity_candidates=current)
   entity=entities.choose(result,selected.get(name));entity['input_name']=name
   # Keep rows bound to the user task name; formal identity remains separately explicit.
   entity['display_name']=entity['name'];entity['name']=name
   resolved.append(entity)
  except SourceError as e:
   attempt(ident,dict(stage='企业识别',company=name,status='受阻',reason=str(e)))
   raise
 effective='business' if kind=='financial' and any(e['listed'] is False for e in resolved) else kind
 reason='包含非上市企业，完整可比经审计财报不可确认；改为公开业务资料研究，不生成未公开财务数字。' if effective!=kind else ''
 with db() as c:engine.meta_update(c,ident,entities=resolved,effective_type=effective,route_reason=reason,discovery_plan=dict(years=years,question=t['question'],research_type=effective),collection=[],business_cards=[])
 all_rows=[];documents=[]
 for entity in resolved:
  if effective=='financial':
   if entity.get('cik'):
    try:
     docs,rs,attempts=sec_reports.collect(entity,years,refresh,progress)
     for d in docs:documents.append(save_document(ident,d))
     all_rows+=rs
     for a in attempts:attempt(ident,dict(stage='SEC年度检索',**a))
    except SourceError as e:
     for year in years:attempt(ident,dict(stage='SEC年度检索',company=entity['name'],year=year,status='受阻',reason=str(e)))
   elif entity['market'] in ['SSE','SZSE','BSE']:
    for year in years:
     progress(f'正在查找并解析{entity["name"]}{year}年度报告')
     try:
      doc,rs=annual_reports.acquire(entity,year,years,refresh);documents.append(save_document(ident,doc));all_rows+=rs
      if doc.get('legal_name'):entity['legal_name']=doc['legal_name']
      attempt(ident,dict(stage='年度报告',company=entity['name'],year=year,status=doc['status'],source=doc['url'],document_id=doc['id'],cached=doc.get('cached',False)))
     except SourceError as e:
      if hasattr(e,'document'):documents.append(save_document(ident,e.document))
      attempt(ident,dict(stage='年度报告',company=entity['name'],year=year,status='未完成',reason=str(e)))
   else:
    for year in years:attempt(ident,dict(stage='年度报告',company=entity['name'],year=year,status='未适配',reason='已识别上市主体，但该市场财报解析适配尚未完成；请上传年报或财务表。'))
  else:
   progress('根据研究问题查找'+entity['name']+'公开业务资料')
   docs,record=business_research.discover(entity,t['question'],years,refresh)
   for d in docs:documents.append(save_document(ident,d))
   attempt(ident,dict(stage='业务资料检索',company=entity['name'],status='已取得公开资料' if docs else '资料不足',**{k:v for k,v in record.items() if k!='company'}))
 if effective=='financial':
  if not all_rows:
   with db() as c:engine.meta_update(c,ident,entities=resolved,collection=documents)
   raise SourceError('已按所选公司和年份尝试查找，但本次未得到可核验的完整财务字段。请查看逐年记录，重试或上传年报/财务表；原有数据仍保留。')
  progress('核对来源版本、币种、单位并计算指标')
  chosen,changes=consolidate(all_rows,names,years)
  imported=server.import_data(ident,'公开披露通用研究｜'+periods.label(years),chosen)
  source_ids=[]
  with db() as c:
   for company in names:
    for dim in t['dimensions']:
     matching=[r for r in chosen if r['company']==company]
     if not matching:continue
     content='\n'.join(f'{r["year"]}年 '+p['label']+'：'+p['value']+'元；'+p.get('quote','') for r in matching for p in r['provenance'].values())[:6000]
     sid=uid();source_ids.append(sid);c.execute('INSERT INTO sources VALUES(?,?,?,?,?,?,?,?,?)',(sid,ident,company,dim,company+'公开报表核验摘录',matching[-1]['source'],content,'公开资料待核验',now()))
   engine.meta_update(c,ident,entities=resolved,collection=documents,active_source_ids=source_ids,version_differences=changes,engine_state='财务分析就绪' if periods.coverage(imported)['complete'] else '已取得部分年度数据',last_error='')
 else:
  cards=business_research.evidence_cards(documents,t['question'],names,effective)
  with db() as c:engine.meta_update(c,ident,collection=documents,business_cards=cards,engine_state='公开业务资料已整理，待人工核验' if any(c['quote'] for c in cards) else '资料不足',last_error='')
 with db() as c:log(c,'task',ident,'通用公开资料流程完成',None,dict(research_type=effective,companies=names,requested_years=years,documents=len(documents),financial_rows=len(all_rows),paid_model_calls=0))
