"""Public entity resolution, uploaded reports, and supplemental business sources."""
import base64,hashlib,re
from urllib.parse import urlsplit
import annual_reports,business_research,entities,engine,research_pipeline,periods
from source_io import CACHE,now
from store import db,detail
def dispatch(path,body):
 import server
 if path=='/api/identify':return entities.identify(server.text(body,'query',80),body.get('refresh') is True)
 ident,action=path.strip('/').split('/')[2:];t=detail(ident)
 if action=='resolve':
  selected=body.get('entity_selections',{})
  if not isinstance(selected,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in selected.items()):raise ValueError('请选择有效的企业主体。')
  with db() as c:engine.meta_update(c,ident,entity_selections=selected)
  return detail(ident)
 company=server.text(body,'company',80)
 if company not in [t['company_a'],t['company_b']]:raise ValueError('请选择本研究的公司。')
 url=server.text(body,'url',1200)
 if urlsplit(url).scheme!='https' or not urlsplit(url).hostname or urlsplit(url).username:raise ValueError('请登记真实公开HTTPS出处。')
 if action=='source-url':
  doc=business_research.web_document(url,company,True);research_pipeline.save_document(ident,doc)
  cards=business_research.evidence_cards(detail(ident)['documents'],t['question'],[x for x in [t['company_a'],t['company_b']] if x],t['meta'].get('effective_type','business'))
  with db() as c:engine.meta_update(c,ident,business_cards=cards,effective_type=t['meta'].get('effective_type','business'))
  return detail(ident)
 name=server.text(body,'name',200);year=int(body.get('year',0))
 if not 1900<=year<=2099 or not name.lower().endswith('.pdf'):raise ValueError('请上传PDF年报并填写有效报告年度。')
 try:raw=base64.b64decode(server.text(body,'content',34_000_000),validate=True)
 except ValueError:raise ValueError('上传文件内容损坏。')
 if len(raw)>25_000_000:raise ValueError('PDF超过25 MB。')
 CACHE.mkdir(parents=True,exist_ok=True);sha=hashlib.sha256(raw).hexdigest();filename=sha+'.bin';(CACHE/filename).write_bytes(raw)
 doc=dict(id=sha,filename=filename,sha256=sha,company=company,report_year=year,title=name,url=url,kind='annual_pdf',downloaded_at=now(),retrieval_method='用户上传原文件（出处待人工核验）',status='已上传',versions_status='用户上传版本')
 try:
  pages=annual_reports.pages_from_pdf(raw,doc)
  head=re.sub(r'\s+','', '\n'.join(pages[:12]))
  entity=next((e for e in t['meta'].get('entities',[]) if e['name']==company),{})
  identity_tokens=[company,entity.get('legal_name'),entity.get('code')]
  if not any(token and re.sub(r'\s+','',token) in head for token in identity_tokens):raise ValueError('上传年报中的企业主体与本研究不匹配，未把其他公司的数据归到当前企业。请检查文件与主体。')
  parsed=annual_reports.extract_cn(pages,doc,company,t['meta'].get('requested_years') or periods.requested(t['question']))
 except ValueError as e:
  doc.update(status='上传文件尚未解析',error=str(e));research_pipeline.save_document(ident,doc);raise
 research_pipeline.save_document(ident,{**doc,'status':'已解析上传文件'})
 prior=t['datasets'][-1]['raw'] if t['datasets'] else []
 merged=[r for r in prior if not (r['company']==company and int(r['year']) in {int(x['year']) for x in parsed['rows']})]+parsed['rows']
 return server.import_data(ident,name,merged)
