# 纠偏迭代记录 · 0.1.1 → 0.2.0

## 产品调整
金融业务移回主线；从导航移出需求池、模拟反馈、Bug、版本和开发说明；异常核验并入财务分析，来源与AI并入研究详情，导出集中报告中心。旧数据库、源码、文档与测试保留，模拟研究归档而非冒充真实案例。

## 真实代码修复与证据
| ID | 修改前 | 修改后 | 代码与验证 |
|---|---|---|---|
| F01 | 来源汇总dict重复url/title参数，真实取数后报错 | 来源元信息显式合并，完整登记6份维度依据 | engine.collect_job；refocus-before错误→final通过；真实流程5/5 |
| F02 | 从1500px处切页面仍停1500px | 同一任务切页定位顶部并清旧通知 | static/app.js route；browser-before-ux-fix失败→browser-regression通过 |
| F03 | 加资料后仍显示AI已完成 | 数据/资料更新→AI待更新；报告排除旧批次结果 | server.import_data/sources、reporting.state、jobPanel；before-status-fix失败→57项通过 |
| F04 | 报告页计算摘要与AI全文重复 | 主区域呈现当前结论，计算摘要按需展开 | static/app.js reportsPage/detailPage；前后截图启发式评审 |

新增真实数据获取、字段出处、模型授权和状态并非上游GPT Researcher新增能力；它未被本版调用。本次实连deepseek-flash一次，未自动重试。4138tokens是一次请求用量，不是费用估计或效果指标。

阶段用例数不同：56项中1错误；57项中1失败；最终57项全部通过。浏览器前置失败阻断了后续测试，不能将前后不同长度集合换算成百分比改善。没有故意制造产品低质量问题，财务单元测试夹具与产品缺陷分开记录。
