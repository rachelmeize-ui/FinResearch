"""Loopback-only HTTP API and static client, Python stdlib + read-only openpyxl.
Run: python server.py --port 8530
"""
import argparse
import base64
import binascii
import csv
import io
import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote
import finance
import research
import store
import periods
from store import db, uid, now, dumps, log, records, task, detail

ROOT=Path(__file__).resolve().parent
ISSUE_STATES=['未处理','处理中','已解决','已忽略']
OP_STATES=['待评估','计划中','进行中','已完成','暂缓']

def text(body,key,limit=500,required=True):
    val=body.get(key,'')
    if not isinstance(val,str):raise ValueError(key+' 必须是文本。')
    val=val.strip()
    if (required and not val) or len(val)>limit:raise ValueError(key+' 不能为空或超过 '+str(limit)+' 字。')
    return val

def create_task(body):
    title=text(body,'title',120); a=text(body,'company_a',80); b=text(body,'company_b',80,False)
    import public_data
    try:a=public_data.resolve(a)
    except ValueError:pass
    try:b=public_data.resolve(b)
    except ValueError:pass
    if a.casefold()==b.casefold():raise ValueError('请填写两家不同的公司。')
    q=text(body,'question',1000)
    requested_years=periods.requested(q,body)
    research_type=body.get('research_type','financial')
    if research_type not in ['financial','business','industry']:raise ValueError('请选择财务、业务竞品或行业研究类型。')
    selections=body.get('entity_selections',{})
    if not isinstance(selections,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in selections.items()):raise ValueError('企业主体选择格式无效。')
    dims=body.get('dimensions',[])
    if not isinstance(dims,list) or not 1<=len(dims)<=6 or any(not isinstance(d,str) or not d.strip() or len(d)>60 for d in dims) or len(set(dims))!=len(dims):
        raise ValueError('请输入 1—6 个不重复的研究维度。')
    ident=uid()
    with db() as c:
        c.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?)',(ident,title,a,b,q,dumps(dims),'待导入',now()))
        c.execute('INSERT INTO task_meta VALUES(?,?)',(ident,dumps({'visibility':'production','period':'尚未取得','requested_years':requested_years,'research_type':research_type,'entity_selections':selections,'engine_state':'等待获取资料'})))
        log(c,'task',ident,'创建',None,body)
    return detail(ident)

def import_data(ident,name,raw):
    if os.environ.get('FINRESEARCH_TEST_MODE')!='1' and any(r.get('data_kind')=='模拟数据' for r in raw):
        raise ValueError('正式研究只接受真实金融数据。模拟数据限独立测试环境，原有记录不会被覆盖。')
    if os.environ.get('FINRESEARCH_TEST_MODE')!='1':
        for row in raw:
            parsed=urlsplit(str(row.get('source','')))
            if parsed.scheme!='https' or not parsed.hostname or parsed.hostname.endswith('.invalid') or parsed.username or parsed.password:
                raise ValueError('每行真实数据需提供可核查的HTTPS出处网址。请补充来源后重新导入。')
    with db() as c:
        t=task(c,ident)
        rows,issues=finance.analyze(raw,[t['company_a'],t['company_b']])
        did=uid()
        c.execute('INSERT INTO datasets VALUES(?,?,?,?,?,?)',(did,ident,name,dumps(raw),dumps(rows),now()))
        for x in issues:
            c.execute('INSERT INTO issues VALUES(?,?,?,?,?,?,?,?,?,?,?)',(uid(),ident,did,x['row_no'],x['code'],x['field'],x['message'],x['severity'],x['status'],x['note'],now()))
        c.execute('UPDATE tasks SET status=? WHERE id=?',('待核验' if issues else '分析就绪',ident))
        m=c.execute('SELECT payload FROM task_meta WHERE task_id=?',(ident,)).fetchone()
        if m and 'AI' in json.loads(m['payload']).get('engine_state',''):
            import engine
            engine.meta_update(c,ident,engine_state='财务数据已更新，AI初稿待更新')
        import engine
        engine.meta_update(c,ident,period=periods.label(int(r['year']) for r in rows if r.get('valid')))
        log(c,'task',ident,'导入财务数据',None,{'dataset_id':did,'name':name,'rows':len(rows),'issues':len(issues)})
    return detail(ident)

def operation(body,ident=None):
    kind=text(body,'kind',30)
    if kind not in ['需求','反馈','Bug','改进任务']:raise ValueError('记录类型无效。')
    vals={k:text(body,k,n,k in ['title','priority','status']) for k,n in [('title',200),('persona',100),('pain',1000),('story',1000),('priority',2),('acceptance',1000),('status',10),('feature',120)]}
    if vals['priority'] not in ['P0','P1','P2'] or vals['status'] not in OP_STATES:raise ValueError('优先级或状态无效。')
    synthetic=int(body.get('synthetic') is True)
    with db() as c:
        before=None
        if ident:
            before=c.execute('SELECT * FROM operations WHERE id=?',(ident,)).fetchone()
            if not before:raise ValueError('需求或反馈不存在。')
            before=dict(before)
            c.execute('UPDATE operations SET kind=?,title=?,persona=?,pain=?,story=?,priority=?,acceptance=?,status=?,feature=?,synthetic=? WHERE id=?',(kind,*vals.values(),synthetic,ident))
        else:
            ident=uid()
            c.execute('INSERT INTO operations VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(ident,kind,*vals.values(),synthetic,now()))
        log(c,'operation',ident,'更新' if before else '新增',before,body)
    return {'id':ident}

def seed():
    with db() as c:
        if c.execute('SELECT COUNT(*) FROM operations').fetchone()[0]:return
    for body in [
        dict(title='导入年度财务数据并解释计算口径',persona='证券投资部实习生',pain='手工跨表计算容易混淆口径',story='作为研究实习生，我希望用同口径数据比较两家公司。',priority='P0',acceptance='CSV/XLSX 导入、指标计算、来源保留、Excel 导出均可执行。',feature='analysis',kind='需求'),
        dict(title='处理异常时保留原因和修改轨迹',persona='资管产品运营人员',pain='问题处理结果难追溯',story='作为运营人员，我希望逐项登记处理意见并恢复历史状态。',priority='P0',acceptance='四种状态、原因必填、更新日志及重启恢复验证。',feature='issues',kind='需求'),
        dict(title='首次打开知道从哪里开始',persona='首次使用者',pain='没有数据时不知道下一步',story='作为新用户，我希望加载示例后完整走通一个任务。',priority='P1',acceptance='空状态提供演示入口、模板及下一步提示。',feature='dashboard',kind='需求'),
    ]:
        operation({**body,'status':'已完成','synthetic':False})
    with db() as c:
        c.execute('INSERT OR IGNORE INTO releases VALUES(?,?,?,?)',('0.1.0','可核验的金融研究 MVP',dumps(['财务导入与计算','SQLite 需求和异常留痕','资料摘录与报告导出']),now()))

def api(method,path,body=None):
    body=body or {}
    parts=path.strip('/').split('/')
    if method=='POST' and (path=='/api/identify' or len(parts)==4 and parts[:2]==['api','tasks'] and parts[3] in ['resolve','upload-report','source-url']):
        import api_extensions
        return api_extensions.dispatch(path,body)
    if method=='GET' and path=='/api/state':
        import engine
        return engine.app_state()
    if method=='GET' and path=='/api/engine':
        import engine
        return engine.readiness()
    if method=='POST' and path=='/api/tasks':return create_task(body)
    if method=='POST' and path=='/api/demo':
        if os.environ.get('FINRESEARCH_TEST_MODE')!='1':raise ValueError('模拟案例已从正式产品移出，旧数据仍归档保存。请创建真实公司研究。')
        t=create_task({'title':'贵州茅台 vs 五粮液｜模拟数据练习','company_a':'贵州茅台','company_b':'五粮液','question':'练习财务趋势比较与数据质量核验；所有数字均为人为构造，不能用于真实公司判断。','dimensions':['收入与增长','盈利能力','资产与负债']})
        raw=finance.parse_file('demo.csv',(ROOT/'examples'/'demo.csv').read_bytes())
        t=import_data(t['id'],'demo.csv（模拟数据）',raw)
        for company in [t['company_a'],t['company_b']]:
            row=[r for r in t['datasets'][-1]['rows'] if r['company']==company][-1]
            snippets=[f"模拟案例：{company} 2024 年模拟营业收入为 {row['revenue']} 亿元，仅为测试值，不能用于真实公司研究。",
                      f"模拟案例：{company} 2024 年模拟合并净利润为 {row['net_profit']} 亿元；毛利率和净利率由模拟输入计算。",
                      f"模拟案例：{company} 2024 年模拟总资产 {row['assets']} 亿元、总负债 {row['liabilities']} 亿元。并非真实年报。"]
            for dimension,content in zip(t['dimensions'],snippets):
                t=api('POST','/api/tasks/'+t['id']+'/sources',dict(company=company,dimension=dimension,title='Synthetic source / 模拟资料',url='https://example.invalid/synthetic-demo',content=content,data_kind='模拟数据'))
        return t
    if len(parts)==3 and parts[:2]==['api','tasks'] and method=='GET':
        import engine,reporting
        t=detail(parts[2]);t['financial_summary']=engine.financial_summary(t)
        t['coverage']=periods.coverage(t)
        t['report']=reporting.state(t)
        return t
    if len(parts)==4 and parts[:2]==['api','tasks']:
        ident,action=parts[2:]
        if method=='POST' and action in ['collect','run-ai']:
            import engine
            return engine.launch(ident,'collect' if action=='collect' else 'model',body.get('refresh') is True)
        if method=='POST' and action=='import':
            name=text(body,'name',200)
            encoded=text(body,'content',2_800_000)
            try: content=base64.b64decode(encoded,validate=True)
            except (ValueError,binascii.Error):raise ValueError('文件内容损坏，请重新选择文件。')
            raw=finance.parse_file(name,content)
            return import_data(ident,name,raw)
        if method=='POST' and action=='sources':
            company=text(body,'company',80); dimension=text(body,'dimension',60)
            title=text(body,'title',200); url=text(body,'url',1200); content=text(body,'content',6000)
            parsed=urlsplit(url)
            if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:raise ValueError('出处必须是无账号密码的 HTTPS 网址。')
            kind=text(body,'data_kind',30)
            if kind not in ['模拟数据','公开资料待核验']:raise ValueError('资料性质无效。')
            if kind=='模拟数据' and os.environ.get('FINRESEARCH_TEST_MODE')!='1':raise ValueError('正式研究不能登记模拟资料。')
            with db() as c:
                t=task(c,ident)
                if company not in [t['company_a'],t['company_b']] or dimension not in t['dimensions']:raise ValueError('资料所属公司或维度不属于当前研究。')
                if c.execute('SELECT COUNT(*) FROM sources WHERE task_id=?',(ident,)).fetchone()[0]>=12:raise ValueError('一个任务最多 12 份资料。')
                sid=uid();c.execute('INSERT INTO sources VALUES(?,?,?,?,?,?,?,?,?)',(sid,ident,company,dimension,title,url,content,kind,now()))
                log(c,'task',ident,'登记资料',None,{'source_id':sid,'title':title,'url':url})
                import engine
                m=c.execute('SELECT payload FROM task_meta WHERE task_id=?',(ident,)).fetchone()
                payload=json.loads(m['payload']) if m else {}
                if payload.get('active_source_ids'):engine.meta_update(c,ident,active_source_ids=payload['active_source_ids']+[sid])
                if 'AI' in payload.get('engine_state',''):engine.meta_update(c,ident,engine_state='资料已更新，AI初稿待更新')
            return detail(ident)
        if method=='POST' and action=='research':
            t=detail(ident)
            cells,mode=research.generate(t,body.get('use_ai') is True)
            with db() as c:
                c.execute('INSERT INTO research VALUES(?,?,?,?,?)',(uid(),ident,dumps(cells),mode,now()))
                log(c,'task',ident,'生成资料比较',None,{'mode':mode,'cells':len(cells)})
            return detail(ident)
        if method=='POST' and action=='review':
            rid=text(body,'research_id',30); idx=body.get('index'); status=text(body,'status',20); value=text(body,'text',2500)
            if status not in ['待核实','人工已确认','资料不足','证据冲突']:raise ValueError('核对状态无效。')
            with db() as c:
                row=c.execute('SELECT * FROM research WHERE id=? AND task_id=?',(rid,ident)).fetchone()
                if not row:raise ValueError('研究结果不存在。')
                cells=json.loads(row['cells'])
                if not isinstance(idx,int) or isinstance(idx,bool) or not 0<=idx<len(cells):raise ValueError('比较项不存在。')
                old=cells[idx].copy()
                if status=='人工已确认' and (body.get('confirmed') is not True or not old.get('source_id')):raise ValueError('确认前请打开出处、阅读正文并勾选核对。')
                cells[idx].update(text=value,status=status)
                c.execute('UPDATE research SET cells=? WHERE id=?',(dumps(cells),rid))
                log(c,'task',ident,'修订研究结论',old,cells[idx])
            return detail(ident)
        if method=='POST' and action=='complete':
            t=detail(ident)
            if not t['datasets']:raise ValueError('请先导入财务数据。')
            latest=t['datasets'][-1]
            if any(i['dataset_id']==latest['id'] and i['status'] in ['未处理','处理中'] for i in t['issues']):raise ValueError('最新批次仍有未处理问题，请先记录处理结果。')
            if not any(r['valid'] for r in latest['rows']):raise ValueError('没有可计算的数据行，请更正数据后重新导入。')
            represented={r['company'] for r in latest['rows'] if r['valid']}
            if represented!={t['company_a'],t['company_b']}:raise ValueError('两家公司都需至少一行有效数据，才能结束比较任务的核验。')
            with db() as c:
                c.execute('UPDATE tasks SET status=? WHERE id=?',('已完成',ident));log(c,'task',ident,'结束本次核验',{'status':t['status']},{'status':'已完成'})
            return detail(ident)
    if method=='PATCH' and len(parts)==3 and parts[:2]==['api','issues']:
        status=text(body,'status',10);note=text(body,'note',2000)
        if status not in ISSUE_STATES:raise ValueError('异常处理状态无效。')
        with db() as c:
            old=c.execute('SELECT * FROM issues WHERE id=?',(parts[2],)).fetchone()
            if not old:raise ValueError('问题记录不存在。')
            c.execute('UPDATE issues SET status=?,note=?,updated_at=? WHERE id=?',(status,note,now(),parts[2]))
            log(c,'issue',parts[2],'变更处理状态',dict(old),body)
            latest=c.execute('SELECT id FROM datasets WHERE task_id=? ORDER BY rowid DESC LIMIT 1',(old['task_id'],)).fetchone()
            if latest and latest['id']==old['dataset_id'] and status in ['未处理','处理中']:
                t=task(c,old['task_id'])
                c.execute('UPDATE tasks SET status=? WHERE id=?',('待核验',old['task_id']))
                if t['status']=='已完成':log(c,'task',old['task_id'],'重新开启核验',{'status':t['status']},{'status':'待核验'})
        return {'ok':True}
    if path=='/api/operations' and method=='POST':return operation(body)
    if len(parts)==3 and parts[:2]==['api','operations'] and method=='PATCH':return operation(body,parts[2])
    raise ValueError('接口或操作不存在。')

def markdown(t):
    import reporting
    return reporting.markdown(t)

def legacy_markdown(t):
    latest=t['datasets'][-1] if t['datasets'] else None
    lines=['# '+t['title'],'',t['question'],'','状态：'+t['status'],'生成时间：'+now(),'',
           '## 数据口径','仅支持年度、合并、CNY。金额统一为亿元；净利润为合并净利润。模拟数据不能用于投资结论。',
           '处理问题的状态是人工记录，不会修改原始数据或自动证明数据正确。','', '## 财务指标']
    if latest:
        lines+=['数据批次：'+latest['name'],'|公司|年度|营业收入(亿元)|净利润(亿元)|毛利率|净利率|资产负债率|营收同比|来源|数据性质|','|---|---|---|---|---|---|---|---|---|---|']
        def fmt(v,ratio=False):return '不可计算' if v is None else (f'{v:.2%}' if ratio else f'{v:,.4f}')
        for r in latest['rows']:
            lines.append('|'.join(['',r['company'],str(r['year']),fmt(r['revenue']),fmt(r['net_profit']),*[fmt(r[k],True) for k in finance.RATIOS],r['source'].replace('|','/'),r['data_kind'],'']))
    lines+=['','## 计算说明',*['- '+v for v in finance.METHODS.values()],'','## 数据核验问题']
    for i in t['issues']:lines.append(f"- 第{i['row_no']}行 / {i['field']} / {i['message']} / {i['status']}：{i['note']}")
    lines+=['','## 资料比较']
    if t['research']:
        r=t['research'][-1];lines.append('生成方式：'+r['mode'])
        for cell in r['cells']:lines.extend(['',f"### {cell['company']} / {cell['dimension']}",cell['text'],'状态：'+cell['status'],'资料性质：'+cell['data_kind'],'原文摘录：'+cell['quote'],'出处：'+cell['url']])
    lines+=['','## 操作轨迹',*['- '+a['created_at']+' '+a['action'] for a in t['audit']]]
    return '\n'.join(lines)

class Handler(BaseHTTPRequestHandler):
    def respond(self,status,data,ctype='application/json; charset=utf-8',filename=None):
        if not isinstance(data,bytes):data=dumps(data).encode('utf-8')
        self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(data)))
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-store')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if filename:self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
        self.end_headers();self.wfile.write(data)
    def do_GET(self):self.handle_request('GET')
    def do_POST(self):self.handle_request('POST')
    def do_PATCH(self):self.handle_request('PATCH')
    def handle_request(self,method):
        try:
            host=self.headers.get('Host','')
            if host not in [f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}']:
                return self.respond(403,{'error':'仅允许本机访问。'})
            origin=self.headers.get('Origin')
            if method!='GET' and origin and origin not in ['http://'+host]:return self.respond(403,{'error':'请从本机工作台提交操作。'})
            path=unquote(urlsplit(self.path).path)
            if method=='GET' and path=='/api/template.csv':return self.respond(200,('\ufeff'+','.join(finance.ALIASES.keys())+'\n').encode('utf-8'),'text/csv; charset=utf-8','financial-template.csv')
            parts=path.strip('/').split('/')
            if method=='GET' and len(parts)==5 and parts[:2]==['api','tasks'] and parts[3]=='disclosures':
                import public_data
                from source_io import CACHE
                t=detail(parts[2]);doc=next((d for d in t.get('documents',[]) if d.get('record_id','')+'.pdf'==parts[4]),None)
                if doc:
                    raw=(CACHE/Path(doc['filename']).name).read_bytes()
                    return self.respond(200,raw,'application/pdf' if raw.startswith(b'%PDF') else 'application/json')
                t=detail(parts[2]);entry=next((e for name,e in public_data.CATALOG.items() if e['code']+'.pdf'==parts[4] and name in [t['company_a'],t['company_b']]),None)
                if not entry or not t['meta'].get('collection'):raise ValueError('该任务尚未获取对应原始披露文件。')
                pdf=ROOT/'data/public-reports'/entry['filename']
                return self.respond(200,pdf.read_bytes(),'application/pdf')
            if method=='GET' and len(parts)==4 and parts[:2]==['api','tasks'] and parts[-1] in ['report.md','report.xlsx','report.html']:
                t=detail(parts[2])
                if os.environ.get('FINRESEARCH_TEST_MODE')!='1' and t['meta'].get('visibility')=='archived_test':raise ValueError('旧模拟任务已归档，不生成正式研究报告。原文件保留在本机归档目录。')
                if not t['datasets'] and not t['meta'].get('business_cards'):raise ValueError('尚未取得研究资料，请先完成资料获取或导入。')
                if parts[-1]=='report.md':return self.respond(200,markdown(t).encode(),'text/markdown; charset=utf-8','research-report.md')
                if parts[-1]=='report.html':
                    import reporting
                    return self.respond(200,reporting.html_report(t).encode(),'text/html; charset=utf-8')
                from exporter import excel
                return self.respond(200,excel(t),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','financial-research.xlsx')
            if path.startswith('/api/'):
                length=int(self.headers.get('Content-Length','0'))
                if length>(34_100_000 if path.endswith('/upload-report') else 2_900_000):return self.respond(413,{'error':'请求过大，财务表限2 MB、年报PDF限25 MB。'})
                body=json.loads(self.rfile.read(length)) if length else {}
                if not isinstance(body,dict):raise ValueError('请求应为对象。')
                return self.respond(200,api(method,path,body))
            if method!='GET':return self.respond(405,{'error':'操作不支持。'})
            if path.startswith('/docs/'):
                filename=Path(path).name
                target=ROOT/'docs'/filename
                if target.suffix!='.md' or not target.is_file():return self.respond(404,{'error':'文档不存在。'})
                return self.respond(200,target.read_bytes(),'text/plain; charset=utf-8')
            target=ROOT/'static'/('index.html' if path=='/' else path.lstrip('/'))
            if os.environ.get('FINRESEARCH_TEST_MODE')!='1' and target.name in ['dirty.csv','legacy-app.js']:
                return self.respond(404,{'error':'测试资料不在正式研究界面提供。'})
            if not target.resolve().is_relative_to((ROOT/'static').resolve()) or not target.is_file():return self.respond(404,{'error':'页面不存在。'})
            ctype=mimetypes.guess_type(target)[0] or 'application/octet-stream'
            return self.respond(200,target.read_bytes(),ctype+'; charset=utf-8')
        except (ValueError,KeyError,TypeError,UnicodeError) as e:self.respond(400,{'error':str(e)[:400]})
        except Exception:
            import traceback;traceback.print_exc()
            self.respond(500,{'error':'操作未完成，已有数据仍保留。请查看本地运行日志或重试。'})
    def log_message(self,fmt,*args):
        print(self.log_date_time_string(),fmt%args,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8530);args=p.parse_args()
    store.init()
    s=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'FinResearch Workspace: http://127.0.0.1:{args.port}',flush=True)
    try:s.serve_forever()
    except KeyboardInterrupt:pass
    finally:s.server_close()
