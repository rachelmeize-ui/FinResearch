import sys,json,urllib.request,urllib.parse
from pathlib import Path
OUT=Path('test-results/engine-v3/probes');OUT.mkdir(parents=True,exist_ok=True)
def get(name,url,data=None):
 try:
  req=urllib.request.Request(url,data=urllib.parse.urlencode(data).encode() if data else None,headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.cninfo.com.cn/','Accept':'application/json,text/html,*/*'})
  with urllib.request.urlopen(req,timeout=30) as r:b=r.read(12_000_000)
  (OUT/(name+'.txt')).write_bytes(b)
  try:obj=json.loads(b);print(name,json.dumps(obj,ensure_ascii=True)[:2600])
  except Exception:print(name,'bytes',len(b),b[:100])
 except Exception as e:print(name,type(e).__name__,str(e))
get('top','https://www.cninfo.com.cn/new/information/topSearch/query',dict(keyWord='贵州茅台',maxSecNum=10,maxListNum=10))
get('stocks','https://www.cninfo.com.cn/new/data/szse_stock.json')
get('ann','https://www.cninfo.com.cn/new/hisAnnouncement/query',dict(pageNum=1,pageSize=30,column='szse',tabName='fulltext',stock='600519,gssh0600519',searchkey='2025年年度报告',seDate='2026-01-01~2026-12-31',isHLtitle='true',sortName='time',sortType='desc'))
get('netease','https://ir.netease.com/financial-information/annual-reports')
get('mihoyo','https://www.mihoyo.com/')
