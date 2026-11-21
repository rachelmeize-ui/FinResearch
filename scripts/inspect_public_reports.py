import json
from pathlib import Path
import urllib.request
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]
sources={
 'moutai-2024':'https://static.cninfo.com.cn/finalpage/2025-04-03/1222993920.PDF',
 'wuliangye-2024':'https://disc.static.szse.cn/download/disc/disk03/finalpage/2025-04-26/e366c663-84d0-4700-a59a-00a7d6412d48.PDF',
}
folder=ROOT/'data/public-reports';folder.mkdir(parents=True,exist_ok=True)
for name,url in sources.items():
 p=folder/(name+'.pdf')
 if not p.exists():
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 FinResearch public disclosure reader'})
  with urllib.request.urlopen(req,timeout=40) as res:raw=res.read(20_000_001)
  if len(raw)>20_000_000 or not raw.startswith(b'%PDF'):raise ValueError('Not a bounded public PDF')
  p.write_bytes(raw)
 reader=PdfReader(p);pages=[x.extract_text() or '' for x in reader.pages]
 (folder/(name+'-pages.json')).write_text(json.dumps(pages,ensure_ascii=False),encoding='utf-8')
 print(name,'pages',len(pages))
 for i,s in enumerate(pages):
  compact=''.join(s.split())
  if ('合并资产负债表' in compact or '合并利润表' in compact) and ('流动资产' in compact or '营业总收入' in compact):
   print('PAGE',i+1);print(s[:11000])
