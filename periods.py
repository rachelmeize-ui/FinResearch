"""Requested research years and actual company/year coverage are different facts."""
import re

DEFAULT_YEARS=[2023,2024]
YEAR=r'(?:19|20)\d{2}'
RANGE=re.compile(r'('+YEAR+r')\s*年?\s*(?:—|–|-|~|～|至|到)\s*('+YEAR+r')')

def label(years):
    years=sorted(set(years))
    if not years:return '尚未取得'
    if len(years)>1 and years==list(range(years[0],years[-1]+1)):
        return f'{years[0]}—{years[-1]}'
    return '、'.join(map(str,years))

def requested(question,body=None):
    body=body or {}
    if body.get('start_year') not in [None,''] or body.get('end_year') not in [None,'']:
        try:
            start=int(str(body.get('start_year','')));end=int(str(body.get('end_year','')))
        except (ValueError,TypeError):raise ValueError('请填写有效的起始年度和结束年度。')
        if not 1900<=start<=end<=2099 or end-start>20:
            raise ValueError('研究年度需在1900—2099年内，结束年度不得早于起始年度，跨度最多20年。')
        return list(range(start,end+1))
    found=RANGE.search(question or '')
    if found:
        return requested('',dict(start_year=found[1],end_year=found[2]))
    return sorted(set(map(int,re.findall(r'(?<!\d)('+YEAR+r')(?!\d)',question or '')))) or DEFAULT_YEARS.copy()

def coverage(t):
    wanted=t.get('meta',{}).get('requested_years') or requested(t.get('question',''))
    rows=t.get('datasets',[])
    rows=rows[-1]['rows'] if rows else []
    valid=[r for r in rows if r.get('valid')]
    actual=sorted({int(r['year']) for r in valid})
    per_company=[]
    for company in [x for x in [t['company_a'],t['company_b']] if x]:
        have=sorted({int(r['year']) for r in valid if r['company']==company})
        per_company.append(dict(company=company,actual_years=have,missing_years=sorted(set(wanted)-set(have))))
    missing=[x for x in per_company if x['missing_years']]
    message=('；'.join(x['company']+'缺少'+label(x['missing_years'])+'年数据' for x in missing)+'。当前仅能分析已取得的年度，尚未完成所选研究期间；请补充带真实出处的数据。') if missing and actual else ''
    return dict(requested_years=wanted,requested_period=label(wanted),actual_years=actual,actual_period=label(actual),
                companies=per_company,complete=not missing,status='覆盖完整' if not missing else '部分覆盖' if actual else '待获取',message=message)
