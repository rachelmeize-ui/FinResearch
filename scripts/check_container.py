"""Disposable container smoke test; no real user data or external model calls."""
import base64
import json
import os
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

image = sys.argv[1] if len(sys.argv)>1 else 'finresearch:hosting-check'
name = 'finresearch-check-'+uuid.uuid4().hex[:12]
volume = name+'-data'
env = dict(os.environ, FINRESEARCH_ACCESS_PASSWORD=secrets.token_urlsafe(32))
auth = 'Basic '+base64.b64encode(('owner:'+env['FINRESEARCH_ACCESS_PASSWORD']).encode()).decode()


def docker(*args):
    return subprocess.check_output(['docker',*args],env=env,text=True,stderr=subprocess.PIPE).strip()


def request(path, data=None, authenticated=True):
    headers={'Host':'research.example.com'}
    if authenticated: headers['Authorization']=auth
    raw=json.dumps(data).encode() if data is not None else None
    if raw is not None: headers['Content-Type']='application/json';headers['Origin']='https://research.example.com'
    req=urllib.request.Request(base+path,raw,headers)
    with urllib.request.urlopen(req,timeout=5) as response: return json.load(response)


def ready():
    for _ in range(80):
        try: request('/healthz',authenticated=False);return
        except Exception: time.sleep(.25)
    raise RuntimeError('Container did not become healthy')


try:
    docker('volume','create',volume)
    docker('run','-d','--name',name,'-p','127.0.0.1::10000','-e','FINRESEARCH_ACCESS_PASSWORD','-e','FINRESEARCH_PUBLIC_ORIGIN=https://research.example.com','-v',volume+':/var/lib/finresearch',image)
    port=docker('port',name,'10000/tcp').rsplit(':',1)[-1]
    base='http://127.0.0.1:'+port;ready()
    try: request('/api/state',authenticated=False)
    except urllib.error.HTTPError as e: assert e.code==401
    else: raise AssertionError('Private API was exposed')
    assert not request('/api/state')['tasks']
    created=request('/api/tasks',dict(title='Container persistence check',company_a='网易',company_b='',question='检查研究记录保存',dimensions=['业务'],research_type='business',start_year=2023,end_year=2025))
    docker('restart',name)
    port=docker('port',name,'10000/tcp').rsplit(':',1)[-1]
    base='http://127.0.0.1:'+port;ready()
    saved=request('/api/tasks/'+created['id'])
    assert saved['meta']['requested_years']==[2023,2024,2025]
    assert request('/api/engine')['authorized_calls_remaining']==0
    print(json.dumps({'container_start':True,'private_access':True,'restart_keeps_research':True,'paid_calls':0}))
except Exception:
    subprocess.run(['docker','logs',name],check=False)
    raise
finally:
    subprocess.run(['docker','rm','-f',name],capture_output=True)
    subprocess.run(['docker','volume','rm',volume],capture_output=True)
