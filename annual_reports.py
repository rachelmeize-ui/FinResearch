"""Issuer/year discovery and generic consolidated-statement PDF extraction."""
import io,json,re,hashlib
from datetime import datetime
from decimal import Decimal
from pypdf import PdfReader
from source_io import fetch,json_fetch,clean,SourceError,CACHE
LABELS={'revenue':'营业收入','cost':'营业成本','net_profit':'合并净利润','assets':'总资产','liabilities':'总负债'}
PATTERNS={'revenue':r'(?:其中[:：]\s*)?营业收入','cost':r'(?:(?:其中|减)[:：]\s*)?营业成本','net_profit':r'(?:[四五六七八九十]+[、.．]\s*)?净利润(?:\s*[（(][^\n]{0,70}[）)])?', 'assets':r'资产总计','liabilities':r'负债合计'}
def discover(entity,year,refresh=False):
 data,meta=json_fetch('https://www.cninfo.com.cn/new/hisAnnouncement/query',dict(pageNum=1,pageSize=50,column='szse',tabName='fulltext',stock=entity['code']+','+entity['org_id'],searchkey=str(year)+'年年度报告',seDate=f'{year}-01-01~{datetime.now().year}-12-31',isHLtitle='false',sortName='time',sortType='desc'),refresh)
 candidates=[]
 for a in data.get('announcements') or []:
  title=clean(a['announcementTitle'])
  if a.get('secCode')!=entity['code'] or not re.search(str(year)+r'年?年度报告(?:全文)?(?:[（(](?:修订|更新|更正|修正)[^）)]*[）)])?$',title) or re.search(r'摘要|英文|取消|审核|审议|提示|披露时间',title):continue
  if not a.get('adjunctUrl','').lower().endswith('.pdf'):continue
  candidates.append(dict(title=title,url='https://static.cninfo.com.cn/'+a['adjunctUrl'],report_year=year,company=entity['name'],published_at=datetime.fromtimestamp(a['announcementTime']/1000).date().isoformat(),announcement_id=a['announcementId'],discovery_url=meta['url'],discovery_sha256=meta['sha256'],versions_status='修订版' if re.search('修订|更新|更正',title) else '原披露版'))
 candidates.sort(key=lambda x:(x['published_at'],x['versions_status']=='修订版'),reverse=True)
 if not candidates:raise SourceError(f'已查询{entity["name"]}{year}年度公告，未找到可确认的完整中文年报。可重新查找或上传该年度原始年报。')
 return candidates
def pages_from_pdf(raw,meta):
 if not raw.startswith(b'%PDF'):raise SourceError('下载内容不是PDF，未进入财务解析。')
 file=CACHE/(meta['sha256']+'.pages.json')
 if file.exists():return json.loads(file.read_text(encoding='utf-8'))
 try:
  reader=PdfReader(io.BytesIO(raw));pages=[p.extract_text() or '' for p in reader.pages]
 except Exception:raise SourceError('PDF无法提取文本，请上传可复制文本的原始年报或真实财务表。')
 if len(pages)>900:raise SourceError('年报页数超过支持上限。')
 if sum(map(len,pages))<200:raise SourceError('PDF可能为扫描件，尚未接入OCR，请上传文本版PDF或财务表。')
 file.write_text(json.dumps(pages,ensure_ascii=False),encoding='utf-8');return pages
def extract_cn(pages,doc,company,years):
 year=doc['report_year'];result={};field_evidence={};legal_name=None
 for text in pages[:12]:
  m=re.search(r'(?:公司的中文名称|公司中文名称|公司名称)\s*[:：]?\s*([^\n]{3,70}(?:股份有限公司|有限公司))',text)
  if m:legal_name=m[1].strip();break
 for kind,anchor,end,keys in [('balance','合并资产负债表','母公司资产负债表',['assets','liabilities']),('income','合并利润表','母公司利润表',['revenue','cost','net_profit'])]:
  blocks=[]
  for i,p in enumerate(pages):
   anchor_pattern=anchor.replace('合并','合并(?:及公司)?')
   anchor_match=re.search(anchor_pattern,p)
   if anchor_match:
    chunk='\n'.join(pages[i:i+4]);chunk=chunk[anchor_match.start():].split(end)[0]
    if any(k in chunk for k in ['资产总计','营业收入']):blocks.append((i,chunk))
  for i,block in blocks:
   compact=re.sub(r'\s+','',block[:1800])
   year_columns=str(year) in compact and str(year-1) in compact
   balance_columns=kind=='balance' and f'{year}年12月31日' in compact and '期末余额' in compact and '期初余额' in compact
   if not (year_columns or balance_columns):continue
   unit_match=re.search(r'(?:单位\s*[:：]|金额单位为)\s*(?:人民币)?\s*(亿元|万元|千元|元)',block[:1600])
   if not unit_match:continue
   unit=unit_match[1]
   if '美元' in block[:600] or '港元' in block[:600]:continue
   found={}
   for key in keys:
    # Only row-start labels within the consolidated statements; decimal tokens skip note numbers.
    pat=re.compile(r'(?m)^\s*'+PATTERNS[key]+r'([^\n]*(?:\n[^\n]*){0,2})')
    matches=list(pat.finditer(block))
    for m in matches:
     tail=m.group(0)
     if key=='net_profit' and ('归属于' in tail.split('\n')[0] or '综合收益' in tail.split('\n')[0]):continue
     values=list(re.finditer(r'[（(]?[−–-]?(?:\d{1,3}(?:[,，]\d{3})+(?:\.\d{2})?|\d+\.\d{2})[)）]?(?!\d)',tail))
     if len(values)<2:continue
     quote=tail[:values[1].end()].strip()
     vals=[x.group().replace(',','').replace('，','').replace('−','-').replace('–','-').replace('(','-').replace('（','-').replace(')','').replace('）','') for x in values[:2]]
     before=block[:m.start()];page=i+1+before.count('\n\f')
     # Locate the exact field on its actual PDF page, including statements continuing on next pages.
     page=next((j+1 for j in range(i,min(i+4,len(pages))) if re.search(r'(?m)^\s*'+PATTERNS[key],pages[j])),i+1)
     found[key]=(vals,dict(field=key,label=LABELS[key],page=page,quote=quote,url=doc['url'],report_year=year,unit=unit,currency='CNY',scope='合并',sha256=doc['sha256'],document_id=doc['id'],version=doc.get('versions_status','原披露版')))
     break
   if len(found)==len(keys):
    for k,(v,p) in found.items():result[k]=v;field_evidence[k]=p
    break
 missing=set(LABELS)-set(result)
 if missing:raise SourceError('已取得年报，但通用合并报表解析尚不能核验：'+ '、'.join(LABELS[k] for k in sorted(missing))+'。未用估计值补齐，可上传真实财务表。')
 rows=[]
 for j,y in enumerate([year,year-1]):
  if y not in years:continue
  factors={'元':Decimal(1),'万元':Decimal(10000),'千元':Decimal(1000),'亿元':Decimal(100000000)}
  values={k:str((abs(Decimal(result[k][j])) if k=='cost' else Decimal(result[k][j]))*factors[field_evidence[k]['unit']]) for k in LABELS}
  rows.append(dict(company=company,year=str(y),period='年度',scope='合并',currency='CNY',unit='元',**values,source=doc['url'],data_kind='公开资料待核验',report_title=doc['title'],fetched_at=doc['downloaded_at'],provenance={k:{**p,'value':values[k],'original_value':result[k][j],'sign_rule':'成本减项取绝对值' if k=='cost' and Decimal(result[k][j])<0 else '原值','unit':'元','original_unit':p['unit'],'year':y,'column_kind':'当期' if j==0 else '上期比较数','restatement':'需比较不同报告版本确认'} for k,p in field_evidence.items()}))
 return dict(rows=rows,legal_name=legal_name,evidence=field_evidence)
def acquire(entity,year,years,refresh=False):
 candidates=discover(entity,year,refresh);doc=candidates[0]
 raw,meta=fetch(doc['url'],refresh=refresh)
 doc={**doc,**meta,'status':'已下载','kind':'annual_pdf','fiscal_years':[year,year-1]}
 try:
  pages=pages_from_pdf(raw,doc);parsed=extract_cn(pages,doc,entity['name'],years)
 except SourceError as e:
  doc.update(status='已下载但解析未完成',error=str(e));e.document=doc;raise

 doc.update(status='已解析并登记字段',pages=len(pages),parsed_fields=list(parsed['evidence']),legal_name=parsed['legal_name'],alternative_versions=candidates[1:])
 return doc,parsed['rows']
