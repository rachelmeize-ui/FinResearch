"""Evidence-only business/industry research; no invented financial estimates or AI claims."""
import re,html,json,io,urllib.parse,xml.etree.ElementTree as ET
from html.parser import HTMLParser
from source_io import fetch,SourceError
class Text(HTMLParser):
 def __init__(self):super().__init__();self.skip=0;self.parts=[];self.title=False;self.title_text='';self.links=[];self.active_link=None
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag in ['script','style','noscript']:self.skip+=1
  if tag=='meta' and a.get('name','').lower() in ['description','keywords']:self.parts.append(a.get('content',''))
  if tag=='title':self.title=True
  if tag=='a':self.active_link=[a.get('href',''),'']
 def handle_endtag(self,tag):
  if tag in ['script','style','noscript']:self.skip=max(0,self.skip-1)
  if tag=='title':self.title=False
  if tag=='a' and self.active_link:self.links.append(self.active_link);self.active_link=None
 def handle_data(self,data):
  if self.title:self.title_text+=data
  if self.active_link:self.active_link[1]+=data
  if not self.skip and not self.title and data.strip():self.parts.append(data.strip())
def web_document(url,company,refresh=False):
 raw,meta=fetch(url,refresh=refresh,limit=4_000_000)
 if raw.startswith(b'%PDF') or 'application/pdf' in meta.get('content_type',''):raise SourceError('该链接为PDF，未当作网页正文解析；请使用年度报告入口或上传年报。')
 text=raw.decode('utf-8',errors='replace');p=Text();p.feed(text)
 content='\n'.join(p.parts)
 if len(content)<40:raise SourceError('官网正文需脚本加载，当前未提取到足够正文；请上传真实资料或补充网址。')
 return dict(**meta,company=company,title=p.title_text.strip() or company+'公开资料',content=content[:60000],links=p.links,kind='public_web',status='已提取公开正文',date_scope='当前网页，未证明为所选历史年度快照')

def official_url(url,domains):
 p=urllib.parse.urlsplit(url);host=(p.hostname or '').lower()
 return p.scheme=='https' and any(d and (host==d or host.endswith('.'+d)) for d in domains)

def report_links(doc,years,domains):
 """Select annual, not interim, PDF links from an actually downloaded official index."""
 found={}
 for href,label in doc.get('links',[]):
  label=re.sub(r'\s+',' ',label).strip();match=re.search(r'((?:19|20)\d{2})\s*(?:年\s*)?(?:年度報告|年度报告|年報|年报|annual report)',label,re.I)
  url=urllib.parse.urljoin(doc['final_url'],href)
  if match and int(match[1]) in years and urllib.parse.urlsplit(url).path.lower().endswith('.pdf') and official_url(url,domains):
   found.setdefault(int(match[1]),dict(url=url,title=label,year=int(match[1]),discovery_url=doc['url'],discovery_sha256=doc['sha256']))
 return list(found.values())

def report_document(link,company,refresh=False):
 from annual_reports import pages_from_pdf
 raw,meta=fetch(link['url'],refresh=refresh,timeout=240);pages=pages_from_pdf(raw,meta)
 year=link['year'];method='pypdf'
 def confirms(pages):
  front=re.sub(r'\s+','', '\n'.join(pages[:8])).translate(str.maketrans('〇零一二三四五六七八九','00123456789'))
  return bool(re.search(str(year)+r'(?:年)?(?:年度報告|年度报告|年報|年报)',front,re.I) or re.search(r'annualreport'+str(year),front,re.I) or re.search(str(year)+r'annualreport',front,re.I))
 front=re.sub(r'\s+','', '\n'.join(pages[:8]))
 if not confirms(pages) and re.search(r'(?:19|20)\d{2}(?:年)?(?:年度報告|年度报告|年報|年报)|annualreport(?:19|20)\d{2}',front,re.I):raise SourceError(f'{year}年报已下载，但封面年度与所选年度不一致，未采用该文件。')
 if not confirms(pages):
  # Some Chinese CFF fonts are extracted as unrelated Unicode by pypdf. Use
  # pdfminer's CMap support; keep a separate cache so financial parsing is unchanged.
  from source_io import CACHE
  file=CACHE/(meta['sha256']+'.business-pages-v2.json')
  try:
   if file.exists():pages=json.loads(file.read_text(encoding='utf8'))
   else:
    import pdfplumber
    with pdfplumber.open(io.BytesIO(raw)) as pdf:pages=[page.extract_text() or '' for page in pdf.pages]
    file.write_text(json.dumps(pages,ensure_ascii=False),encoding='utf8')
   method='pdfplumber/pdfminer'
  except ImportError:raise SourceError('年报已下载，但中文字体解析组件未安装；请安装项目依赖后重试，未采用乱码正文。')
  except Exception:raise SourceError(f'{year}年报已下载，但封面及正文年度无法解析，未采用该文件。')
 if not confirms(pages):raise SourceError(f'{year}年报已下载，但封面及正文年度无法确认，未将其作为该年度证据。')
 return dict(**meta,company=company,title=link['title'],report_year=year,
  text_parser=method,
  discovery_url=link['discovery_url'],discovery_sha256=link['discovery_sha256'],
  content='\n'.join(pages),page_blocks=[dict(page=i+1,text=t) for i,t in enumerate(pages)],
  kind='official_report',status='已提取年报正文（未作财务字段核验）',date_scope=f'{year}年度报告 · 业务原文，待人工核验')
def discover(entity,question,years,refresh=False,progress=None):
 query=entity['name']+' '+question+' '+str(years[0])+' '+str(years[-1])
 domains=entity.get('official_domains') or [urllib.parse.urlsplit(entity.get('website','')).hostname]
 if entity.get('market')=='行业主题':domains=['stats.gov.cn','gov.cn','caict.ac.cn','cgigc.com.cn','gpc.org.cn']
 urls=[entity['website']] if entity.get('website') else []
 urls+=entity.get('business_urls',[])
 if entity.get('id')=='sec:1110646':urls.append('https://www.neteasegames.com/')
 search=dict(query=query,status='未执行',results=[])
 # Search is a public free endpoint; failures remain evidence of an attempted query, never results.
 try:
  raw,meta=fetch('https://www.bing.com/search?format=rss&q='+urllib.parse.quote(query),refresh=refresh,limit=2_000_000)
  items=ET.fromstring(raw).findall('.//item');search.update(status='已查找',source=meta['url'])
  for item in items:
   url=item.findtext('link') or '';host=urllib.parse.urlsplit(url).hostname or ''
   accepted=official_url(url,domains)
   search['results'].append(dict(title=item.findtext('title'),url=url,accepted=accepted,reason='' if accepted else '未属于已确认的官方来源域名，未采用'))
   if accepted:urls.append(url)
 except (SourceError,ET.ParseError) as e:search.update(status='检索服务不可用',reason=str(e))
 if search['status']=='已查找' and not any(r['accepted'] for r in search['results']):search.update(status='未发现可信官方结果',reason='返回结果未落在已确认的官网域名内，未作为业务证据下载。')
 docs=[];failures=[]
 if not any(domains):failures.append(dict(stage='官网定位',reason='已识别企业，但尚未确认官网域名；搜索结果不能自动视为官方证据。请补充官方资料网址。'))
 for url in list(dict.fromkeys(urls))[:4]:
  try:
   doc=web_document(url,entity['name'],refresh);doc['kind']='official_web';docs.append(doc)
  except SourceError as e:failures.append(dict(url=url,reason=str(e)))
 annual_attempts=[];annuals={}
 for url in entity.get('report_indexes',[]):
  try:
   index=web_document(url,entity['name'],refresh)
   for link in report_links(index,years,domains):annuals.setdefault(link['year'],link)
  except SourceError as e:failures.append(dict(stage='年报索引',url=url,reason=str(e)))
 for year in years if entity.get('report_indexes') else []:
  if progress:progress(f'正在下载并提取{entity["name"]}{year}年度业务资料')
  link=annuals.get(year)
  if not link:annual_attempts.append(dict(year=year,status='未找到',reason='官方索引未发现所选年度的完整年报PDF链接'));continue
  try:
   doc=report_document(link,entity['name'],refresh);docs.append(doc)
   annual_attempts.append(dict(year=year,status='已下载并提取正文',url=doc['url'],sha256=doc['sha256'],pages=len(doc['page_blocks'])))
  except SourceError as e:annual_attempts.append(dict(year=year,status='未完成',url=link['url'],reason=str(e)))
 return docs,dict(company=entity['name'],question=question,years=years,search=search,failures=failures,annual_attempts=annual_attempts)
DIMENSIONS={'产品组合':['产品','產品','游戏','遊戲','原神','崩坏','game','games','product','products'],'商业模式':['增值服务','增值服務','金融科技','营销服务','營銷服務','订阅','訂閱','广告','廣告','运营','運營','发行','發行','develop','publish','subscription','advertising','monetization'],'主要市场':['全球','海外','市场','市場','global','market','markets'],'竞争与风险':['风险','風險','竞争','競爭','risk','risks','competition']}

def passages(text):
 """Keep contiguous source context rather than isolated wrapped PDF lines."""
 for paragraph in re.split(r'(?<=[。！？])\n|\n\s*\n',text):
  lines=paragraph.splitlines()
  while len(lines)>1 and len(lines[0].strip())<14:lines.pop(0)
  paragraph='\n'.join(lines).strip()
  if len(paragraph)<=850:yield paragraph
  else:
   chunk=''
   for line in lines:
    if len(chunk)+len(line)>850:
     yield chunk.strip();chunk=''
    chunk+=line+'\n'
   if chunk.strip():yield chunk.strip()
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
    blocks=d.get('page_blocks') or [dict(page=None,text=d['content'])]
    for block in blocks:
     for line in passages(block['text']):
      line=line.strip()
      if re.match(r'^(?:了解更多|查看更多|查看详情|更多关于|learn more|read more|skip to|copyright)',line,re.I):continue
      if re.search(r'購股權|购股权|薪酬|股份獎勵|股份奖励|share option|remuneration',line,re.I):continue
      if re.search(r'附屬公司及受控制|已發行\s*[╱/]\s*實收|權益比例|权益比例|principal subsidiaries',line,re.I) or len(re.findall(r'\d+(?:\.\d+)?%',line))>=4:continue
      if re.search(r'营业收入|營業收入|净利润|淨利潤|市場份額|市場佔有率|市场份额|revenue|net profit|market share',line,re.I) and re.search(r'\d',line):continue
      minimum=16 if re.search(r'[\u4e00-\u9fff]',line) else 35
      if minimum<=len(line)<=850 and any(contains(line,w) for w in words):matches.append((line,d,block['page']))
   if matches:
    matches.sort(key=lambda pair:(pair[1].get('kind')=='official_report',dimension!='竞争与风险' and pair[2] is not None and pair[2]<=50,pair[1].get('report_year',0),sum(contains(pair[0],w) for w in words+qwords)),reverse=True)
    line,d,page=matches[0];quote=line;cards.append(dict(company=company,dimension=dimension,text=quote,quote=quote,source_id=d['id'],url=d['url']+(f'#page={page}' if page else ''),page=page,report_year=d.get('report_year'),status='来源摘录 · 待人工核对',kind='官方原文摘录（非AI推论）' if d.get('kind') in ['official_web','official_report'] else '第三方资料摘录（未独立核验）',date_scope=d.get('date_scope','见资料报告年度')+(f' · PDF第{page}页' if page else '')))
   else:cards.append(dict(company=company,dimension=dimension,text='当前已获取资料不足以回答该维度，未生成推断或金额。',quote='',url='',source_id='',status='资料不足',kind='信息缺口'))
 return cards
