/* Responsive evidence-linked financial chart; shares the dashboard's chart library. */
window.FinResearchFinanceChart=(()=>{
  let instance=null,observer=null,taskId='',mode='auto',range=null,labels=[];
  const colors=['#3080ED','#9955DC'];
  function unmount(){observer?.disconnect();observer=null;if(instance){instance.dispose();instance=null;}}
  function view(title){return `<div class="finance-chart-controls" aria-label="图表年度范围"><div><button type="button" data-finance-window="all">全部年度</button><button type="button" data-finance-window="recent">最近5年</button></div><span id="finance-visible-years" aria-live="polite"></span></div><div id="finance-chart" class="finance-chart" role="group" tabindex="0" aria-label="${title}年度对比图"></div><div class="finance-chart-caption"><span>悬停查看数值，点击柱形核对来源；也可使用下方数据表。</span><button type="button" data-finance-table>查看数据与来源</button></div>`;}
  function extent(){
    if(range)return range;
    const recent=mode==='recent'||mode==='auto'&&document.querySelector('#finance-chart').clientWidth<600;
    return [recent?Math.max(0,labels.length-5):0,labels.length-1];
  }
  function describe(start,end){
    const el=document.querySelector('#finance-visible-years');if(!el)return;
    el.textContent=`显示 ${labels[start]}—${labels[end]}年 · 共${labels.length}个研究年度`;
    document.querySelectorAll('[data-finance-window]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.financeWindow==='all'?start===0&&end===labels.length-1:labels.length>5&&start===Math.max(0,labels.length-5)&&end===labels.length-1)));
  }
  function mount({id,rows,companies,years,key,title,percent,onSource,indexOfRow}){
    unmount();const el=document.querySelector('#finance-chart');if(!el)return;
    if(!window.echarts){el.innerHTML='<p>图表组件暂时无法载入，请使用下方财务数据表核对数值与来源。</p>';document.querySelectorAll('[data-finance-window]').forEach(button=>button.disabled=true);return;}
    if(taskId!==id){taskId=id;mode='auto';range=null;}
    labels=[...new Set(years)].sort((a,b)=>a-b).map(String);if(!labels.length)return;
    const narrow=el.clientWidth<600,[start,end]=extent();
    const selected=companies.filter(name=>rows.some(r=>r.company===name));
    instance=echarts.init(el,null,{renderer:'svg'});
    instance.setOption({animation:false,aria:{enabled:true},textStyle:{fontFamily:'"Segoe UI","Microsoft YaHei",sans-serif'},
      grid:{left:narrow?55:70,right:18,top:24,bottom:narrow?105:86},
      legend:{bottom:0,itemWidth:10,itemHeight:10,itemGap:18,textStyle:{fontSize:12,color:'#526174'}},
      tooltip:{trigger:'axis',confine:true,renderMode:'richText',valueFormatter:value=>value==null?'未取得':Number(value).toLocaleString('zh-CN',{maximumFractionDigits:2})+(percent?'%':'亿元')},
      xAxis:{type:'category',data:labels,axisTick:{show:false},axisLine:{lineStyle:{color:'#dce3ed'}},axisLabel:{fontSize:12,color:'#657187',hideOverlap:true,showMinLabel:true,showMaxLabel:true}},
      yAxis:{type:'value',splitNumber:4,axisLabel:{fontSize:11,color:'#657187',formatter:value=>Number(value).toLocaleString('zh-CN',{maximumFractionDigits:1})+(percent?'%':'')},splitLine:{lineStyle:{color:'#e8edf5',type:'dashed'}}},
      dataZoom:labels.length>5?[{type:'slider',bottom:37,height:18,startValue:labels[start],endValue:labels[end],showDataShadow:false,brushSelect:false,borderColor:'#dbe3ef',fillerColor:'#dce9fb',handleStyle:{color:'#3080ED',borderColor:'#3080ED'},textStyle:{fontSize:10,color:'#657187'},labelPrecision:0}]:[],
      series:selected.map(company=>({name:company,type:'bar',barMaxWidth:36,barGap:'18%',barCategoryGap:'28%',label:{show:false},itemStyle:{color:colors[companies.indexOf(company)%colors.length],borderRadius:[3,3,0,0]},data:labels.map(year=>{const r=rows.find(r=>r.valid&&r.company===company&&String(r.year)===year),index=r?indexOfRow(r):-1;return {value:r&&Number.isFinite(r[key])?r[key]*(percent?100:1):null,rowIndex:index,field:key};})}))
    });
    instance.on('click',event=>{if(event.data?.rowIndex>=0){el.focus({preventScroll:true});onSource(event.data.rowIndex,event.data.field);}});
    instance.on('datazoom',()=>{const zoom=instance.getOption().dataZoom?.[0];if(!zoom)return;const start=Math.round((zoom.start||0)*(labels.length-1)/100),end=Math.round((zoom.end??100)*(labels.length-1)/100);range=[start,end];describe(start,end);});
    document.querySelector('[data-finance-window=recent]').disabled=labels.length<=5;
    describe(start,end);
    observer=new ResizeObserver(()=>instance?.resize());observer.observe(el);
  }
  document.addEventListener('click',event=>{
    const preset=event.target.closest('[data-finance-window]');
    if(preset&&instance){mode=preset.dataset.financeWindow;range=null;const [start,end]=extent();if(labels.length>5)instance.dispatchAction({type:'dataZoom',start:start/(labels.length-1)*100,end:end/(labels.length-1)*100});describe(start,end);}
    if(event.target.closest('[data-finance-table]')){const table=document.querySelector('#finance-chart-data .scroll');table?.scrollIntoView({block:'start'});table?.focus({preventScroll:true});}
  });
  return {view,mount,unmount};
})();
