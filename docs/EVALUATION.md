# 分层验证结果 · 2026-11-21

## 真实外部数据
public_data.collect(refresh=True)实际从巨潮和深交所披露下载两份2024年报，保存PDF、SHA-256、获取时间；两公司2023/2024各5个金额共20项，与固定参考值核对。页面使用校验过的真实快照会明确显示缓存；不会把缓存说成刚联网抓取。首个完整浏览器任务读取这些真实快照，并从页面打开对应原披露PDF。

贵州茅台：2024收入170899152276.34元、合并净利润89334728025.90元，源PDF63/64页；五粮液：2024收入89175178322.70元、合并净利润33193460484.32元，PDF60/61页。已渲染检查关键合并利润表原页，合并净利润未用摘要归母净利润替代。两年资产/负债页码均保留。

## 本地与模拟输入检查
最终57/57通过，0跳过。其中40项为保留的原本地/合成输入测试；新增边界和状态验证另计，两个测试方法使用实际下载快照核对字段及集成流程。真实下载成功不由合成测试代证。

## 浏览器
真实资料+一次真实模型流程5/5通过（live-flow.json）。独立SQLite副本的模拟角色回归7/7通过（browser-regression.json），无新付费调用。包括上下文共享、20个字段链接、实际下载、拒绝模拟导入、资料变化后旧AI排除、手机390px与刷新恢复、授权与异源边界。没有真实用户访谈或满意度数据。

## 大模型
实际调用deepseek-flash一次：3355输入、783输出、总4138tokens；成功保存6项初稿，6项连续引文匹配；待人工核对。调用预算从1减到0，失败不会自动重试，重跑普通Browser不调用模型。配置状态、授权、执行记录与生成结果可分辨。GPT Researcher没有加载，全网搜索API未接入。

## 文件交付
实际Excel下载后以openpyxl只读检查：6张表、4行真实数据、20条字段出处、数值/公式/模型署名、无错误单元格，16项检查通过。原生Excel重新计算尚未验证；不把工具重算当作原生应用验证。Markdown保留两份来源、报告期、口径、AI模式和限制。

## 复跑
run.ps1 -Mode Test；run.ps1 -Mode Browser；run.ps1 -Mode CheckExport。运行环境：Windows、bundled Python3.12与Node24、本机Chrome、SQLite、pypdf、openpyxl（只读）及artifact-tool（写Excel）。浏览器回归使用8532端口和test-results下的数据库副本，默认不使用模型额度。

证据：test-results/final.json；refocus/live-flow.json、real-model-result.json、browser-regression.json、export-verification.json；refocus-before.json、before-status-fix.json与browser-before-ux-fix.json保存失败前证据。没有性能SLA、100%覆盖率、真实投资效果或效率提升百分比。

## 未完成
更多年份/公司、行情接口、全网搜索、生产权限/远程部署、真实外部用户测试、原生Excel重算和财务规则完备性。当前历史财务研究可以完成；上述能力不会用预设内容伪装成功。
