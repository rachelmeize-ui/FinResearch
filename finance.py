"""Annual consolidated RMB financial data; deterministic, no LLM calculations."""
import csv
import io
import math
import re
from collections import Counter
from decimal import Decimal, InvalidOperation

FIELDS = ['company','year','period','scope','currency','unit','revenue','cost','net_profit','assets','liabilities','source','data_kind']
ALIASES = dict(zip(['公司','年度','报告期','报表口径','币种','单位','营业收入','营业成本','净利润','总资产','总负债','来源','数据性质'], FIELDS))
MONEY = ['revenue','cost','net_profit','assets','liabilities']
RATIOS = ['gross_margin','net_margin','debt_ratio','revenue_yoy']
UNITS = {'元': Decimal(1), '万元': Decimal(10000), '亿元': Decimal(100000000)}
METHODS = {'gross_margin':'(营业收入－营业成本) ÷ 营业收入；营业成本不含期间费用',
           'net_margin':'合并净利润 ÷ 营业收入；不以归母净利润替代',
           'debt_ratio':'期末总负债 ÷ 期末总资产；不是有息负债率',
           'revenue_yoy':'(本年营业收入－上年营业收入) ÷ 上年营业收入；仅相邻年度、同币种同口径且上年收入>0时计算'}

def parse_file(name, content):
    if len(content) > 2_000_000:
        raise ValueError('文件超过 2 MB，请拆分后导入。')
    if name.lower().endswith('.csv'):
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = content.decode('gb18030')
        reader = csv.DictReader(io.StringIO(text))
        headers = reader.fieldnames or []
        rows = list(reader)
    elif name.lower().endswith('.xlsx'):
        import zipfile
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            if sum(x.file_size for x in z.infolist()) > 20_000_000:
                raise ValueError('Excel 解压后超过 20 MB，请减少内容。')
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=False)
        try:
            sheet = wb.worksheets[0]
            if (sheet.max_row or 0) > 1001 or (sheet.max_column or 0) > 40:
                raise ValueError('最多导入 1000 行、40 列。')
            values = sheet.iter_rows(values_only=True)
            headers = [str(x or '').strip() for x in next(values, [])]
            if len(headers)>40:raise ValueError('最多导入 40 列。')
            rows=[]
            for r in values:
                if any(x is not None for x in r):
                    if len(r)>40:raise ValueError('最多导入 40 列。')
                    rows.append(dict(zip(headers,r)))
                    if len(rows)>1000:raise ValueError('最多导入 1000 行。')
        finally:
            wb.close()
    else:
        raise ValueError('请选择 UTF-8/GB18030 CSV 或 .xlsx 文件；不支持旧版 .xls。')
    mapped = [ALIASES.get(str(h).strip(), str(h).strip()) for h in headers]
    if len(headers)>40:raise ValueError('最多导入 40 列。')
    if len(mapped) != len(set(mapped)):
        raise ValueError('存在重复或映射后重名的列，请检查表头。')
    missing = set(FIELDS) - set(mapped)
    if missing:
        raise ValueError('缺少列：' + '、'.join(sorted(missing)) + '。请下载模板。')
    if not rows or len(rows) > 1000:
        raise ValueError('请导入 1—1000 行数据。')
    return [{ALIASES.get(str(k).strip(), str(k).strip()): v for k,v in r.items() if k is not None} for r in rows]

def number(value):
    if value is None or str(value).strip() in ('', '--', 'NA', 'N/A', 'null'):
        return None
    text = str(value).strip().replace(',', '').replace('，', '')
    if text.startswith('(') and text.endswith(')'):
        text = '-' + text[1:-1]
    try:
        n = Decimal(text)
        if not n.is_finite() or abs(n) > Decimal('1e18'):
            raise ValueError('数值不在支持范围内')
        return n
    except InvalidOperation:
        raise ValueError('不是有效数值')

def analyze(raw_rows, companies):
    rows, issues = [], []
    def issue(i, code, field, message, severity='warning'):
        issues.append(dict(row_no=i, code=code, field=field, message=message, severity=severity, status='未处理', note=''))
    for i, raw in enumerate(raw_rows, 1):
        r = {k: raw.get(k) for k in FIELDS}
        r['provenance']=raw.get('provenance',{})
        r['fetched_at']=raw.get('fetched_at','')
        r['report_title']=raw.get('report_title','')
        r.update(row_no=i, raw=raw, valid=True, **{k:None for k in RATIOS})
        for f in ['company','period','scope','currency','unit','source','data_kind']:
            r[f] = str(r[f] or '').strip()
            if not r[f]:
                issue(i,'missing',f,'必填字段为空：'+f,'error'); r['valid']=False
        if r['company'] not in companies:
            issue(i,'company','company','公司不属于本任务的两家公司。','error'); r['valid']=False
        y = str(raw.get('year','')).strip()
        if re.fullmatch(r'(19|20)\d{2}(\.0)?', y):
            r['year'] = int(float(y))
        else:
            r['year'] = None; issue(i,'period','year','年度必须是 1900—2099 的整数。','error'); r['valid']=False
        for f, expected in [('period','年度'),('scope','合并'),('currency','CNY')]:
            if r[f] != expected:
                issue(i,'basis',f,f+' 仅支持 '+expected+'；不自动混算其他口径。','error'); r['valid']=False
        if r['data_kind'] not in ['模拟数据','公开资料待核验','人工核验数据']:
            issue(i,'kind','data_kind','数据性质需为模拟数据、公开资料待核验或人工核验数据。','error'); r['valid']=False
        factor = UNITS.get(r['unit'])
        if factor is None:
            issue(i,'unit','unit','仅支持元、万元、亿元；未知单位不参与计算。','error'); r['valid']=False
        for f in MONEY:
            try:
                v = number(raw.get(f))
                if v is None:
                    issue(i,'missing',f,'缺少金额：'+f,'error'); r['valid']=False
                r[f] = float(v * factor / Decimal(100000000)) if v is not None and factor is not None else None
            except ValueError:
                r[f] = None; r['valid']=False; issue(i,'type',f,'金额不是有限数值，不能用公式或文字代替。','error')
        for f in ['revenue','cost','assets','liabilities']:
            if r[f] is not None and r[f] < 0:
                issue(i,'negative',f,'出现负数，需要回查原始报表；不是财务造假判断。','error'); r['valid']=False
        if r['assets'] == 0:
            issue(i,'zero','assets','总资产为零，资产负债率不可计算。','error'); r['valid']=False
        if r['revenue'] == 0:
            issue(i,'zero','revenue','营业收入为零，毛利率与净利率不可计算。','error'); r['valid']=False
        if r['liabilities'] is not None and r['assets'] is not None and r['liabilities'] > r['assets']:
            issue(i,'range','liabilities','总负债大于总资产，需要核实（可能为负净资产）。')
        rows.append(r)
    counts = Counter((r['company'],r['year'],r['scope'],r['period'],r['currency']) for r in rows)
    for r in rows:
        i=r['row_no']
        if counts[(r['company'],r['year'],r['scope'],r['period'],r['currency'])] > 1:
            issue(i,'duplicate','year','同公司、年度、报表口径存在多行；不静默选第一行或相加。','error'); r['valid']=False
    lookup={(r['company'],r['year'],r['scope'],r['period'],r['currency']):r for r in rows if r['valid']}
    for r in rows:
        if not r['valid']: continue
        r['gross_margin']=(r['revenue']-r['cost'])/r['revenue']
        r['net_margin']=r['net_profit']/r['revenue']
        r['debt_ratio']=r['liabilities']/r['assets']
        prev=lookup.get((r['company'],r['year']-1,r['scope'],r['period'],r['currency']))
        if prev and prev['revenue'] > 0:
            r['revenue_yoy']=(r['revenue']-prev['revenue'])/prev['revenue']
            if abs(r['revenue_yoy']) > 1:
                issue(r['row_no'],'outlier','revenue_yoy','营业收入同比变化超过 100%；规则提示，需人工解释。')
        for key in ['gross_margin','net_margin','debt_ratio']:
            if not -1 <= r[key] <= 1:
                issue(r['row_no'],'outlier',key,'比率超出 [-100%,100%]，请核实业务原因与输入。')
        # Optional source-stated ratios, entered as decimals, independently reconciled.
        for key in RATIOS:
            if raw_rows[r['row_no']-1].get(key) not in (None,''):
                try:
                    reported=number(raw_rows[r['row_no']-1][key])
                    if r[key] is not None and abs(float(reported)-r[key]) > .0001:
                        issue(r['row_no'],'ratio_mismatch',key,'导入比率与重算差异超过 0.01 个百分点。')
                except (ValueError,TypeError):
                    issue(r['row_no'],'type',key,'导入比率必须为小数，例如 0.25 表示 25%。')
    return rows,issues
