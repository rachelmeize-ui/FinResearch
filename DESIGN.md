---
name: FinResearch
description: 白灰与深蓝的本地公司研究工作台，以财务比较和证据核验为中心。
colors:
  ink: "#202936"
  muted: "#5b6575"
  accent: "#234c95"
  accent-hover: "#193b79"
  line: "#e1e5eb"
  canvas: "#f6f7f9"
  white: "#fff"
  soft: "#eef3fb"
  warning: "#855616"
  danger: "#a63030"
  comparison: "#8495b4"
  control-border: "#cdd4de"
  status-neutral-bg: "#edf0f5"
  status-neutral-text: "#536174"
  status-good-bg: "#edf5ef"
  status-good-text: "#366246"
  status-warn-bg: "#fbf2e3"
  status-bad-bg: "#fbecec"
typography:
  headline:
    fontFamily: '"Segoe UI","Microsoft YaHei","PingFang SC",sans-serif'
    fontSize: "26px"
    fontWeight: 650
    lineHeight: 1.4
    letterSpacing: "-0.025em"
  section:
    fontFamily: '"Segoe UI","Microsoft YaHei","PingFang SC",sans-serif'
    fontSize: "17px"
    fontWeight: 650
    lineHeight: 1.5
  title:
    fontFamily: '"Segoe UI","Microsoft YaHei","PingFang SC",sans-serif'
    fontSize: "14px"
    fontWeight: 650
    lineHeight: 1.55
  body:
    fontFamily: '"Segoe UI","Microsoft YaHei","PingFang SC",sans-serif'
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.65
  label:
    fontFamily: '"Segoe UI","Microsoft YaHei","PingFang SC",sans-serif'
    fontSize: "12px"
    fontWeight: 500
    lineHeight: 1.65
  button:
    fontFamily: '"Segoe UI","Microsoft YaHei","PingFang SC",sans-serif'
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  inset: "3px"
  status: "4px"
  field: "5px"
  control: "6px"
  panel: "8px"
spacing:
  base: "8px"
  compact: "12px"
  standard: "16px"
  section: "24px"
  wide: "32px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.white}"
    typography: "{typography.button}"
    rounded: "{rounded.control}"
    padding: "7px 13px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
    textColor: "{colors.white}"
  button-secondary:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    typography: "{typography.button}"
    rounded: "{rounded.control}"
    padding: "7px 13px"
  input:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "8px 10px"
  status:
    backgroundColor: "{colors.status-neutral-bg}"
    textColor: "{colors.status-neutral-text}"
    rounded: "{rounded.status}"
    padding: "2px 7px"
  analysis-panel:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "20px 24px"
---

# Design System: FinResearch

## Overview

**Creative North Star: "可追溯的金融研究工作台"**

Operate 模式：供金融专业学生、研究实习生和初级分析人员连续阅读、比较财务表格并核对来源。采用用户确定的白、灰、深蓝专业金融 SaaS 方向，以名称、文本和数据组织界面；不依赖装饰图片或复制参考产品的品牌资产。

白色工作面置于浅灰画布，深蓝标记主操作、当前位置和证据入口。细线分隔与紧凑排版保持数据密度；首页、列表、研究工作区与报告预览属于同一视觉系统。本文为实现扫描结果，来源为 `static/index.html`、`static/style.css`、`static/app.js`；旧版绿色侧栏规范保存在 `archive/ui-before-20261121-DESIGN.md`。

**Key Characteristics:**

- 白灰工作面、克制深蓝与清晰边界。
- 紧凑表格、右对齐金额和等宽数字。
- 状态使用文字，来源入口就近可见。
- 系统中文字体、键盘焦点与窄屏重排。

## Colors

颜色值以顶部 frontmatter 为准；下列名称说明其用途，不建立第二套色值。

### Primary

- **研究深蓝（accent）**：主按钮、链接、选中导航、标签页下划线、第一家公司柱形和键盘焦点。
- **交互深蓝（accent-hover）**：主按钮和文字链接的悬停状态。
- **浅蓝选区（soft）**：桌面当前导航、选中分段控件与数字来源按钮悬停。

### Secondary

- **比较灰蓝（comparison）**：第二家公司柱形和图例；表示公司身份，不表示优劣。
- **核验琥珀（warning / status-warn-bg）**：待核验、进行中或未处理状态。
- **错误红（danger / status-bad-bg）**：受阻、错误和证据冲突状态。
- **完成绿（status-good-text / status-good-bg）**：就绪、成功和已确认状态。

### Neutral

- **正文墨色（ink）**与**说明灰（muted）**区分内容层级。
- **画布灰（canvas）**承载页面，**工作白（white）**承载表单、表格与报告。
- **分隔灰（line）**用于容器和分隔线；**控件边界（control-border）**用于输入和次按钮。
- **中性状态（status-neutral-bg / status-neutral-text）**用于无需警示的状态说明。

**The Meaning Before Color Rule.** 状态必须保留明确文字；公司对比色不得解释为涨跌、投资评级或收益预测。

## Typography

正文与标题共用 frontmatter 中的系统字体栈，无远程字体依赖。标题使用中等偏重字重，不使用超大展示字体；正文段落通常限制在（75ch）以内。财务金额和百分比使用 `tabular-nums`，数值列右对齐。

### Hierarchy

- **Headline**：页面和研究公司标题；手机尺寸降为（23px）。
- **Section**：页面内章节标题；更窄屏的部分章节使用（16px）。
- **Title**：研究发现、文件条目与次级标题。
- **Body**：基础正文；具体研究发现和报告正文使用（13px）。
- **Label**：表单标签、来源说明和次级操作；微型状态标签使用（11px）。
- **Button**：普通按钮与操作链接；报表值按钮保持表格的数字秩序。

报告正文行高为（1.85），研究发现段落行高为（1.8）。手机图表金额取整、百分比保留一位小数；精确值仍由数据表提供。

**The Exact Value Rule.** 不为视觉整齐改写财务值；缺失值显示破折号，原始金额、页面亿元和比例单位必须可辨认。

## Layout

桌面采用固定白色侧栏（208px）、顶栏（62px）和居中工作区。主内容最大宽度（1440px），常规内边距（30px 36px 54px）；超宽屏从（1600px）起水平内边距增至（48px）。首页开始研究区域为双列，概览采用主内容加核验指引栏。常用间距以（8px）为基准，另有实际内容需要的局部间距，不强制所有尺寸为其倍数。

在（1100px）及以下缩小侧栏和列间距；（800px）及以下侧栏转顶部三项导航，概览、首页表单与研究标题转单列，任务切换器移到标题下方；（480px）及以下表单、后续步骤与操作区继续纵向重排，来源抽屉占满宽度。研究的四个标签页保持横向、允许局部滚动。

表格区域可聚焦、独立双向滚动，最大高度（560px），表头及首列固定。来源明细表最小宽度（720px），末列最小宽度（156px），来源按钮不折行；窄屏显示向右滑动提示。页面正文不承担表格的横向溢出。报告纸张最大宽度（920px），桌面内边距（42px 54px），随窄屏缩小。

## Elevation & Depth

常规工作面靠底色、细边框和空隙分层，无卡片浮起阴影。唯一结构性阴影用于模态来源抽屉（`-12px 0 40px #172b4d1f`），背幕使用（`#18253638`），明确证据面板覆盖当前研究上下文。表格固定表头、抽屉固定标题栏依靠背景和层级保持可读。

**The Flat Work Surface Rule.** 普通内容不增加浮动投影；深度用于正在核验的覆盖面板。

## Shapes

形状以小圆角矩形为主：输入框、导航和说明区使用 field 级圆角，按钮与滚动表使用 control 级，分析面板与研究列表使用 panel 级，状态标签使用 status 级；精确值见 frontmatter。边框常规为（1px）。报告纸张保持直角文档轮廓；移动导航改为底线选中。避免大圆角胶囊、装饰图标卡片和渐变。

## Components

### Buttons

主按钮深蓝底白字，次按钮白底墨字与细边框，文字按钮用于查看依据等局部操作。普通按钮最小高度（36px）；首页开始研究按钮额外使用（10px 20px）内边距。悬停改变底色和边界，按下使用更深的中性底色；禁用状态为灰底灰字并禁用指针。背景、边框过渡为（0.15s）；减少动态效果偏好下取消过渡。

焦点采用深蓝实线（2px），外偏移（3px）；包含链接、表单控件、表格滚动区和可聚焦图表柱形。柱形焦点偏移为（6px）。

### Chips

状态标签紧凑、不可操作；背景和文字配对表示中性、完成、待核验和错误。其含义始终由文字给出。图表/数据表切换是按钮组，使用 `aria-pressed` 和浅蓝选中底色，不与状态标签混用。

### Cards / Containers

分析面板使用白底、细线和小圆角，桌面内边距见 frontmatter；移动端分别收紧为（18px）和（15px）。列表按行分隔，研究发现以横线组织；不把每个数值独立放入高大的指标卡片。空状态保留标题、解释和下一步入口。

### Inputs / Fields

白底细边框、全宽输入，普通控件最小高度（38px）。标签在控件上方；多行内容允许垂直调整。必填、网址格式和长度约束使用原生校验，保存失败显示可见文字反馈。错误不会被包装成成功通知。

### Navigation

主导航固定为首页、我的研究、报告；研究内共用公司、研究问题、报告期、来源和 AI 状态，再展示研究概览、财务对比、来源与核验、研究报告四个链接。当前位置通过文字颜色、背景或下划线与 `aria-current` 共同体现。手机顶部导航保持相同内容，不新增开发管理入口。

### Evidence Drawer

原生模态对话框从右侧展示，桌面宽度（480px）、高度（100dvh），窄屏不超过视口。数字、图表柱形和来源按钮共享字段抽屉，显示原始字段、PDF 实际页码、计算规则和原披露链接；AI 核验抽屉另含引用、编辑与审核表单。支持关闭按钮与原生 Escape，关闭后恢复到仍存在的触发元素。

## Do's and Don'ts

### Do:

- **Do** 使用同一研究上下文串联概览、比较、来源核验和报告。
- **Do** 保留金额单位、报告期、合并口径、来源和 AI 初稿状态。
- **Do** 让表格在自身容器内滚动，并提供可见键盘焦点。
- **Do** 为等待、失败、缺数据和未生成内容提供明确文字与下一步。

### Don't:

- **Don't** 加入渐变、装饰图片、大圆角胶囊或膨胀的指标卡片。
- **Don't** 用红绿替代公司身份、用颜色替代核验文字。
- **Don't** 把历史年报柱形画成连续行情走势，或暗示实时行情已接入。
- **Don't** 将固定公式、既有 AI 初稿和人工已确认结论混为一种可信状态。
