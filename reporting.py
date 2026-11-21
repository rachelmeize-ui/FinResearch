"""One report state for all pages/exports; stale AI is not presented as current."""
import html
import finance
import engine
import periods
from store import now

CAUTIONS=[
 '本报告为已取得年度的历史财报分析，不代表最新经营或市场行情。',
 '净利润为合并净利润，包含少数股东损益；不同于归属于母公司股东的净利润。',
 '毛利率使用合并报表营业收入与营业成本计算，不等于年报的酒类分部毛利率。',
 '茅台合并净利润包含财务子公司损益，营业收入未包含单列利息收入；统一计算的净利率仍需结合业务结构解释。',
 '本期未接入股票行情或估值模型，不生成价格走势、买卖建议或收益承诺。',
]
def state(t):
    rows=engine.active_rows(t);did=t['datasets'][-1]['id'] if t['datasets'] else None
    ids=t['meta'].get('active_source_ids') or [s['id'] for s in t['sources'] if s['data_kind']!='模拟数据']
    runs=[r for r in t['model_runs'] if r['status']=='succeeded']
    run=runs[-1] if runs else None
    current=bool(run and run['dataset_id']==did and set(run['source_ids'])==set(ids))
    result=next((r for r in t['research'] if current and r['id']==run['research_id']),None)
    coverage=periods.coverage(t)
    business=t['meta'].get('effective_type',t['meta'].get('research_type')) in ['business','industry']
    cautions=([coverage['message']] if coverage['message'] and not business else [])+[x for x in CAUTIONS if '茅台' not in x or '贵州茅台' in [t['company_a'],t['company_b']]]
    if business:cautions=['业务资料为已取得公开原文摘录，非AI推论；当前网页不代表所选历史年度快照。','未取得可比经审计报表的企业不填入财务数值；第三方估算未作为事实。']
    return dict(rows=rows,summary=engine.financial_summary(t),ai=result,model_run=run,ai_stale=bool(run and not current),cautions=cautions,coverage=coverage,business_cards=t['meta'].get('business_cards',[]),research_type=t['meta'].get('effective_type',t['meta'].get('research_type','financial')),documents=t.get('documents',[]),issues=t.get('active_issues',[]))

def markdown(t):
    s=state(t);r=s['rows']
    if s['research_type'] in ['business','industry']:return business_markdown(t,s)
    coverage=s['coverage']
    lines=['# '+t['title'],'','研究问题：'+t['question'],'研究年度：'+coverage['requested_period'],'实际数据年度：'+coverage['actual_period'],'期间覆盖：'+coverage['status'],'生成时间：'+now()]
    if coverage['message'] and s['research_type']=='financial':lines+=['','**期间未完整覆盖：'+coverage['message']+'**']
    if s['research_type'] in ['business','industry']:
        lines+=['','研究类型：'+s['research_type'],'','## 公开业务资料比较（原文摘录，非AI推论）']
        for c in s['business_cards']:
            lines+=['',c['company']+' / '+c['dimension'],c['text'],'证据性质：'+c['kind'],'期间限制：'+c.get('date_scope','见原文'),'出处：'+c.get('url','资料不足')]
    lines+=['','## 研究结论（披露数据与固定公式）']
    for item in s['summary']:
        lines+=['- '+item['company']+' / '+item['dimension']+'：'+item['text']]
    lines+=['','## 财务数据与指标','金额：亿元；年度合并报表；币种：CNY；净利润口径：合并净利润。',
    '|公司|年度|营业收入|营业成本|合并净利润|总资产|总负债|毛利率|净利率|资产负债率|营收同比|数据性质|','|---|---|---|---|---|---|---|---|---|---|---|---|']
    def f(v,p=False):return '不可计算' if v is None else f'{v:.2%}' if p else f'{v:,.4f}'
    for x in r:lines.append('|'+ '|'.join([x['company'],str(x['year']),*[f(x[k]) for k in finance.MONEY],*[f(x[k],True) for k in finance.RATIOS],x['data_kind']])+'|')
    lines+=['','## AI研究初稿']
    if s['ai']:
        lines+=['实际模型：'+s['model_run']['model']+'；生成时间：'+s['ai']['created_at']+'；待人工核对。']
        for cell in s['ai']['cells']:
            lines+=['',f"### {cell['company']} / {cell['dimension']}",cell['text'],'性质：'+cell.get('kind','分析推断')+'；核对状态：'+cell['status'],'原文依据：'+cell['quote'],'出处：'+cell['url']]
    else:lines.append('当前数据尚无有效AI研究初稿。'+('数据或来源已变化，上次初稿未纳入当前报告。' if s['ai_stale'] else '财务结论为固定计算结果，未包装成AI生成。'))
    lines+=['','## 数据来源与字段核验']
    for row in r:
        lines+=['',f"### {row['company']} {row['year']}年度",'来源：'+row['source']]
        for key,p in row.get('provenance',{}).items():
            lines.append(f"- {p['label']}：原始金额{p['value']}元；{p['scope']}报表；定位：{('PDF第'+str(p['page'])+'页') if p.get('page') else p.get('tag','结构化字段')}；版本：{p.get('version','原披露版')}；对照：{p.get('restatement','请人工核对')}；{p['url']}#page={p['page']}；SHA-256：{p['sha256']}")
    if t['meta'].get('version_differences'):
        lines+=['','## 披露版本差异（待人工判断是否重述或口径调整）']
        for v in t['meta']['version_differences']:
            lines+=['- '+v['company']+' '+str(v['year'])+' '+v['field']+'：'+'；'.join(str(x['report_year'])+'年报 '+str(x['value'])+'元 '+x['source'] for x in v['versions'])]
    lines+=['','## 本次资料发现与取得记录']
    for d in t.get('documents',[]):
        lines+=['- '+d['title']+'；'+d['status']+'；'+d['url']+'；SHA-256：'+d['sha256']]
        if d.get('filing_url'):lines+=['20-F原始申报：'+d['filing_url']+'；原文获取状态：'+d.get('filing_download','未知')]
    for a in t.get('attempts',[]):lines+=['- '+a.get('company','')+' '+str(a.get('year',a.get('years','')))+'：'+a['status']+'；'+a.get('reason','')]
    lines+=['','## 数据核验']
    if not s['issues']:lines.append('当前批次未触发已实现规则；不等于真实数据无误，仍需人工核对原始披露。')
    for i in s['issues']:lines.append(f"- 第{i['row_no']}行 / {i['field']}：{i['message']}；{i['status']}；{i['note']}")
    lines+=['','## 计算口径',*['- '+v for v in finance.METHODS.values()],'','## 研究限制',*['- '+v for v in CAUTIONS]]
    return '\n'.join(lines)

def business_markdown(t,s):
    lines=['# '+t['title'],'','研究问题：'+t['question'],'研究年度：'+s['coverage']['requested_period'],
           '研究类型：'+('行业与市场资料研究' if s['research_type']=='industry' else '企业业务比较'),
           '证据性质：公开原文摘录，非AI推论；当前网页未证明为所选历史年度快照。','生成时间：'+now()]
    if t['meta'].get('route_reason'):lines+=['',t['meta']['route_reason']]
    lines+=['','## 公开资料比较（原文摘录，非AI推论）']
    for c in s['business_cards']:
        lines+=['','### '+c['company']+' / '+c['dimension'],c['text'],'核验状态：'+c['status'],'来源类型：'+c['kind'],'期间限制：'+c.get('date_scope','见原文')]
        if c.get('quote'):lines+=['原文依据：'+c['quote'],'出处：'+c['url']]
    lines+=['','## 资料来源及获取结果']
    for d in t.get('documents',[]):lines+=['- '+d['title']+'；'+d['url']+'；'+d['status']+'；SHA-256：'+d['sha256']]
    for a in t.get('attempts',[]):
        lines+=['- '+a.get('company','')+'：'+a['status']+'；'+a.get('reason','')]
        if a.get('search'):lines+=['实际检索：'+a['search']['query']+'；'+a['search']['status']]
    lines+=['','## 范围与限制',*['- '+c for c in s['cautions']]]
    return '\n'.join(lines)

def html_report(t):
    # Printable HTML uses the same report state; no second source of conclusions.
    chunks=[]
    for line in markdown(t).splitlines():
        text=html.escape(line)
        if line.startswith('### '):chunks.append('<h3>'+text[4:]+'</h3>')
        elif line.startswith('## '):chunks.append('<h2>'+text[3:]+'</h2>')
        elif line.startswith('# '):chunks.append('<h1>'+text[2:]+'</h1>')
        elif line.startswith('|'):chunks.append('<pre>'+text+'</pre>')
        elif line:chunks.append('<p>'+text+'</p>')
    return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>'+html.escape(t['title'])+'</title><link rel="stylesheet" href="/report.css"></head><body>'+''.join(chunks)+'</body></html>'
