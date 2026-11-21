import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def uid(): return uuid.uuid4().hex[:16]
def dumps(x): return json.dumps(x,ensure_ascii=False,allow_nan=False)

@contextmanager
def db():
    path=Path(os.environ.get('FINRESEARCH_DB',ROOT/'data'/'workspace.sqlite3'))
    path.parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(path,timeout=15)
    c.row_factory=sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    try:
        with c: yield c
    finally: c.close()

def init():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,title TEXT,company_a TEXT,company_b TEXT,question TEXT,dimensions TEXT,status TEXT,created_at TEXT);
        CREATE TABLE IF NOT EXISTS datasets(id TEXT PRIMARY KEY,task_id TEXT REFERENCES tasks(id),name TEXT,raw TEXT,rows TEXT,created_at TEXT);
        CREATE TABLE IF NOT EXISTS issues(id TEXT PRIMARY KEY,task_id TEXT REFERENCES tasks(id),dataset_id TEXT REFERENCES datasets(id),row_no INTEGER,code TEXT,field TEXT,message TEXT,severity TEXT,status TEXT,note TEXT,updated_at TEXT);
        CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY,task_id TEXT REFERENCES tasks(id),company TEXT,dimension TEXT,title TEXT,url TEXT,content TEXT,data_kind TEXT,created_at TEXT);
        CREATE TABLE IF NOT EXISTS research(id TEXT PRIMARY KEY,task_id TEXT REFERENCES tasks(id),cells TEXT,mode TEXT,created_at TEXT);
        CREATE TABLE IF NOT EXISTS operations(id TEXT PRIMARY KEY,kind TEXT,title TEXT,persona TEXT,pain TEXT,story TEXT,priority TEXT,acceptance TEXT,status TEXT,feature TEXT,synthetic INTEGER,created_at TEXT);
        CREATE TABLE IF NOT EXISTS audit(id TEXT PRIMARY KEY,entity TEXT,entity_id TEXT,action TEXT,before_json TEXT,after_json TEXT,created_at TEXT);
        CREATE TABLE IF NOT EXISTS releases(version TEXT PRIMARY KEY,title TEXT,changes TEXT,created_at TEXT);
        CREATE TABLE IF NOT EXISTS task_meta(task_id TEXT PRIMARY KEY REFERENCES tasks(id),payload TEXT);
        CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,task_id TEXT REFERENCES tasks(id),kind TEXT,status TEXT,stage TEXT,error TEXT,started_at TEXT,finished_at TEXT);
        CREATE UNIQUE INDEX IF NOT EXISTS one_running_job_per_task ON jobs(task_id) WHERE status='running';
        CREATE TABLE IF NOT EXISTS model_runs(id TEXT PRIMARY KEY,task_id TEXT REFERENCES tasks(id),dataset_id TEXT,research_id TEXT,provider TEXT,model TEXT,status TEXT,usage TEXT,error TEXT,created_at TEXT);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
        CREATE TABLE IF NOT EXISTS research_documents(id TEXT PRIMARY KEY,task_id TEXT REFERENCES tasks(id),payload TEXT,created_at TEXT);
        CREATE TABLE IF NOT EXISTS research_attempts(id TEXT PRIMARY KEY,task_id TEXT REFERENCES tasks(id),payload TEXT,created_at TEXT);
        ''')
        if 'source_ids' not in [r['name'] for r in c.execute('PRAGMA table_info(model_runs)')]:
            c.execute("ALTER TABLE model_runs ADD COLUMN source_ids TEXT NOT NULL DEFAULT '[]'")
        if not c.execute("SELECT 1 FROM settings WHERE key='refocus_migrated'").fetchone():
            for record in records(c,'tasks'):
                data=records(c,'datasets','task_id=?',(record['id'],))
                simulated=any(r.get('data_kind')=='模拟数据' for batch in data for r in json.loads(batch['rows']))
                c.execute('INSERT OR IGNORE INTO task_meta VALUES(?,?)',(record['id'],dumps({'visibility':'archived_test' if simulated else 'production','legacy':True})))
            c.execute("INSERT INTO settings VALUES('refocus_migrated','1')")

def log(c,entity,entity_id,action,before,after):
    c.execute('INSERT INTO audit VALUES(?,?,?,?,?,?,?)',(uid(),entity,entity_id,action,dumps(before),dumps(after),now()))

def records(c,table,where='',args=()):
    # Table/where supplied only by application constants, never request strings.
    return [dict(x) for x in c.execute('SELECT * FROM '+table+(' WHERE '+where if where else ''),args)]

def task(c,ident):
    r=c.execute('SELECT * FROM tasks WHERE id=?',(ident,)).fetchone()
    if not r: raise ValueError('研究任务不存在。')
    t=dict(r);t['dimensions']=json.loads(t['dimensions']);return t

def detail(ident):
    with db() as c:
        t=task(c,ident)
        # rowid preserves insertion order even when two writes share a timestamp.
        t['datasets']=records(c,'datasets','task_id=? ORDER BY rowid',(ident,))
        for d in t['datasets']:
            d['rows']=json.loads(d['rows']);d['raw']=json.loads(d['raw'])
        t['issues']=records(c,'issues','task_id=?',(ident,))
        t['sources']=records(c,'sources','task_id=?',(ident,))
        t['research']=records(c,'research','task_id=? ORDER BY rowid',(ident,))
        for r in t['research']:r['cells']=json.loads(r['cells'])
        t['audit']=records(c,'audit','entity_id IN (SELECT id FROM issues WHERE task_id=?) OR entity_id=? ORDER BY created_at',(ident,ident))
        m=c.execute('SELECT payload FROM task_meta WHERE task_id=?',(ident,)).fetchone()
        t['meta']=json.loads(m['payload']) if m else {'visibility':'production'}
        t['jobs']=records(c,'jobs','task_id=? ORDER BY rowid',(ident,))
        t['model_runs']=records(c,'model_runs','task_id=? ORDER BY rowid',(ident,))
        for run in t['model_runs']:
            run['usage']=json.loads(run['usage']);run['source_ids']=json.loads(run['source_ids'])
        t['active_issues']=[i for i in t['issues'] if t['datasets'] and i['dataset_id']==t['datasets'][-1]['id']]
        t['documents']=[json.loads(r['payload']) for r in records(c,'research_documents','task_id=? ORDER BY rowid',(ident,))]
        t['attempts']=[json.loads(r['payload']) for r in records(c,'research_attempts','task_id=? ORDER BY rowid',(ident,))]
        return t
