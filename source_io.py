"""Bounded public HTTPS retrieval, durable content hashes and explicit failures."""
import hashlib,json,re,socket,ipaddress,urllib.request,urllib.parse,time,uuid,os
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent
CACHE=Path(os.environ.get('FINRESEARCH_DATA_DIR',ROOT/'data'))/'research-documents'
class SourceError(ValueError):pass
def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def safe_url(url):
 p=urllib.parse.urlsplit(url)
 if p.scheme!='https' or not p.hostname or p.username or p.password or p.port not in [None,443]:raise SourceError('仅接受公开HTTPS资料网址。')
 try:
  addresses=socket.getaddrinfo(p.hostname,443)
  if any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):raise SourceError('不能访问本机、内网或保留地址。')
 except socket.gaierror:raise SourceError('资料网站域名无法解析，请稍后重试或上传文件。')
 return url
class Redirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  safe_url(newurl);return super().redirect_request(req,fp,code,msg,headers,newurl)
def fetch(url,data=None,refresh=False,limit=25_000_000,timeout=25):
 safe_url(url);CACHE.mkdir(parents=True,exist_ok=True)
 encoded=urllib.parse.urlencode(data).encode() if data is not None else None
 key=hashlib.sha256(url.encode()+(encoded or b'')).hexdigest()
 file=CACHE/(key+'.bin');meta_file=CACHE/(key+'.json')
 if file.exists() and meta_file.exists() and not refresh:
  raw=file.read_bytes();meta=json.loads(meta_file.read_text(encoding='utf-8'))
  if hashlib.sha256(raw).hexdigest()!=meta['sha256']:raise SourceError('资料缓存校验失败，请重新查找。')
  immutable=CACHE/(meta['sha256']+'.bin')
  if not immutable.exists():immutable.write_bytes(raw)
  return raw,{**meta,'filename':immutable.name,'cached':True,'retrieval_method':'已获取真实资料缓存'}
 origin=urllib.parse.urlsplit(url)
 referer='https://www.cninfo.com.cn/' if origin.hostname=='www.cninfo.com.cn' or (origin.hostname or '').endswith('.cninfo.com.cn') else f'https://{origin.netloc}/'
 req=urllib.request.Request(url,data=encoded,headers={'User-Agent':'FinResearch/0.3 academic research workspace','Referer':referer,'Accept':'application/json,text/html,application/pdf,*/*'})
 try:
  with urllib.request.build_opener(Redirect()).open(req,timeout=timeout) as r:
   start=time.monotonic();chunks=[];size=0
   while True:
    remaining=timeout-(time.monotonic()-start)
    if remaining<=0:raise TimeoutError('total download deadline')
    try:r.fp.raw._sock.settimeout(min(15 if timeout>25 else 5,remaining))
    except AttributeError:pass
    chunk=r.read1(min(65536,limit+1-size))
    if not chunk:break
    chunks.append(chunk);size+=len(chunk)
    if size>limit:break
   raw=b''.join(chunks);final=r.geturl();ctype=r.headers.get('Content-Type','')
 except urllib.error.HTTPError as e:raise SourceError('公开资料网站返回HTTP '+str(e.code)+'，未获取文件；可稍后重试或上传原文件。')
 except (OSError,TimeoutError,urllib.error.URLError):raise SourceError('公开资料暂不可达或请求超时；可重试或上传原文件。')
 if len(raw)>limit:raise SourceError('公开文件超过25 MB上限，请使用较小文件。')
 digest=hashlib.sha256(raw).hexdigest()
 meta=dict(id=key,url=url,final_url=final,sha256=digest,bytes=len(raw),content_type=ctype,downloaded_at=now(),filename=digest+'.bin',cached=False,retrieval_method='联网取得公开资料')
 immutable=CACHE/meta['filename']
 if not immutable.exists():immutable.write_bytes(raw)
 temporary=CACHE/(uuid.uuid4().hex+'.download');temporary.write_bytes(raw);temporary.replace(file)
 temporary=CACHE/(uuid.uuid4().hex+'.meta');temporary.write_text(json.dumps(meta,ensure_ascii=False),encoding='utf-8');temporary.replace(meta_file)
 return raw,meta
def json_fetch(url,data=None,refresh=False):
 raw,meta=fetch(url,data,refresh)
 try:return json.loads(raw),meta
 except (ValueError,UnicodeError):raise SourceError('资料接口未返回可解析内容，未将网页错误页当成数据。')
def clean(value):return re.sub(r'<[^>]+>','',str(value or '')).strip()
