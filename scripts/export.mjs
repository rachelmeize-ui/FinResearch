import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const cfg=JSON.parse(await fs.readFile(new URL('../runtime.local.json',import.meta.url),'utf8'));
const req=createRequire(path.join(cfg.modules||process.cwd(),'__finresearch__.cjs'));
const {Workbook,SpreadsheetFile}=await import(pathToFileURL(req.resolve('@oai/artifact-tool')).href);
const [input,output]=process.argv.slice(2);
const t=JSON.parse(await fs.readFile(input,'utf8'));
const wb=Workbook.create();
const latest=t.datasets.at(-1);
const safe=v=>typeof v==='string'&&/^[=+@-]/.test(v)?"'"+v:v;
function sheet(name,headers,rows,width=19){
  const s=wb.worksheets.add(name);s.showGridLines=false;
  const data=[headers,...rows.map(r=>r.map(v=>safe(v??'')))];
  s.getRangeByIndexes(0,0,data.length,headers.length).values=data;
  s.getRangeByIndexes(0,0,1,headers.length).format={fill:'#173C35',font:{bold:true,color:'#FFFFFF'},rowHeight:30,wrapText:true};
  s.getRangeByIndexes(1,0,Math.max(rows.length,1),headers.length).format.rowHeight=25;
  s.getRangeByIndexes(0,0,data.length,headers.length).format.columnWidth=width;
  s.freezePanes.freezeRows(1);return s;
}
const rs=latest?.rows||[];
const heads=[rs.some(r=>r.data_kind==='模拟数据')?'公司（含模拟数据）':'公司','年度','营业收入(亿元)','营业成本(亿元)','合并净利润(亿元)','总资产(亿元)','总负债(亿元)','毛利率','净利率','资产负债率','营收同比','行状态','数据性质','来源'];
const s=sheet('财务分析',heads,rs.map(r=>[r.company,r.year,r.revenue,r.cost,r.net_profit,r.assets,r.liabilities,r.gross_margin,r.net_margin,r.debt_ratio,r.revenue_yoy,r.valid?'可计算':'输入待修正',r.data_kind,r.source]));
s.getRange('N1:N'+(rs.length+1)).format.columnWidth=45;
s.getRange('N1:N'+(rs.length+1)).format.wrapText=true;
if(rs.length){
  s.getRange(`C2:G${rs.length+1}`).setNumberFormat('#,##0.0000;(#,##0.0000);"—"');
  s.getRange(`H2:K${rs.length+1}`).setNumberFormat('0.0%;(0.0%);"—"');
  s.getRange(`C2:G${rs.length+1}`).format.font.color='#1457A6';
  rs.forEach((r,i)=>{
    if(!r.valid)return;
    const n=i+2;
    for(const [col,f] of [['H',`=(C${n}-D${n})/C${n}`],['I',`=E${n}/C${n}`],['J',`=G${n}/F${n}`]])s.getRange(`${col}${n}`).formulas=[[f]];
    const p=rs.findIndex(x=>x.valid&&x.company===r.company&&x.year===r.year-1);
    if(p>=0&&rs[p].revenue>0)s.getRange(`K${n}`).formulas=[[`=(C${n}-C${p+2})/C${p+2}`]];
  });
}
const issues=sheet('核验问题',['行号','字段','规则','核验提示','严重程度','处理状态','处理意见','数据批次'],t.issues.map(i=>[i.row_no,i.field,i.code,i.message,i.severity,i.status,i.note,i.dataset_id]),24);
const ai=t.report?.ai;
const comparison=sheet('研究结论',['公司','研究维度','结论','性质','原文摘录','出处网址','核对状态'],[
 ...(t.report?.summary||[]).map(c=>[c.company,c.dimension,c.text,'披露数据与固定公式','',c.sources.map(p=>p.url+'#page='+p.page).join('\n'),'待人工核对']),
 ...(t.report?.business_cards||[]).map(c=>[c.company,c.dimension,c.text,c.kind,c.quote,c.url,c.status]),
 ...(ai?.cells||[]).map(c=>[c.company,c.dimension,c.text,'真实模型初稿 / '+(c.kind||'分析推断'),c.quote,c.url,c.status])],28);
const provenance=rs.flatMap(r=>Object.entries(r.provenance||{}).map(([key,p])=>[r.company,r.year,p.label,Number(p.value),p.unit,p.currency,p.scope,p.page||p.tag||'',p.url,p.sha256,p.version||'',p.restatement||'',JSON.stringify(p.versions||[])]));
const provenanceSheet=sheet('数据来源',['公司','报告期','字段','原始金额','原始单位','币种','口径','PDF页序 / XBRL标签','原始披露网址','SHA-256','选用版本','版本核对','历史版本值'],provenance,24);
if(provenance.length){provenanceSheet.getRange(`D2:D${provenance.length+1}`).setNumberFormat('#,##0.00');provenanceSheet.getRange(`I2:J${provenance.length+1}`).format.columnWidth=70;provenanceSheet.getRange(`I2:J${provenance.length+1}`).format.wrapText=true;provenanceSheet.getRange(`A2:J${provenance.length+1}`).format.rowHeight=45;}
const audit=sheet('处理日志',['时间 (UTC)','动作','实体','记录编号','变更前','变更后'],t.audit.map(a=>[a.created_at.replace('T',' ').replace('+00:00',' UTC'),a.action,a.entity,a.entity_id,a.before_json,a.after_json]),26);
for(const [tab,cols,count] of [[issues,['D','G'],t.issues.length],[comparison,['C','E','F'],(t.report?.summary?.length||0)+(t.report?.business_cards?.length||0)+(ai?.cells?.length||0)],[audit,['E','F'],t.audit.length]]){
 if(count){for(const col of cols){tab.getRange(`${col}2:${col}${count+1}`).format.columnWidth=60;tab.getRange(`${col}2:${col}${count+1}`).format.wrapText=true;}tab.getRange(`A2:H${count+1}`).format.rowHeight=72;}
}
audit.getRange('A1:A'+(t.audit.length+1)).format.columnWidth=34;
const methods=sheet('计算说明',['项目','定义'],[
 ['任务',t.title],['金额单位','所有金额统一到亿元；仅支持 CNY、合并、年度口径'],
 ['毛利率','(营业收入－营业成本)/营业收入；不使用净利润替代毛利润'],
 ['净利率','合并净利润/营业收入；非归母净利润口径'],['资产负债率','总负债/总资产；不是有息负债率'],
 ['营收同比','(本年收入－上年收入)/上年收入；仅相邻年度且同口径、上年收入大于零'],
 ['异常处置','处理状态不会修改原始数据。更正请导入新批次，旧批次记录保留。'],
 ['数据性质','正式研究使用真实公开披露；手动导入资料仍需人工核对。'],
 ['资料研究',ai?'真实模型 '+(t.report?.model_run?.model||'')+'；'+ai.created_at+'；研究初稿待人工核对':t.report?.ai_stale?'数据或来源变化，历史AI初稿未纳入当前报告':'当前仅有披露数据与固定计算结论，未生成AI研究初稿'],
 ['研究范围','研究年度：'+(t.report?.coverage?.requested_period||'待设置')+'；实际数据：'+(t.report?.coverage?.actual_period||'未取得')+'；'+(t.report?.coverage?.message||'所选年度覆盖完整。')+' 不含最新行情与估值。'],
 ['跨公司口径','茅台净利润含财务子公司损益，营业收入不含单列利息收入；净利率解释需留意业务结构。']
],45);
methods.getRange('A1:A12').format.columnWidth=22;
methods.getRange('B1:B12').format.columnWidth=110;
methods.getRange('B2:B12').format.wrapText=true;
methods.getRange('A2:B12').format.rowHeight=42;
wb.recalculate();
const check=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:10},maxChars:1500});
await fs.writeFile(output+'.check.json',check.ndjson);
if(process.env.FINRESEARCH_RENDER==='1'){
 for(const [sheetName,range] of [['财务分析','A1:K6'],['核验问题','A1:F5'],['研究结论','A1:D5'],['数据来源','A1:H6'],['处理日志','A1:D5'],['计算说明','A1:B12']]){
  const png=await wb.render({sheetName,range,scale:1,format:'png'});
  await fs.writeFile(output+'.'+sheetName+'.png',new Uint8Array(await png.arrayBuffer()));
 }
}
await (await SpreadsheetFile.exportXlsx(wb)).save(output);
