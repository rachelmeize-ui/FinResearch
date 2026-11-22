"""Company resolution uses public issuer records, never guesses an ambiguous name."""
import re
from source_io import json_fetch,SourceError
PRIVATE={'米哈游':dict(id='private:mihoyo',name='米哈游',legal_name='上海米哈游网络科技股份有限公司',code='',market='非上市',listed=False,website='https://www.mihoyo.com/',identity_source='https://www.mihoyo.com/',identity_note='用户给定非上市企业；品牌与具体运营子公司需结合原文核对',source_types=['公司官网','产品官网','公开经营信息'],research_scope=['business','industry'])}
ALIASES={'mihoyo':'米哈游','上海米哈游网络科技股份有限公司':'米哈游'}
# Official source entry points, keyed by resolved security identity (not a fuzzy name).
# These are discovery seeds only: reports and business statements are fetched and parsed.
OFFICIAL_SOURCES={
 'cninfo:00700':dict(website='https://www.tencent.com/zh-cn/',official_domains=['tencent.com'],
  business_urls=['https://www.tencent.com/zh-cn/what-we-create/for-consumers/','https://www.tencent.com/zh-cn/what-we-create/for-business/'],
  report_indexes=['https://www.tencent.com/zh-cn/investors/financial-reports/'],
  website_source='https://www.tencent.com/zh-cn/investors/financial-reports/')
}
def identify(query,refresh=False):
 query=str(query).strip();canonical=ALIASES.get(query.lower(),query)
 if canonical in PRIVATE:return dict(query=query,candidates=[PRIVATE[canonical]],exact=True)
 if query.lower() in ['网易','netease','netease, inc.','ntes','09999','9999']:
  s,m=json_fetch('https://data.sec.gov/submissions/CIK0001110646.json',refresh=refresh)
  item=dict(id='sec:1110646',name='网易',legal_name=s['name'],code='NTES / 09999',market='Nasdaq / HKEX',listed=True,cik='1110646',website='https://ir.netease.com/',identity_source=m['url'],identity_sha256=m['sha256'],source_types=['20-F','SEC XBRL','官方业务披露'],research_scope=['financial','business','industry'])
  return dict(query=query,candidates=[item],exact=True)
 data,meta=json_fetch('https://www.cninfo.com.cn/new/information/topSearch/query',dict(keyWord=query,maxSecNum=10,maxListNum=10),refresh)
 candidates=[]
 for s in data:
  if s.get('category') not in ['A股','港股'] or s.get('delisted')=='true':continue
  code=s['code'];market=('SSE' if code.startswith('6') else 'BSE' if code.startswith(('4','8','9')) else 'SZSE') if s['category']=='A股' else 'HKEX'
  candidates.append(dict(id='cninfo:'+code,name=s['zwjc'],legal_name=None,legal_name_status='待从正式年报核对',code=code,org_id=s['orgId'],market=market,listed=True,identity_source=meta['url'],identity_sha256=meta['sha256'],source_types=['年度报告','正式公告'] if market!='HKEX' else ['港股披露（适配待完成）'],research_scope=['financial','business','industry'] if market!='HKEX' else ['business']))
 for item in candidates:item.update(OFFICIAL_SOURCES.get(item['id'],{}))
 exact=[x for x in candidates if query in [x['name'],x['code']]]
 return dict(query=query,candidates=candidates,exact=len(exact)==1,exact_id=exact[0]['id'] if len(exact)==1 else None)
def choose(result,selected=None):
 options=result['candidates']
 if selected:
  found=next((x for x in options if x['id']==selected),None)
  if found:return found
  raise SourceError('所选企业不属于本次查询候选，请重新识别并选择。')
 if result.get('exact'):
  return next((x for x in options if x['id']==result.get('exact_id')),options[0])
 if not options:raise SourceError('未找到可确认的企业主体。请补充股票代码、正式名称或公开资料，未自动匹配其他公司。')
 raise SourceError('存在多个候选企业，请选择正式主体与交易所后继续。')
