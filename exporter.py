"""Excel authoring delegates to bundled @oai/artifact-tool. No shell interpolation."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parent
def runtime():
    cfg=ROOT/'runtime.local.json'
    if cfg.exists():return json.loads(cfg.read_text(encoding='utf-8'))
    node=os.environ.get('FINRESEARCH_NODE','node')
    return {'node':node}

def excel(task):
    import reporting
    task={**task,'report':reporting.state(task)}
    if os.environ.get('FINRESEARCH_EXCEL_BACKEND')=='portable' or not (ROOT/'runtime.local.json').exists():
        from portable_excel import excel as portable
        return portable(task)
    cfg=runtime()
    with tempfile.TemporaryDirectory(prefix='finresearch-') as td:
        payload=Path(td)/'input.json';out=Path(td)/'report.xlsx'
        payload.write_text(json.dumps(task,ensure_ascii=False,allow_nan=False),encoding='utf-8')
        result=subprocess.run([cfg['node'],str(ROOT/'scripts'/'export.mjs'),str(payload),str(out)],capture_output=True,timeout=90,cwd=ROOT)
        if result.returncode or not out.exists():raise ValueError('Excel 生成失败，请检查 Node 与 @oai/artifact-tool 环境；Markdown 报告仍可导出。')
        return out.read_bytes()
