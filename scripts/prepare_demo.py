"""Create one idempotent synthetic showcase; never alters existing user tasks."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import finance
import server
import store
ROOT=server.ROOT
store.init();server.seed()
title='贵州茅台 vs 五粮液｜完整核验演示（模拟数据）'
with store.db() as c:
    found=c.execute('SELECT id FROM tasks WHERE title=?',(title,)).fetchone()
if found:
    t=store.detail(found['id'])
else:
    t=server.api('POST','/api/demo',{})
    with store.db() as c:
        c.execute('UPDATE tasks SET title=? WHERE id=?',(title,t['id']))
    dirty=finance.parse_file('dirty.csv',(ROOT/'static/dirty.csv').read_bytes())
    t=server.import_data(t['id'],'异常模拟批次（用于核验练习）',dirty)
    for i in t['issues']:
        server.api('PATCH','/api/issues/'+i['id'],{'status':'已解决','note':'自动演示记录：此项由专用模拟夹具触发；随后已重新导入完整模拟数据，旧批次不改写。不是人工核验真实年报。'})
    good=finance.parse_file('demo.csv',(ROOT/'examples/demo.csv').read_bytes())
    t=server.import_data(t['id'],'修订后模拟批次（6行完整数据）',good)
    t=server.api('POST','/api/tasks/'+t['id']+'/research',{})
    t=server.api('POST','/api/tasks/'+t['id']+'/complete',{})

entries=[
 ('Bug','B01/B02：数据库字段与占位符不一致','P0','server.py operation/import_data','首次初始化和异常导入可提交；bootstrap和异常流程回归通过。',False),
 ('Bug','B03：同秒导入可能恢复错误批次','P0','store.py detail','同秒逆序ID导入后，newer.csv仍为最新。',False),
 ('Bug','B04：重开异常未撤销任务完成状态','P1','server.py PATCH issues','完成任务后重开最新批次问题，任务为待核验。',False),
 ('Bug','B05：部分XLSX缺少尺寸元数据导致异常','P0','finance.py parse_file','合法最小XLSX和真实上传都通过；读取过程中限行列。',False),
 ('Bug','B06/B07：Windows导出路径与时间/说明显示','P0','scripts/export.mjs','实际下载五表；时间保留UTC文本；说明换行可读。',False),
 ('Bug','B08：缺少一家公司的有效数据仍可结束任务','P1','server.py complete','双公司任务需要两家公司各有有效行；先失败再修复，40项回归通过。',False),
 ('反馈','模拟运营反馈：问题重新开启后应回到待核验','P1','issues','对应B04，完成→重开场景自动执行通过。',True),
 ('反馈','模拟研究反馈：交付文件要带公式、出处和处理日志','P1','export','浏览器真实下载，独立读缓存、公式、来源和日志。',True),
 ('反馈','模拟新手反馈：需要示例、计算说明和下一步入口','P1','dashboard','空状态与手机截图启发式评审；不宣称真人满意度。',True),
]
for kind,label,priority,feature,acceptance,synthetic in entries:
    with store.db() as c:
        exists=c.execute('SELECT 1 FROM operations WHERE title=?',(label,)).fetchone()
    if exists:continue
    server.operation(dict(kind=kind,title=label,persona='资管产品运营人员' if '运营' in label else '首次使用者' if '新手' in label else '证券投资部实习生',pain='模拟场景假设' if synthetic else '实际开发运行或回归测试发现；见USER_TESTING与ITERATION_LOG。',story=label,priority=priority,acceptance=acceptance,status='已完成',feature=feature if synthetic else 'analysis' if 'XLSX' in label else 'issues' if '重开' in label else 'planning' if '字段' in label else 'research',synthetic=synthetic))
with store.db() as c:
    c.execute('INSERT INTO releases VALUES(?,?,?,?) ON CONFLICT(version) DO UPDATE SET changes=excluded.changes',('0.1.1','核验、保存与Excel交付修复',store.dumps(['同秒批次顺序','重新开启问题的任务联动','XLSX兼容与真实下载验证','40项后端、11个浏览器场景通过']),store.now()))
out=ROOT/'outputs'/'finresearch-20261121';out.mkdir(parents=True,exist_ok=True)
t=store.detail(t['id'])
(out/'demo-task.json').write_text(store.dumps(t),encoding='utf-8')
(out/'金融研究核验报告_模拟数据.md').write_text(server.markdown(t),encoding='utf-8')
from exporter import excel
(out/'金融研究核验报告_模拟数据.xlsx').write_bytes(excel(t))
(ROOT/'data'/'demo-id.txt').write_text(t['id'],encoding='utf-8')
print(json.dumps({'task_id':t['id'],'url':'http://127.0.0.1:8530/#research/'+t['id'],'datasets':len(t['datasets']),'current_rows':len(t['datasets'][-1]['rows']),'issues':len(t['issues']),'sources':len(t['sources']),'comparison_cells':len(t['research'][-1]['cells'])},ensure_ascii=True))
