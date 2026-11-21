"""One-off, evidence-led refinements after recorded browser persona review."""
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'static/app.js'
s=p.read_text(encoding='utf-8')
if "history.scrollRestoration='manual'" not in s:s="history.scrollRestoration='manual';\n"+s
s=s.replace('async function route(){const [raw,id]',"async function route(){notice('');const [raw,id]")
s=s.replace("current=await api('/api/tasks/'+appState.tasks[0].id);render();}","current=await api('/api/tasks/'+appState.tasks[0].id);render();window.scrollTo(0,0);}")
start=s.index('function reportsPage()');end=s.index('function render()',start)
s=s[:start]+'''function reportsPage(){if(!current)return '<h1>报告中心</h1>'+emptyTask();const ai=!!current.report.ai;return `<h1>报告中心</h1><p class="muted">根据当前研究对象、数据批次和核对结果交付报告。</p>${context()}${jobPanel()}${!latest()?'<div class="step">资料尚未就绪，暂不能导出。<a href="'+link('research')+'">先获取真实资料</a></div>':`<div class="panel"><h2>导出当前研究</h2><div class="actions"><a class="download primary" href="/api/tasks/${current.id}/report.xlsx" download>下载 Excel</a><a class="download" href="/api/tasks/${current.id}/report.md" download>下载研究报告</a><a class="download" href="/api/tasks/${current.id}/report.html" target="_blank">查看可打印报告</a></div><p class="tiny">保留当前财务公式、字段来源、核验记录与结论。AI初稿需核对；数据变化后的旧初稿不作为当前结论。</p></div><h2>研究结论${ai?' · AI初稿':''}</h2>${ai?aiResults():aiResults()+financialConclusions()}${ai?'<details class="panel"><summary>查看财务计算摘要</summary>'+financialConclusions()+'</details>':''}<h2>研究范围与限制</h2><ul>${current.report.cautions.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`}`;}
''' +s[end:]
s=s.replace('<h2>财务分析结论</h2>${latest()?financialConclusions():\'<p class="muted">取得真实数据后显示计算结果及依据。</p>\'}', '<details class="panel"><summary>查看财务计算摘要</summary>${latest()?financialConclusions():\'<p class="muted">取得真实数据后显示计算结果及依据。</p>\'}</details>')
s=s.replace("notice(j.status==='blocked'?j.error:j.kind==='collect'?'真实财报已获取，财务分析已就绪。':'真实模型研究初稿已生成，待核对。',j.status==='blocked');","notice('');")
s=s.replace("const j=current?.jobs.at(-1);return", "const j=current?.jobs.at(-1);if(j?.kind==='model'&&current.report?.ai_stale)return '<div id=\"job-panel\"><div class=\"alert\">数据或来源已变化，上次AI初稿待更新。</div></div>';return")
p.write_text(s,encoding='utf-8')
