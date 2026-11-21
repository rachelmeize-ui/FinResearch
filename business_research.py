"""Evidence-only business/industry research; no invented financial estimates or AI claims."""
import re,html,urllib.parse,xml.etree.ElementTree as ET
from html.parser import HTMLParser
from source_io import fetch,SourceError
class Text(HTMLParser):
 def __init__(self):super().__init__();self.skip=0;self.parts=[];self.title=False;self.title_text=''
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag in ['script','style','noscript']:self.skip+=1
  if tag=='meta' and a.get('name','').lower() in ['description','keywords']:self.parts.append(a.get('content',''))
  if tag=='title':self.title=True
 def handle_endtag(self,tag):
  if tag in ['script','style','noscript']:self.skip=max(0,self.skip-1)
  if tag=='title':self.title=False
 def handle_data(self,data):
  if self.title:self.title_text+=data
  if not self.skip and not self.title and data.strip():self.parts.append(data.strip())
def web_document(url,company,refresh=False):
 raw,meta=fetch(url,refresh=refresh,limit=4_000_000)
 text=raw.decode('utf-8',errors='replace');p=Text();p.feed(text)
 content='\n'.join(p.parts)
 if len(content)<40:raise SourceError('官网正文需脚本加载，当前未提取到足够正文；请上传真实资料或补充网址。')
 return dict(**meta,company=company,title=p.title_text.strip() or company+'公开资料',content=content[:60000],kind='public_web',status='已提取公开正文',date_scope='当前网页，未证明为所选历史年度快照')
def discover(entity,question,years,refresh=False):
 query=entity['name']+' '+question+' '+str(years[0])+' '+str(years[-1])
 domains=[urllib.parse.urlsplit(entity.get('website','')).hostname]
 if entity.get('market')=='行业主题':domains=['stats.gov.cn','gov.cn','caict.ac.cn','cgigc.com.cn','gpc.org.cn']
 urls=[entity['website']] if entity.get('website') else []
 if entity.get('id')=='sec:1110646':urls.append('https://www.neteasegames.com/')
 search=dict(query=query,status='未执行',results=[])
 # Search is a public free endpoint; failures remain evidence of an attempted query, never results.
 try:
  raw,meta=fetch('https://www.bing.com/search?format=rss&q='+urllib.parse.quote(query),refresh=refresh,limit=2_000_000)
  items=ET.fromstring(raw).findall('.//item');search.update(status='已查找',source=meta['url'])
  for item in items:
   url=item.findtext('link') or '';host=urllib.parse.urlsplit(url).hostname or ''
   search['results'].append(dict(title=item.findtext('title'),url=url))
   if any(d and (host==d or host.endswith('.'+d)) for d in domains):urls.append(url)
 except (SourceError,ET.ParseError) as e:search.update(status='检索服务不可用',reason=str(e))
 docs=[];failures=[]
 for url in list(dict.fromkeys(urls))[:4]:
  try:
   doc=web_document(url,entity['name'],refresh);doc['kind']='official_web';docs.append(doc)
  except SourceError as e:failures.append(dict(url=url,reason=str(e)))
 return docs,dict(company=entity['name'],question=question,years=years,search=search,failures=failures)
DIMENSIONS={'产品组合':['产品','游戏','原神','崩坏','game','product'],'商业模式':['运营','发行','IP','服务','develop','publish','service'],'主要市场':['全球','海外','市场','global','market'],'竞争与风险':['风险','竞争','risk','competition']}
def contains(line,word):
 return bool(re.search(r'\b'+re.escape(word)+r'\b',line,re.I)) if re.fullmatch('[A-Za-z]+',word) else word in line
def evidence_cards(documents,question,companies,research_type='business'):
 cards=[];qwords=[x for x in re.findall(r'[\u4e00-\u9fff]{2,8}|[A-Za-z]{3,}',question) if x not in ['比较','公司','研究','分析']]
 for company in companies:
  docs=[d for d in documents if d.get('company')==company and d.get('content')]
  dimensions={'市场规模与增长':['市场','规模','增长','market','growth'],'产业链与商业模式':['产业链','商业模式','发行','运营','industry','publish'],'竞争格局':['竞争','格局','competition'],'政策与风险':['政策','监管','风险','regulation','risk']} if research_type=='industry' else DIMENSIONS
  for dimension,words in dimensions.items():
   matches=[]
   for d in docs:
    for line in d['content'].splitlines():
     if re.search(r'营业收入|净利润|市场份额|revenue|net profit|market share',line,re.I) and re.search(r'\d',line):continue
     if 35<=len(line)<=850 and any(contains(line,w) for w in words):matches.append((line,d))
   if matches:
    matches.sort(key=lambda pair:sum(contains(pair[0],w) for w in words+qwords),reverse=True)
    line,d=matches[0];cards.append(dict(company=company,dimension=dimension,text=line[:350],quote=line[:350],source_id=d['id'],url=d['url'],status='来源摘录 · 待人工核对',kind='官方原文摘录（非AI推论）' if d.get('kind')=='official_web' else '第三方资料摘录（未独立核验）',date_scope=d.get('date_scope','见资料报告年度')))
   else:cards.append(dict(company=company,dimension=dimension,text='当前已获取资料不足以回答该维度，未生成推断或金额。',quote='',url='',source_id='',status='资料不足',kind='信息缺口'))
 return cards
