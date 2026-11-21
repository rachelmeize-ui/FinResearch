"""Server XLSX exporter with deterministic cached formulas; no desktop runtime."""
import io
import json
import xlsxwriter


def excel(t):
    output = io.BytesIO()
    wb = xlsxwriter.Workbook(output, {'in_memory': True, 'strings_to_formulas': False, 'strings_to_urls': False})
    header = wb.add_format({'bold': True, 'bg_color': '#173C35', 'font_color': '#FFFFFF', 'text_wrap': True})
    text = wb.add_format({'text_wrap': True, 'valign': 'top'})
    amount = wb.add_format({'num_format': '#,##0.0000;(#,##0.0000);"—"'})
    percent = wb.add_format({'num_format': '0.0%;(0.0%);"—"'})

    def sheet(name, columns, rows):
        ws = wb.add_worksheet(name)
        ws.hide_gridlines(2)
        ws.freeze_panes(1, 0)
        ws.set_column(0, len(columns)-1, 24, text)
        ws.set_row(0, 32)
        ws.write_row(0, 0, columns, header)
        for n, row in enumerate(rows, 1):
            ws.write_row(n, 0, [v if v is not None else '' for v in row], text)
        return ws

    rows = t['datasets'][-1]['rows'] if t['datasets'] else []
    ws = sheet('财务分析', ['公司', '年度', '营业收入(亿元)', '营业成本(亿元)', '合并净利润(亿元)', '总资产(亿元)', '总负债(亿元)', '毛利率', '净利率', '资产负债率', '营收同比', '行状态', '数据性质', '来源'], [
        [r.get(k) for k in ['company','year','revenue','cost','net_profit','assets','liabilities','gross_margin','net_margin','debt_ratio','revenue_yoy']] + ['可计算' if r['valid'] else '输入待修正', r.get('data_kind'), r.get('source')] for r in rows])
    ws.set_column('N:N', 65, text)
    for i, r in enumerate(rows, 1):
        for col, key in enumerate(['revenue','cost','net_profit','assets','liabilities'], 2):
            if isinstance(r.get(key), (float, int)): ws.write_number(i, col, r[key], amount)
        if not r['valid']: continue
        n = i+1
        for col, formula, key in [(7, f'=(C{n}-D{n})/C{n}', 'gross_margin'), (8, f'=E{n}/C{n}', 'net_margin'), (9, f'=G{n}/F{n}', 'debt_ratio')]:
            ws.write_formula(i, col, formula, percent, r[key])
        previous = next((j for j, p in enumerate(rows, 2) if p['valid'] and p['company']==r['company'] and p['year']==r['year']-1 and p['revenue']>0), None)
        if previous is not None:
            ws.write_formula(i, 10, f'=(C{n}-C{previous})/C{previous}', percent, r['revenue_yoy'])
    report = t['report']
    ai = report.get('ai') or {}
    facts = [[c['company'],c['dimension'],c['text'],'披露数据与固定公式','', '\n'.join(p['url']+(('#page='+str(p['page'])) if p.get('page') else '') for p in c['sources']),'待人工核对'] for c in report.get('summary', [])]
    facts += [[c.get(k,'') for k in ['company','dimension','text','kind','quote','url','status']] for c in report.get('business_cards', [])]
    facts += [[c['company'],c['dimension'],c['text'],'真实模型初稿 / '+c.get('kind','分析推断'),c['quote'],c['url'],c['status']] for c in ai.get('cells', [])]
    sheet('研究结论', ['公司','研究维度','结论','性质','原文摘录','出处网址','核对状态'], facts)
    provenance = []
    for r in rows:
        for p in r.get('provenance', {}).values():
            provenance.append([r['company'],r['year'],p.get('label'),float(p['value']),p.get('unit'),p.get('currency'),p.get('scope'),p.get('page') or p.get('tag',''),p.get('url'),p.get('sha256'),p.get('version',''),p.get('restatement',''),json.dumps(p.get('versions',[]),ensure_ascii=False)])
    sheet('数据来源', ['公司','报告期','字段','原始金额','原始单位','币种','口径','PDF页序 / XBRL标签','原始披露网址','SHA-256','选用版本','版本核对','历史版本值'], provenance)
    sheet('核验问题', ['行号','字段','规则','核验提示','严重程度','处理状态','处理意见','数据批次'], [[i.get(k,'') for k in ['row_no','field','code','message','severity','status','note','dataset_id']] for i in t['issues']])
    sheet('处理日志', ['时间 (UTC)','动作','实体','记录编号','变更前','变更后'], [[a.get(k,'') for k in ['created_at','action','entity','entity_id','before_json','after_json']] for a in t['audit']])
    coverage = report['coverage']
    methods = sheet('计算说明', ['项目','定义'], [
        ['任务',t['title']], ['金额单位','亿元；仅 CNY、合并、年度口径'],
        ['毛利率','(营业收入－营业成本)/营业收入'], ['净利率','合并净利润/营业收入，非归母净利润'], ['资产负债率','总负债/总资产'],
        ['营收同比','仅相邻年度、同口径且上年收入大于零'],
        ['研究范围', '研究年度：'+coverage['requested_period']+'；实际数据：'+coverage['actual_period']],
        ['来源与版本','字段级来源、页码或XBRL标签、历史版本均在数据来源页；不得将AI初稿视为人工核验结论。'],
        ['AI状态','真实模型初稿，待人工核对' if ai else '当前未纳入有效AI初稿'],
        *[['研究限制', c] for c in report.get('cautions', [])],
    ])
    methods.set_column('B:B', 100, text)
    wb.close()
    return output.getvalue()
