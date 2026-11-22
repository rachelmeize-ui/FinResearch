# FinResearch · 公开证据驱动的公司研究

本地单人研究工具。选择研究对象、年度、研究问题及类型，识别主体，实际查找公开资料，进行财务计算或业务证据整理，核验后导出报告。主导航：首页 / 我的研究 / 报告；每份研究共用四个工作区标签。

首页优先展示已保存研究的真实财务看板：财务对照表、彩色年度横条、盈利折线、资产扇形/环形、研究摘录词云和收入/净利润分组柱状图。可切换研究、年度与公司，点击图形或数字核对出处。打开“新建研究”后仍采用问题优先的表单；输入在当前浏览器会话暂存。详见 [看板与十年案例验收](docs/DASHBOARD_DELIVERY.md)，原A版过程保留在 [首页改进说明](docs/HOME_UI_DELIVERY.md)。

## 从 GitHub 安装

需要 Python 3.11 或以上版本。Windows PowerShell 示例：

```powershell
git clone https://github.com/rachelmeize-ui/FinResearch.git
cd FinResearch
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe server.py --port 8530
```

浏览器打开 http://127.0.0.1:8530/ ，创建研究后获取公开资料。新安装使用空白数据库，不附带个人研究或预设成功结果。公开资料检索、财务计算、来源核验和 Markdown 报告导出不需要模型密钥。

Excel 默认使用可移植的 XlsxWriter 导出，不依赖桌面应用。原本机配置存在时仍保留 Node.js 22+ / `@oai/artifact-tool` 导出，可用 `FINRESEARCH_EXCEL_BACKEND=portable` 明确切换。参照 [运行配置示例](runtime.example.json) 配置原桌面路径；示例路径需要替换。浏览器验收脚本依赖本地 Chrome、Playwright 和相应运行配置。Python 单元测试可执行 `python -m unittest discover -s tests -v`；新安装未包含外部资料快照，对应集成检查会明确跳过。

仓库只保存代码、文档及明确标记的测试样例，不上传密钥、运行配置、数据库、下载文件和个人报告。`examples/demo.*` 是测试数据，正式研究界面会拒绝导入模拟数据。AI 调用默认授权额度为零，配置密钥本身不会自动发起研究调用。

这是需要 Python 后端的本地应用，**上传 GitHub 不等于已部署在线服务，GitHub Pages 不能运行其完整功能**。当前仅监听本机地址；如需远程运行，还需部署后端、持久化存储及身份验证。

Docker 服务器配置与访问保护见 [部署说明](docs/DEPLOYMENT.md)。默认运行方式仍只接受本机访问；远程绑定没有 HTTPS 网站地址及独立访问密码时会拒绝启动。

## 运行与使用

运行 `run.ps1` 或双击“打开工作台.cmd”，访问 http://127.0.0.1:8530/ 。保留Python HTTP/SQLite和原生JS/CSS，依赖见requirements.txt及本机runtime.local.json。

- 财务研究：按公司代码和所选年度查询巨潮完整年报，下载PDF后通用解析合并财务表。网易使用SEC申报目录、实际20-F与XBRL，严格核对CNY及年度口径。
- 业务竞品：包括非上市企业时按公开业务资料研究，保存原文、来源类型与缺口，不为未公开财报编造数字。
- 行业研究：按主题和问题查找权威公开资料；缺少资料时如实输出不足，本轮不宣称完整行业分析已通过。
- 主体歧义必须选择；失败会保留逐年记录，可重试、补充公开网页、上传PDF或导入真实CSV/XLSX。

已实测：茅台/五粮液2023—2025六份年报；美的集团2024—2025两份年报；网易2023—2025三个20-F及XBRL；米哈游/网易业务资料比较。更多A股走相同检索/解析代码，格式及访问情况不保证全部成功。港股其他企业、美股通用ticker入口、OCR、多币种跨准则比较尚未完成。

## 真实边界

财务值来自公开文件，比例由finance.py确定性计算。研究问题驱动研究类型、年度检索与业务查询；未用大模型创造财务数值。新引擎为entities、annual_reports、sec_reports、source_io、business_research与research_pipeline，**未加载GPT Researcher**。旧固定案例读取器仅保留兼容和回归。

本轮新增付费模型调用0次。原先一次授权已用完，余额仍为0；已有AI初稿可以查看、人工核验。不要运行授权脚本补额度，不把来源摘录称为AI实时生成。密钥仅保留原本地配置，未写入前端或资料输出。

## 验证与资料

`run.ps1 -Mode Test`执行全部本地回归；`-Mode Browser`运行新引擎浏览器验收（独立数据库副本、真实缓存、无模型调用）。原检查脚本、数据库和历史截图保留。

最终结果：77项后端检查、9组浏览器场景、18项Excel内容检查通过。分别区分真实外部获取、真实缓存回归和模拟单元测试，详见 [引擎交付说明](docs/ENGINE_V3_DELIVERY.md)。正式站点新研究及下载验证见test-results/engine-v3/production-check.json。

数据存data/workspace.sqlite3，升级前已备份，新增来源与检索记录表不重置原表。同URL资料更新按SHA-256保留不可变内容版本。单元测试与浏览器测试不修改你的既有研究。

本机Node/artifact-tool负责Excel写入，openpyxl仅用于读取检查。换机需配置相应运行环境；尚未执行原生Excel重算。服务只监听127.0.0.1，未执行GitHub或公网部署，尚无多用户权限。

视觉规范见DESIGN.md；原UI改版的历史证据保留在docs/UI_REDESIGN_DELIVERY.md，新研究流程以ENGINE_V3_DELIVERY.md为准。项目表达需区分本人决策、AI辅助实现与真实用户访谈，不能把模拟评审写成真人研究。
