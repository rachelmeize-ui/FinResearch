/* Read-only dashboard over saved research. No retrieval or model calls. */
window.FinResearchDashboard=(()=>{
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const labels={revenue:'营业收入',net_profit:'合并净利润',assets:'总资产',liabilities:'总负债',net_assets:'计算净资产',gross_margin:'毛利率',net_margin:'净利率',debt_ratio:'资产负债率',revenue_yoy:'营收同比'};
  const rules={gross_margin:'（营业收入－营业成本）÷ 营业收入',net_margin:'合并净利润 ÷ 营业收入',debt_ratio:'总负债 ÷ 总资产',revenue_yoy:'（本年营业收入－相邻上年营业收入）÷ 相邻上年营业收入',net_assets:'总资产－总负债'};
  const dependencies={gross_margin:['revenue','cost'],net_margin:['net_profit','revenue'],debt_ratio:['liabilities','assets'],revenue_yoy:['revenue'],net_assets:['assets','liabilities']};
  const colors=['#3080ED','#9955DC'];
  const percentage=k=>['gross_margin','net_margin','debt_ratio','revenue_yoy'].includes(k);
  const finite=v=>typeof v==='number'&&Number.isFinite(v);
  const format=(v,k)=>finite(v)?(percentage(k)?(v*100).toFixed(2)+'%':v.toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2})):'—';
  const eligible=tasks=>tasks.filter(t=>t.data_rows>0&&!['business','industry'].includes(t.meta?.effective_type||t.meta?.research_type));
  let task=null,year=null,assetCompany='',annualCompany='',balanceShape='pie',profitMetric='net_margin',serial=0,instances=[],observer=null,available=[],keywordItems=[],keywordCorpus=[];
  function saved(){const requested=new URLSearchParams(location.search).get('study');if(requested)return requested;try{return sessionStorage.getItem('finresearch.dashboard-study')||'';}catch{return '';}}
  function hasData(tasks){return eligible(tasks).length>0;}
  function view(tasks){
    const choices=eligible(tasks),selected=choices.find(t=>t.id===saved())||choices[0];
    if(!selected)return '<section class="dashboard-welcome"><h2>从第一份真实数据开始</h2><p>完成公司研究后，收入、盈利与资产结构图表会显示在这里。当前不使用示例数字填充看板。</p></section>';
    return `<section id="home-dashboard" aria-label="研究数据看板"><div class="dashboard-toolbar"><label>研究对象<select id="dashboard-task">${choices.map(t=>`<option value="${esc(t.id)}" ${t.id===selected.id?'selected':''}>${esc(t.title)} · ${esc(t.coverage?.requested_period||'年度待设置')}</option>`).join('')}</select></label><div id="dashboard-controls"></div></div><div id="dashboard-content" aria-busy="true"><div class="dashboard-loading" role="status">正在读取这份研究的财务数据与来源…</div></div></section>`;
  }
  function dispose(){for(const chart of instances)chart.dispose();instances=[];observer?.disconnect();observer=null;}
  function unmount(){serial++;dispose();}
  async function load(id){
    const request=++serial,root=document.querySelector('#home-dashboard');if(!root)return;
    dispose();document.querySelector('#dashboard-controls').innerHTML='';
    const content=document.querySelector('#dashboard-content');content.setAttribute('aria-busy','true');content.innerHTML='<div class="dashboard-loading" role="status">正在读取这份研究的财务数据与来源…</div>';
    try{
      const response=await fetch('/api/tasks/'+encodeURIComponent(id));const data=await response.json();if(!response.ok)throw Error(data.error||'无法读取这份研究。');
      if(request!==serial||!root.isConnected)return;
      task=data;const actual=years();if(!actual.includes(year))year=actual.at(-1);
      if(!companies().includes(assetCompany))assetCompany=companies()[0]||'';
      if(!companies().includes(annualCompany))annualCompany=companies()[0]||'';
      try{sessionStorage.setItem('finresearch.dashboard-study',id);}catch{}
      if(new URLSearchParams(location.search).has('study')){const url=new URL(location.href);url.searchParams.set('study',id);history.replaceState(null,'',url);}
      document.querySelector('#dashboard-controls').innerHTML=`<label>报表年度<select id="dashboard-year" ${actual.length?'':'disabled'}>${actual.map(y=>`<option ${y===year?'selected':''}>${y}</option>`).join('')||'<option>尚无有效数据</option>'}</select></label><a class="button" href="#research/${esc(id)}">进入研究</a><a class="button" href="/api/tasks/${esc(id)}/report.xlsx" download>导出 Excel</a>`;
      content.setAttribute('aria-busy','false');renderData();
    }catch(error){if(request!==serial||!root.isConnected)return;content.setAttribute('aria-busy','false');content.innerHTML=`<div class="dashboard-error" role="alert"><h2>暂时无法载入这份研究</h2><p>${esc(error.message)}</p><button type="button" data-dashboard-action="retry">重新读取</button><p>已保存的研究仍保留。也可以切换另一份研究，或创建新研究。</p></div>`;}
  }
  function mount(tasks){available=eligible(tasks);if(!document.querySelector('#home-dashboard'))return;load(document.querySelector('#dashboard-task').value);}
  function rows(){return (task?.datasets.at(-1)?.rows||[]).filter(r=>r.valid);}
  function companies(){return [...new Set([task?.company_a,task?.company_b].filter(Boolean))];}
  function years(){return [...new Set(rows().map(r=>r.year))].sort((a,b)=>a-b);}
  function rowFor(company,y){return rows().find(r=>r.company===company&&r.year===y);}
  function sourceButton(r,key){const value=key==='net_assets'&&r?r.assets-r.liabilities:r?.[key];return finite(value)?`<button type="button" class="dashboard-value" data-dashboard-company="${esc(r.company)}" data-dashboard-year="${r.year}" data-dashboard-field="${key}" aria-label="查看${esc(r.company)}${r.year}年${labels[key]}的来源">${format(value,key)}</button>`:'<span aria-label="尚未取得有效数据">—</span>';}
  function table(){
    const fields=['revenue','net_profit','gross_margin','net_margin','debt_ratio','revenue_yoy'];
    const sources=[];
    for(const company of companies())for(const p of Object.values(rowFor(company,year)?.provenance||{})){
      if(p.url&&!sources.some(s=>s.url===p.url)){const doc=task.documents?.find(d=>d.url===p.url);sources.push({url:p.url,title:doc?.title?(doc.title.includes(company)?doc.title:company+' · '+doc.title):company+' · '+(p.report_year||year)+'年正式披露'});}
    }
    return `<section class="dashboard-table-panel"><div class="dashboard-section-title"><h2>财务对照表</h2><span>${year||'—'}年度 · 合并 / CNY</span></div><div class="dashboard-table-scroll" tabindex="0" role="region" aria-label="公司财务对照报表"><table class="dashboard-compare-table"><thead><tr><th scope="col">财务指标</th>${companies().map((company,i)=>`<th scope="col"><span class="company-swatch series-${i}"></span>${esc(company)}</th>`).join('')}</tr></thead><tbody>${fields.map(k=>`<tr><th scope="row">${labels[k]}<small>${percentage(k)?'百分比':'亿元'}</small></th>${companies().map(company=>`<td class="num">${sourceButton(rowFor(company,year),k)}</td>`).join('')}</tr>`).join('')}</tbody></table></div><p class="dashboard-table-note">点击数字核对依据。合并净利润包含少数股东损益，规则计算仍需人工核对。</p><div class="dashboard-disclosures"><div><h3>披露依据</h3><a href="#sources/${esc(task.id)}">全部来源</a></div>${sources.slice(0,3).map(s=>`<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a>`).join('')||'<p>字段级出处请点击数值核对。</p>'}</div></section>`;
  }

  function panel(id,title,tools,note){return `<section class="dashboard-chart-panel"><div class="dashboard-chart-head"><h2>${title}</h2>${tools||''}</div><div id="dashboard-${id}" class="dashboard-chart" tabindex="0" role="group" aria-label="${title}图表"></div><div class="dashboard-chart-foot"><span>${note}</span><button type="button" data-dashboard-data="${id}">数据与来源</button></div></section>`;}
  function keywords(){
    const seen=new Set(),corpus=[];
    function add(label,text,url,kind){if(typeof text!=='string'||!text.trim()||seen.has(text.trim()))return;seen.add(text.trim());corpus.push({label,text:text.trim().normalize('NFKC'),url,kind});}
    add('研究问题',task.question,'#research/'+task.id,'用户提出的问题');
    for(const s of task.financial_summary||[])add(s.company+' / '+s.dimension,s.text,'#research/'+task.id,'固定公式财务摘要');
    for(const r of rows())for(const p of Object.values(r.provenance||{}))add(r.company+' '+r.year+' / '+p.label,p.quote,p.url,'已保存字段引文');
    for(const d of task.documents||[])add(d.company+' / 披露标题',d.title,d.url,'披露文件标题');
    keywordCorpus=corpus;
    const counts=new Map(),stop=new Set(['公司','年度','报告','其中','单位','本期','上期','本年','上年','万元','亿元','人民币','附注','数据','当前','说明','合并','进行','实际','研究','比较','两家','股份','有限','有限公司','股份有限公司','请','可以','根据','不是','没有','不能','同一','用于','包含','口径']);
    const terms=[...companies(),'营业收入','营业成本','合并净利润','净利润','净利率','毛利率','资产负债率','资产负债结构','总资产','总负债','负债合计','资产总计','盈利能力','收入增长','少数股东损益','股东权益','归母净利润','经营活动','现金流量','销售费用','管理费用','所得税','利润总额','研发','风险','市场','产品'].sort((a,b)=>b.length-a.length);
    function count(word,n=1){if(word.length>=2&&word.length<=14&&!stop.has(word)&&!/^\d/.test(word))counts.set(word,(counts.get(word)||0)+n);}
    for(const entry of corpus){let text=entry.text.replace(/[（(][^（）()]{0,20}(?:亏损|损失)[^（）()]{0,50}填列[^（）()]{0,20}[)）]/g,' ');for(const term of terms){const parts=text.split(term);if(parts.length>1){count(term,parts.length-1);text=parts.join(' ');}}
      if(Intl.Segmenter)for(const token of new Intl.Segmenter('zh-CN',{granularity:'word'}).segment(text))if(token.isWordLike&&/^[\u4e00-\u9fffA-Za-z]+$/.test(token.segment))count(token.segment);
    }
    keywordItems=[...counts].map(([word,count])=>({word,count})).sort((a,b)=>b.count-a.count||a.word.localeCompare(b.word,'zh-CN')).slice(0,26);
    const max=keywordItems[0]?.count||1;
    return `<section class="dashboard-chart-panel dashboard-keyword-panel"><div class="dashboard-chart-head"><h2>研究关键词</h2><span class="keyword-scope">前${Math.min(18,keywordItems.length)}词 · ${corpus.length}段摘录</span></div><div id="dashboard-keywords" class="dashboard-keyword-cloud" aria-label="研究摘录关键词，字号表示词频">${keywordItems.slice(0,18).map((item,i)=>`<button type="button" class="keyword-color-${i%6}" data-dashboard-keyword="${i}" data-word-size="${Math.round(14+14*Math.sqrt(item.count/max))}" aria-label="${esc(item.word)}，出现${item.count}次，查看相关摘录" title="${esc(item.word)} · ${item.count}次">${esc(item.word)}</button>`).join('')||'<p>当前摘录不足，暂无可提取的关键词。</p>'}</div><div class="dashboard-chart-foot"><span>摘录词频 · 不代表经营判断</span><button type="button" data-dashboard-data="keywords">词频与摘录</button></div></section>`;
  }
  function keywordEvidence(index){const item=keywordItems[index];if(!item)return;const snippets=keywordCorpus.filter(c=>c.text.includes(item.word));openDrawer(`<h3>${esc(item.word)} · ${item.count}次</h3><p>统计当前研究问题、摘要、保存的字段引文与披露标题；相同文本去重。排除了财报科目中的模板提示语；不是年报全文、行业热度或经营情绪统计。</p>${snippets.slice(0,8).map(c=>`<section class="evidence-item"><h3>${esc(c.label)}</h3><p>${esc(c.kind)}</p><blockquote>${esc(c.text.slice(0,900))}</blockquote><a href="${esc(c.url)}" ${c.url.startsWith('https:')?'target="_blank" rel="noopener"':''}>查看对应资料</a></section>`).join('')}`);}
  function renderData(){
    dispose();const content=document.querySelector('#dashboard-content');if(!content||!task)return;
    if(!rows().length){content.innerHTML=`<div class="dashboard-error"><h2>这份研究暂无可计算财务数据</h2><p>无效或缺失值不会当作零绘图。</p><a class="button" href="#sources/${esc(task.id)}">检查数据与来源</a></div>`;return;}
    if(!rowFor(assetCompany,year))assetCompany=companies().find(c=>rowFor(c,year))||'';
    content.innerHTML=`${task.coverage?.complete?'':`<div class="dashboard-coverage">研究年度 ${esc(task.coverage?.requested_period)}；实际数据 ${esc(task.coverage?.actual_period)}。${esc(task.coverage?.message||"缺失年度保留空位，不补造数值。")}</div>`}<div class="dashboard-main">${table()}<div class="dashboard-chart-grid">${panel('annual','年度收入',`<label class="visually-hidden" for="dashboard-annual-company">年度收入公司</label><select id="dashboard-annual-company">${companies().map(c=>`<option ${c===annualCompany?'selected':''}>${esc(c)}</option>`).join('')}</select>`,'亿元 · 颜色区分年度')}${panel('balance','资产结构',`<select id="dashboard-balance-company" aria-label="资产结构公司">${companies().filter(c=>rowFor(c,year)).map(c=>`<option ${c===assetCompany?'selected':''}>${esc(c)}</option>`).join('')}</select><select id="dashboard-balance-shape" aria-label="资产图形"><option value="pie" ${balanceShape==='pie'?'selected':''}>扇形图</option><option value="donut" ${balanceShape==='donut'?'selected':''}>环形图</option></select>`,`${year}年度 · 净资产＝总资产－总负债`)}${panel('profit','盈利趋势',`<label class="visually-hidden" for="dashboard-profit-metric">盈利指标</label><select id="dashboard-profit-metric"><option value="net_margin" ${profitMetric==='net_margin'?'selected':''}>净利率</option><option value="gross_margin" ${profitMetric==='gross_margin'?'selected':''}>毛利率</option></select>`,'百分比 · 缺失数据不连线')}${keywords()}${panel('revenue','收入与净利润对比',null,'亿元 · 实际取得年度 · 缺失值不补零')}</div></div><div class="dashboard-report-link"><span>图表来自已保存的真实财务记录，不含实时股价与市场估值。</span><a href="#reports/${esc(task.id)}">预览完整研究报告</a></div>`;
    document.querySelectorAll('[data-word-size]').forEach(el=>el.style.fontSize=el.dataset.wordSize+'px');

    if(!window.echarts){document.querySelectorAll('.dashboard-chart').forEach(el=>{el.innerHTML='<p class="chart-unavailable">图表组件未能载入。上方报表及“数据与来源”仍可使用。</p>';});return;}
    drawAll();
  }
  function common(id='profit'){const xs=task.coverage?.requested_years||years(),width=document.querySelector('#dashboard-'+id)?.clientWidth||600,step=Math.max(1,Math.ceil(xs.length/Math.max(3,Math.floor((width-82)/48))));return {animation:false,color:colors,textStyle:{fontFamily:'"Segoe UI","Microsoft YaHei",sans-serif',fontSize:12,color:'#526174'},aria:{enabled:true},tooltip:{trigger:'axis',confine:true,renderMode:'richText',valueFormatter:v=>finite(v)?v.toLocaleString('zh-CN',{maximumFractionDigits:2}):'未取得'},legend:{bottom:0,itemWidth:10,itemHeight:10,icon:'roundRect',textStyle:{fontSize:12,color:'#526174'}},grid:{left:60,right:22,top:24,bottom:56},xAxis:{type:'category',data:task.coverage?.requested_years||years(),axisTick:{show:false},axisLine:{lineStyle:{color:'#dce3ed'}},axisLabel:{color:'#657187',fontSize:12,hideOverlap:true,interval:index=>step===1||index===xs.length-1||(index%step===0&&xs.length-1-index>=step)}},yAxis:{type:'value',axisLabel:{color:'#657187',fontSize:11},splitLine:{lineStyle:{color:'#edf0f5',type:'dashed'}}}};}
  function series(key,type){const xs=task.coverage?.requested_years||years();return companies().map((company,index)=>({name:company,type,barMaxWidth:30,barGap:'24%',symbol:'circle',symbolSize:7,connectNulls:false,smooth:false,itemStyle:{color:colors[index%colors.length],borderRadius:type==='bar'?[3,3,0,0]:0},lineStyle:{width:2.5},areaStyle:type==='line'?{opacity:.06}:undefined,data:xs.map(y=>{const r=rowFor(company,y),value=r?.[key];return {value:finite(value)?value*(percentage(key)?100:1):null,company,year:y,field:key};})}));}
  function init(id,option){const el=document.querySelector('#dashboard-'+id);const instance=echarts.init(el,null,{renderer:'svg'});instance.setOption(option);instance.on('click',event=>{if(event.data?.company){el.focus({preventScroll:true});evidence(rowFor(event.data.company,event.data.year),event.data.field);}});instances.push(instance);return instance;}
  function drawAll(){
    const income=series('revenue','bar'),profit=series('net_profit','bar');
    income.forEach(v=>v.name+=' · 收入');profit.forEach((v,i)=>{v.name+=' · 净利润';v.itemStyle.color=['#69BCE8','#D296E8'][i%2];});
    const base=common('revenue'),small=document.querySelector('#dashboard-revenue').clientWidth<480;init('revenue',{...base,grid:{...base.grid,bottom:small?92:56},legend:{...base.legend,textStyle:{...base.legend.textStyle,fontSize:small?11:12},itemGap:small?8:10},series:[...income,...profit]});
    drawAnnual();drawProfit();drawBalance();

    observer=new ResizeObserver(()=>instances.forEach(chart=>chart.resize()));document.querySelectorAll('.dashboard-chart').forEach(el=>observer.observe(el));
  }
  function replaceChart(id){const el=document.querySelector('#dashboard-'+id),old=echarts.getInstanceByDom(el);if(old){instances=instances.filter(c=>c!==old);old.dispose();}return el;}
  function drawAnnual(){
    replaceChart('annual');const ys=[...(task.coverage?.requested_years||years())].sort((a,b)=>b-a),palette=['#3788F0','#A05BE0','#D66AB6','#E9AA45','#38AEB9','#56AB79','#638FE0','#AC72C6','#DC889F','#70B9A3'];
    init('annual',{animation:false,aria:{enabled:true},tooltip:{trigger:'item',renderMode:'richText',valueFormatter:v=>format(v,'revenue')+'亿元'},grid:{left:42,right:56,top:6,bottom:26},xAxis:{type:'value',axisLabel:{fontSize:10,color:'#718097'},splitLine:{lineStyle:{color:'#edf0f5'}}},yAxis:{type:'category',data:ys,inverse:true,axisTick:{show:false},axisLine:{show:false},axisLabel:{fontSize:11,color:'#657187'}},series:[{type:'bar',barMaxWidth:16,itemStyle:{borderRadius:[0,7,7,0]},label:{show:true,position:'right',color:'#526174',fontSize:10,formatter:p=>finite(p.value)?Math.round(p.value).toLocaleString('zh-CN'):''},data:ys.map((y,i)=>({value:rowFor(annualCompany,y)?.revenue??null,company:annualCompany,year:y,field:'revenue',itemStyle:{color:palette[i%palette.length]}}))}]});
  }
  function drawProfit(){replaceChart('profit');init('profit',{...common(),yAxis:{...common().yAxis,axisLabel:{formatter:v=>v+'%',color:'#657187'}},series:series(profitMetric,'line')});}
  function drawBalance(){
    replaceChart('balance');const r=rowFor(assetCompany,year);if(!r)return;
    const net=r.assets-r.liabilities;
    if(net<0){init('balance',{...common(),legend:{show:false},xAxis:{type:'category',data:['总资产','总负债']},series:[{type:'bar',data:[{value:r.assets,company:r.company,year:r.year,field:'assets',itemStyle:{color:'#16A394'}},{value:r.liabilities,company:r.company,year:r.year,field:'liabilities',itemStyle:{color:'#F2A43B'}}],barMaxWidth:60}]});return;}
    init('balance',{animation:false,aria:{enabled:true},tooltip:{trigger:'item',renderMode:'richText',confine:true,formatter:p=>`${p.name}\n${format(p.value,'assets')} 亿元（${p.percent}%）`},legend:{bottom:0,itemWidth:10,itemHeight:10,textStyle:{color:'#526174',fontSize:12}},graphic:balanceShape==='donut'?[{type:'text',left:'center',top:'34%',style:{text:format(r.assets,'assets'),fill:'#26364b',fontSize:22,fontWeight:600}},{type:'text',left:'center',top:'52%',style:{text:'总资产 · 亿元',fill:'#657187',fontSize:12}}]:[],series:[{type:'pie',radius:balanceShape==='donut'?['56%','76%']:['0%','76%'],center:['50%','43%'],avoidLabelOverlap:true,label:{show:false},itemStyle:{borderColor:'#fff',borderWidth:4,borderRadius:3},data:[{name:'总负债',value:r.liabilities,company:r.company,year:r.year,field:'liabilities',itemStyle:{color:'#F2A43B'}},{name:'计算净资产',value:net,company:r.company,year:r.year,field:'net_assets',itemStyle:{color:'#16A394'}}]}]});
  }
  function evidence(r,key){
    if(!r)return;const value=key==='net_assets'?r.assets-r.liabilities:r[key];let related=[r];
    if(key==='revenue_yoy'){const previous=rowFor(r.company,r.year-1);if(previous)related.push(previous);}
    const pieces=related.flatMap(row=>(dependencies[key]||[key]).map(field=>({row,field,p:row.provenance?.[field]})));
    openDrawer(`<h3>${esc(r.company)} · ${r.year}年 · ${labels[key]}</h3><div class="source-value">${format(value,key)}<small>${percentage(key)?'':'亿元'}</small></div><p>${esc(rules[key]||'原始披露字段，经统一单位换算。')}</p><p>合并 / CNY / 年度。数据仍需人工核对原文。</p>${pieces.map(({row,field,p})=>p?`<section class="evidence-item"><h3>${row.year} · ${esc(p.label||labels[field]||field)}</h3><dl><dt>原始金额</dt><dd>${esc(p.original_value??p.value)} ${esc(p.original_unit||p.unit)}</dd><dt>统一金额</dt><dd>${esc(p.value)} ${esc(p.unit)}</dd><dt>源报告年度</dt><dd>${esc(p.report_year||row.year)} · ${esc(p.column_kind||"按报表年度")}</dd><dt>年度列映射</dt><dd>${esc(p.column_rule||"按原报表年度列读取")}</dd><dt>页序 / 标签</dt><dd>${esc(p.page||p.tag||'请查原文')}</dd><dt>选用版本</dt><dd>${esc(p.version||p.report_year||'原始披露')}</dd></dl><blockquote>${esc((p.quote||'字段依据见原始披露或XBRL标签。').slice(0,900))}</blockquote><a href="${esc(p.url)}" target="_blank" rel="noopener">打开原始出处</a></section>`:`<p>${row.year}年${esc(labels[field]||field)}：没有已登记的字段级依据，请到来源与核验补充。</p>`).join('')}<p><a href="#sources/${esc(task.id)}" data-dashboard-close>查看这份研究的全部来源</a></p>`);
  }
  function dataView(kind){
    if(kind==='keywords'){openDrawer(`<h3>关键词统计范围</h3><p>当前保存的去重摘录与摘要词频，非年报全文统计。点击词语查看相关摘录。</p><div class="keyword-count-list">${keywordItems.map((k,i)=>`<button type="button" data-dashboard-keyword="${i}">${esc(k.word)} <span>${k.count}次</span></button>`).join('')}</div>`);return;}
    const keys=kind==='balance'?['assets','liabilities','net_assets']:kind==='revenue'?['revenue','net_profit']:[kind==='profit'?profitMetric:kind==='growth'?'revenue_yoy':'revenue'];
    const selected=kind==='balance'?rows().filter(r=>r.company===assetCompany&&r.year===year):kind==='annual'?rows().filter(r=>r.company===annualCompany):rows();
    openDrawer(`<h3>${{annual:'年度收入',revenue:'收入与净利润',profit:'盈利能力',balance:'资产负债结构',growth:'收入同比'}[kind]} · 数据与来源</h3><p>点击数值可查看字段、计算规则与原始披露。</p><div class="dashboard-table-scroll"><table><thead><tr><th>公司 / 年度</th>${keys.map(k=>`<th>${labels[k]}</th>`).join('')}</tr></thead><tbody>${selected.map(r=>`<tr><th scope="row">${esc(r.company)}<small>${r.year}</small></th>${keys.map(k=>`<td>${sourceButton(r,k)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`);
  }
  document.addEventListener('change',e=>{
    if(e.target.id==='dashboard-task')load(e.target.value);
    if(e.target.id==='dashboard-year'){year=Number(e.target.value);renderData();}
    if(e.target.id==='dashboard-profit-metric'){profitMetric=e.target.value;if(window.echarts)drawProfit();}
    if(e.target.id==='dashboard-annual-company'){annualCompany=e.target.value;if(window.echarts)drawAnnual();}
    if(e.target.id==='dashboard-balance-shape'){balanceShape=e.target.value;if(window.echarts)drawBalance();}
    if(e.target.id==='dashboard-balance-company'){assetCompany=e.target.value;if(window.echarts)drawBalance();}
  });
  document.addEventListener('click',e=>{
    const button=e.target.closest('[data-dashboard-field],[data-dashboard-data],[data-dashboard-action],[data-dashboard-close],[data-dashboard-keyword]');if(!button)return;
    if(button.hasAttribute('data-dashboard-keyword'))keywordEvidence(Number(button.dataset.dashboardKeyword));
    if(button.hasAttribute('data-dashboard-field'))evidence(rowFor(button.dataset.dashboardCompany,Number(button.dataset.dashboardYear)),button.dataset.dashboardField);
    if(button.dataset.dashboardData)dataView(button.dataset.dashboardData);
    if(button.dataset.dashboardAction==='retry')load(document.querySelector('#dashboard-task').value);
    if(button.hasAttribute('data-dashboard-close'))closeDrawer();
  });
  return {view,mount,unmount,hasData};
})();
