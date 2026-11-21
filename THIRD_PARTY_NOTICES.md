# 来源与第三方依赖

本目录是独立新建的金融工作台，没有复制 GPT Researcher 源码，也未将其作为运行依赖。资料核对采用旧研序本地应用 `competitor_lab/domain.py` 的 NFKC 归一化、连续引文匹配和人工核对状态思路；财务规则、SQLite、HTTP API、前端、测试均为此次 AI 辅助新增实现。

旧项目上游 GPT Researcher：https://github.com/assafelovic/gpt-researcher 。本机原型固定提交 `3582a6841fe7dc801e2a34e34ee408641aea9bce`，实际 LICENSE 为 Apache-2.0。原目录及其 LICENSE、THIRD_PARTY_NOTICES 均未修改。新项目不应把上游研究能力称为本次新增工程成果。

- Python 标准库：PSF 许可证；HTTP、sqlite3、Decimal、CSV、unittest。
- openpyxl：MIT，仅读取 Excel 和独立验证导出文件；https://openpyxl.readthedocs.io/ 。
- pypdf：BSD-3-Clause，用于提取官方披露PDF合并财务报表；https://pypdf.readthedocs.io/ 。原公开年报版权与披露主体署名保留，来源链接、获取时间和校验值随研究记录保存。
- Node.js：MIT 及其第三方通知。
- @oai/artifact-tool：桌面环境提供，按其分发条款使用；不复制包源码，不宣称该包为个人作品或开源组件。移机使用须有可用的合法运行环境。
- Playwright：Apache-2.0；只用于开发测试，浏览器为本机 Chrome（其许可由安装方管理）。

财务计算解释参考美国 SEC 财务报表入门材料：https://www.sec.gov/about/reports-publications/beginners-guide-financial-statements 。本项目采用年度、合并、人民币的有限口径，不构成会计准则适用性或投资建议。该参考没有作为茅台、五粮液数值来源；示例数值均人为构造。
