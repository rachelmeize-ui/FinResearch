"""SEC submissions + XBRL company facts; explicit form, period and currency checks."""
from source_io import fetch,json_fetch,SourceError
TAGS={'revenue':['RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet'],'cost':['CostOfGoodsAndServicesSold','CostOfRevenue'],'net_profit':['ProfitLoss'],'assets':['Assets'],'liabilities':['Liabilities']}
LABELS={'revenue':'营业收入','cost':'营业成本','net_profit':'合并净利润','assets':'总资产','liabilities':'总负债'}
def collect(entity,years,refresh=False,progress=lambda _:None):
 cik=entity['cik'];sub,sm=json_fetch('https://data.sec.gov/submissions/CIK'+cik.zfill(10)+'.json',refresh=refresh)
 facts,fm=json_fetch('https://data.sec.gov/api/xbrl/companyfacts/CIK'+cik.zfill(10)+'.json',refresh=refresh)
 r=sub['filings']['recent'];documents=[];rows=[];attempts=[]
 for year in years:
  progress(f'查找{entity["name"]}{year}年度20-F与XBRL')
  indices=[i for i,form in enumerate(r['form']) if form in ['20-F','20-F/A'] and r['reportDate'][i]==f'{year}-12-31']
  if not indices:attempts.append(dict(company=entity['name'],year=year,status='未找到',reason='SEC近期申报目录未返回该年度20-F，需历史目录或上传。'));continue
  i=indices[0];accn=r['accessionNumber'][i];url='https://www.sec.gov/Archives/edgar/data/'+str(int(cik))+'/'+accn.replace('-','')+'/'+r['primaryDocument'][i]
  doc=dict(id=fm['id']+'-'+str(year),company=entity['name'],title=entity['legal_name']+f' {year} Form 20-F / SEC XBRL',url=fm['url'],filing_url=url,report_year=year,published_at=r['filingDate'][i],accession=accn,kind='sec_xbrl',status='已取得官方结构化数据',**{k:v for k,v in fm.items() if k not in ['id','url']})
  try:
   filing_raw,html_meta=fetch(url,refresh=refresh,limit=15_000_000)
   if b'20-F' not in filing_raw or entity['legal_name'].split(',')[0].lower().encode() not in filing_raw.lower():raise SourceError('申报原文内容未通过20-F与企业名称核对。')
   doc['filing_download']='已取得20-F原文';doc['filing_document_id']=html_meta['id']
  except SourceError as e:doc['filing_download']=str(e);doc['alternative_source']='已合法取得SEC官方companyfacts，财务值按20-F accession关联；原文未下载成功'
  values={};provenance={};namespace=facts['facts'].get('us-gaap',{})
  for field,tags in TAGS.items():
   chosen=None;tag=None
   for candidate in tags:
    options=[x for x in namespace.get(candidate,{}).get('units',{}).get('CNY',[]) if x.get('form') in ['20-F','20-F/A'] and x.get('end')==f'{year}-12-31' and (field in ['assets','liabilities'] or x.get('start')==f'{year}-01-01')]
    exact=[x for x in options if x.get('accn')==accn]
    if exact:chosen=exact[-1];tag=candidate;break
   if chosen:
    values[field]=str(chosen['val']);provenance[field]=dict(field=field,label=LABELS[field],page=None,value=str(chosen['val']),quote=__import__('json').dumps(chosen,ensure_ascii=False),url=fm['url'],filing_url=url,report_year=year,year=year,unit='元',original_unit='CNY',currency='CNY',scope='合并',sha256=fm['sha256'],document_id=doc['id'],tag='us-gaap:'+tag,accession=accn,filed=chosen.get('filed'),column_kind='SEC年度事实',version=accn)
  if set(values)!=set(TAGS):
   doc.update(status='部分字段未能核验',error='缺少同一20-F/CNY/年度口径字段：'+','.join(set(TAGS)-set(values)))
  else:
   doc['status']='已核对20-F年度事实与币种';rows.append(dict(company=entity['name'],year=str(year),period='年度',scope='合并',currency='CNY',unit='元',**values,source=fm['url'],data_kind='公开资料待核验',report_title=doc['title'],fetched_at=fm['downloaded_at'],provenance=provenance))
  documents.append(doc);attempts.append(dict(company=entity['name'],year=year,status=doc['status'],source=url,reason=doc.get('error',''),filing_download=doc['filing_download']))
 return documents,rows,attempts
