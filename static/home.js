/* Question-first creation surface. Existing API and research workspace stay shared. */
window.FinResearchHome = (() => {
  const storageKey = 'finresearch.home-draft.v1';
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const lastYear = new Date().getFullYear() - 1;
  const modes = {
    financial: {label:'财务研究', hint:'按公司与年度查找公开年报，比较财务表现和资产负债结构。', company:'公司名称或股票代码', placeholder:'输入公司名称或股票代码', question:'例如：比较两家公司的盈利能力、资产负债结构与风险。', outcome:'财务对比', outcomeText:'基于实际取得的财报，计算并比较财务指标。', dimensions:'收入与增长\n盈利能力\n资产与负债'},
    business: {label:'业务竞品', hint:'比较产品、商业模式与市场布局；未公开的财务数字不会估填。', company:'研究公司', placeholder:'输入公司名称', question:'例如：比较两家公司的产品组合、商业模式与主要市场。', outcome:'业务比较', outcomeText:'整理公开业务事实，明确可比信息与资料缺口。', dimensions:'产品组合\n商业模式\n主要市场\n竞争与风险'},
    industry: {label:'行业研究', hint:'按行业主题与问题查找公开证据；资料不足时明确列出信息缺口。', company:'行业或市场主题', placeholder:'例如：中国游戏行业', question:'例如：这个行业的产业链、竞争格局和监管风险有哪些？', outcome:'资料梳理', outcomeText:'按问题组织已取得资料，标注尚缺少的证据。', dimensions:'市场规模与增长\n产业链与商业模式\n竞争格局\n政策与风险'},
  };
  let draft = {research_type:'financial', question:'', company_a:'', company_b:'', comparison:false, start_year:lastYear-2, end_year:lastYear, dimensions:modes.financial.dimensions};
  try {
    const saved = JSON.parse(sessionStorage.getItem(storageKey));
    if (saved && typeof saved==='object') {
      for (const key of ['question','company_a','company_b','dimensions']) if (typeof saved[key]==='string') draft[key]=saved[key].slice(0,key==='question'?1000:2000);
      if (modes[saved.research_type]) draft.research_type=saved.research_type;
      for (const key of ['start_year','end_year']) if (/^\d{0,4}$/.test(String(saved[key]??''))) draft[key]=saved[key];
      draft.comparison=saved.comparison===true;
    }
  } catch {} // A blocked storage API must not prevent creating research.

  function icon(name) {
    const paths = {document:'<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M8 13h8M8 17h5"/>', evidence:'<path d="m10 13 4-4M8 16l-1 1a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0M16 8l1-1a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0" transform="translate(0 0) scale(.95)"/>', chart:'<path d="M4 3v17h17M8 15v-4M13 15V6M18 15V9"/>', search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>'};
    return `<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${paths[name]}</svg>`;
  }

  function form() {
    const m=modes[draft.research_type], compare=draft.comparison&&draft.research_type!=='industry';
    return `<section class="research-composer" aria-label="创建研究">
      <form id="new-form" class="composer-form">
        <div class="question-block"><label for="research-question" class="visually-hidden">研究问题</label>
          <textarea id="research-question" name="question" required maxlength="1000" aria-describedby="question-count" placeholder="${escape(m.question)}">${escape(draft.question)}</textarea>
          <div class="question-tools"><button type="button" class="home-text-button" data-home-action="example">填入一个研究示例</button><span id="question-count">${draft.question.length} / 1000</span></div>
        </div>
        <fieldset class="research-modes"><legend>研究类型</legend><div class="mode-options">${Object.entries(modes).map(([value,mode])=>`<label class="mode-option"><input type="radio" name="research_type" value="${value}" ${draft.research_type===value?'checked':''}><span>${mode.label}</span></label>`).join('')}</div></fieldset>
        <p id="mode-description" class="mode-description">${m.hint}</p>
        <div class="research-parameters">
          <div class="subject-controls"><label for="research-company"><span id="company-label">${m.company}</span><input id="research-company" name="company_a" required maxlength="80" placeholder="${m.placeholder}" value="${escape(draft.company_a)}" autocomplete="off"></label>
            <div id="compare-control" ${draft.research_type==='industry'?'hidden':''}><button type="button" class="compare-toggle" data-home-action="compare" aria-expanded="${compare}" aria-controls="comparison-field">${compare?'移除比较公司':'添加比较公司（可选）'}</button></div>
            <label id="comparison-field" ${compare?'':'hidden'}>比较公司<input name="company_b" maxlength="80" placeholder="输入另一家公司" value="${escape(draft.company_b)}" ${compare?'':'disabled'} autocomplete="off"></label>
          </div>
          <fieldset class="period-controls"><legend>研究年度</legend><div><label class="visually-hidden" for="research-start">起始年度</label><input id="research-start" name="start_year" type="number" min="1900" max="2099" value="${escape(draft.start_year)}" required inputmode="numeric"><span>至</span><label class="visually-hidden" for="research-end">结束年度</label><input id="research-end" name="end_year" type="number" min="1900" max="2099" value="${escape(draft.end_year)}" required inputmode="numeric"></div></fieldset>
        </div>
        <details class="advanced composer-advanced"><summary>调整研究维度（可选）</summary><label>每行一项，最多6项<textarea name="dimensions" required maxlength="360">${escape(draft.dimensions)}</textarea></label></details>
        <p id="home-form-feedback" class="home-form-feedback" role="status" aria-live="polite"></p>
        <div class="form-bottom composer-submit"><div><span>先查公开资料，不调用付费模型</span><small>填写内容暂存于当前浏览器会话</small></div><button type="submit" class="primary">${icon('search')}查找公开资料</button></div>
      </form>
      <aside class="research-outcomes" aria-labelledby="outcomes-title"><h2 id="outcomes-title">你将获得</h2><dl>
        <div><dt>${icon('chart')}<span id="outcome-name">${m.outcome}</span></dt><dd id="outcome-description">${m.outcomeText}</dd></div>
        <div><dt>${icon('evidence')}来源证据</dt><dd>保留原始出处、字段依据与待核验内容。</dd></div>
        <div><dt>${icon('document')}研究报告</dt><dd>预览并导出报告，保留来源与审核状态。</dd></div>
      </dl><p>资料可得性以公开披露为准；缺失信息会明确标出。</p></aside>
    </section>`;
  }

  function recent(tasks) {
    if (!tasks.length) return '<div class="home-no-research"><h3>还没有研究记录</h3><p>在上方填写问题和研究对象，开始第一项研究。保存后可在这里继续。</p></div>';
    return `<div class="home-study-list">${tasks.slice(0,3).map(t=>{
      const state=t.meta.engine_state||t.status, stateClass=/受阻|错误|冲突/.test(state)?'bad':/待|等待|中|未/.test(state)?'warn':/就绪|成功|完成|已生成|已确认/.test(state)?'good':'';
      return `<article class="home-study-row"><div><a class="study-title" href="#research/${escape(t.id)}">${escape(t.title)}</a><p>${escape(t.question)}</p></div><span class="home-study-period">${escape(t.coverage?.requested_period||'年度待设置')}</span><span class="status ${stateClass}">${escape(state)}</span><a class="button" href="#research/${escape(t.id)}">继续研究</a></article>`;
    }).join('')}</div>`;
  }

  function render(tasks) {
    return `<div class="home-heading"><h1>从一个问题，开始公司研究</h1><p>从公开资料到对比与报告，保留每一步证据。</p></div>${form()}<section class="home-recent" aria-labelledby="recent-title"><div class="section-heading"><h2 id="recent-title">最近研究</h2><a href="#studies">查看全部研究</a></div>${recent(tasks)}</section>`;
  }

  function capture(f) {
    draft={...draft,research_type:f.elements.research_type.value,question:f.elements.question.value,company_a:f.elements.company_a.value,company_b:f.elements.company_b.value,start_year:f.elements.start_year.value,end_year:f.elements.end_year.value,dimensions:f.elements.dimensions.value};
    try {sessionStorage.setItem(storageKey,JSON.stringify(draft));} catch {}
  }

  function update(f) {
    if (!f?.isConnected) return;
    const m=modes[f.elements.research_type.value], compare=draft.comparison&&f.elements.research_type.value!=='industry';
    document.querySelector('#question-count').textContent=f.elements.question.value.length+' / 1000';
    f.elements.question.placeholder=m.question;
    document.querySelector('#mode-description').textContent=m.hint;
    document.querySelector('#company-label').textContent=m.company;
    f.elements.company_a.placeholder=m.placeholder;
    document.querySelector('#compare-control').hidden=f.elements.research_type.value==='industry';
    document.querySelector('#comparison-field').hidden=!compare;f.elements.company_b.disabled=!compare;
    const toggle=f.querySelector('[data-home-action=compare]');toggle.setAttribute('aria-expanded',String(compare));toggle.textContent=compare?'移除比较公司':'添加比较公司（可选）';
    document.querySelector('#outcome-name').textContent=m.outcome;
    document.querySelector('#outcome-description').textContent=m.outcomeText;
    const start=Number(f.elements.start_year.value),end=Number(f.elements.end_year.value);
    f.elements.end_year.setCustomValidity(start>end?'结束年度不能早于起始年度。':end-start>20?'研究跨度最多20年，请缩小年度范围。':'');
    capture(f);
  }

  function showError(f,message) {
    const feedback=f.querySelector('#home-form-feedback');feedback.textContent=message;feedback.classList.add('has-error');
  }

  document.addEventListener('click',e=>{
    const button=e.target.closest('[data-home-action]');if(!button)return;
    const f=button.form;
    if (button.dataset.homeAction==='compare') {
      draft.comparison=!draft.comparison;update(f);
      if(draft.comparison)f.elements.company_b.focus();
      else f.querySelector('.entity-picks')?.remove();
    }
    if (button.dataset.homeAction==='example') {
      const type=f.elements.research_type.value, years=f.elements.start_year.value+'—'+f.elements.end_year.value;
      draft.comparison=type!=='industry';
      f.elements.company_a.value=type==='industry'?'中国游戏行业':type==='business'?'米哈游':'贵州茅台';
      f.elements.company_b.value=type==='business'?'网易':type==='financial'?'五粮液':'';
      f.elements.question.value=type==='financial'?`比较${years}年两家公司的收入增长、盈利能力与资产负债结构。`:type==='business'?`比较${years}年米哈游与网易的产品组合、商业模式、主要市场及风险，区分公开事实与信息缺口。`:`研究${years}年中国游戏行业的产业链、竞争格局及监管风险，说明公开资料的限制。`;
      f.querySelector('.entity-picks')?.remove();update(f);f.elements.question.focus();
    }
  });
  for (const event of ['input','change']) document.addEventListener(event,e=>{
    const f=e.target.form;if(f?.id!=='new-form')return;
    if(e.target.name==='research_type')f.querySelector('.entity-picks')?.remove();
    e.target.removeAttribute('aria-invalid');
    const feedback=f.querySelector('#home-form-feedback');feedback.textContent='';feedback.classList.remove('has-error');
    queueMicrotask(()=>update(f));
  });
  document.addEventListener('invalid',e=>{
    const f=e.target.form;if(f?.id!=='new-form')return;
    e.target.setAttribute('aria-invalid','true');
    const details=e.target.closest('details');if(details)details.open=true;
    showError(f,e.target.validity.valueMissing?'请填写研究问题、研究对象和年度，再查找资料。':e.target.validationMessage);
  },true);

  return {render,form,showError,clearDraft(){try{sessionStorage.removeItem(storageKey);}catch{}draft={research_type:'financial',question:'',company_a:'',company_b:'',comparison:false,start_year:lastYear-2,end_year:lastYear,dimensions:modes.financial.dimensions};}};
})();
