"""Legacy snapshot reader retained for archived studies and regression evidence.
Active research uses entities / annual_reports / sec_reports / research_pipeline.
No generated financial values or search-result snippets are used as financial data.
"""
import hashlib
import os
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parent
CATALOG={
 '贵州茅台':dict(code='600519',year=2024,published_at='2025-04-03',filename='moutai-2024.pdf',
  url='https://static.cninfo.com.cn/finalpage/2025-04-03/1222993920.PDF',title='贵州茅台2024年年度报告',
  balance_pages=[58,59,60],income_pages=[63,64],provenance_pages={'revenue':63,'cost':63,'net_profit':64,'assets':59,'liabilities':60}),
 '五粮液':dict(code='000858',year=2024,published_at='2025-04-26',filename='wuliangye-2024.pdf',
  url='https://disc.static.szse.cn/download/disc/disk03/finalpage/2025-04-26/e366c663-84d0-4700-a59a-00a7d6412d48.PDF',title='五粮液2024年年度报告',
  balance_pages=[56,57,58],income_pages=[60,61,62],provenance_pages={'revenue':60,'cost':61,'net_profit':61,'assets':57,'liabilities':58}),
}
LABELS={'revenue':'营业收入','cost':'营业成本','net_profit':'合并净利润','assets':'总资产','liabilities':'总负债'}
PATTERNS={'revenue':r'其中[：:]\s*营业收入','cost':r'其中[：:]\s*营业成本','net_profit':r'五[、.]\s*净利润','assets':r'(?m)^\s*资产总计','liabilities':r'(?m)^\s*负债合计'}
class RetrievalError(ValueError):pass
def utc():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def resolve(company):
    value=str(company).strip()
    for name,entry in CATALOG.items():
        if value in [name,entry['code'],name+'（'+entry['code']+'）']:return name
    raise RetrievalError('自动财报获取当前支持贵州茅台(600519)和五粮液(000858)。其他公司请导入带真实出处的财务表；不会生成替代数据。')

def extract_pair(text,key):
    match=re.search(PATTERNS[key],text)
    if not match:raise RetrievalError('年报未找到合并报表字段：'+LABELS[key])
    tail=text[match.start():match.start()+220]
    nums=list(re.finditer(r'-?\d[\d,]*\.\d{2}',tail))
    if len(nums)<2:raise RetrievalError('年报字段未取得两年数值：'+LABELS[key])
    # Exact excerpt includes PDF line breaks; normalized matcher handles whitespace.
    quote=tail[:nums[1].end()].strip()
    return [n.group().replace(',','') for n in nums[:2]],quote

def download(entry,refresh=False):
    folder=Path(os.environ.get('FINRESEARCH_DATA_DIR',ROOT/'data'))/'public-reports';folder.mkdir(parents=True,exist_ok=True)
    path=folder/entry['filename'];meta_path=path.with_suffix('.meta.json')
    if path.exists() and meta_path.exists() and not refresh:
        raw=path.read_bytes();meta=json.loads(meta_path.read_text(encoding='utf-8'))
        if hashlib.sha256(raw).hexdigest()!=meta['sha256']:raise RetrievalError('本地财报快照校验失败，请重新联网获取。')
        return path,{**meta,'retrieval_method':'真实年报本机快照','cached':True}
    req=urllib.request.Request(entry['url'],headers={'User-Agent':'Mozilla/5.0 FinResearch/0.2 PublicDisclosureReader'})
    try:
        with urllib.request.urlopen(req,timeout=40) as res:
            if res.geturl().split('/')[2] not in ['static.cninfo.com.cn','disc.static.szse.cn']:raise RetrievalError('披露来源重定向到未登记域名，获取已停止。')
            raw=res.read(20_000_001)
    except (urllib.error.URLError,TimeoutError,OSError):
        raise RetrievalError('公开年报下载失败：网络不可达、请求超时或披露站限制。原任务保留；可以重试或手动导入真实资料。')
    if len(raw)>20_000_000 or not raw.startswith(b'%PDF'):raise RetrievalError('披露站未返回支持范围内的PDF，未生成金融数据。')
    meta=dict(url=entry['url'],title=entry['title'],downloaded_at=utc(),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),retrieval_method='联网获取公开年报',cached=False)
    temp=path.with_suffix('.download');temp.write_bytes(raw);temp.replace(path)
    meta_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    return path,meta

def collect_company(company,refresh=False):
    company=resolve(company);entry=CATALOG[company]
    path,meta=download(entry,refresh)
    reader=PdfReader(path)
    pages={p:reader.pages[p-1].extract_text() or '' for p in set(entry['balance_pages']+entry['income_pages'])}
    balance='\n'.join(pages[p] for p in entry['balance_pages']).split('母公司资产负债表')[0]
    income='\n'.join(pages[p] for p in entry['income_pages']).split('合并利润表',1)[-1].split('母公司利润表')[0]
    pairs={};evidence={}
    for key in LABELS:
        values,quote=extract_pair(balance if key in ['assets','liabilities'] else income,key)
        pairs[key]=values;evidence[key]=dict(field=key,label=LABELS[key],page=entry['provenance_pages'][key],quote=quote,url=entry['url'],report_year=2024,unit='元',currency='CNY',scope='合并',sha256=meta['sha256'])
    rows=[]
    for j,year in enumerate([2024,2023]):
        rows.append(dict(company=company,year=str(year),period='年度',scope='合并',currency='CNY',unit='元',
                         **{key:pairs[key][j] for key in LABELS},source=entry['url'],data_kind='公开资料待核验',
                         provenance={k:{**v,'value':pairs[k][j],'year':year} for k,v in evidence.items()},
                         fetched_at=meta['downloaded_at'],report_title=entry['title'],published_at=entry['published_at']))
    return dict(company=company,entry=entry,meta=meta,rows=list(reversed(rows)),evidence=evidence)

def collect(companies,refresh=False,progress=lambda message:None):
    names=[resolve(c) for c in companies]
    if len(set(names))!=2:raise RetrievalError('请选择两家不同的公司。')
    result=[]
    # Sequential progress is intentional: preserve specific failed company in task history.
    for company in names:
        progress('正在读取'+company+'公开年报')
        result.append(collect_company(company,refresh))
    return result
