# Anti-Patterns 反模式清单

每个反模式都有：问题描述、NO/OK 对照、为什么是问题、以及来源。

## 目录

- [1. Description 包含 Workflow 摘要](#1-description-包含-workflow-摘要)
- [2. SKILL.md 超 500 行](#2-skillmd-超-500-行)
- [3. References 嵌套超过一层](#3-references-嵌套超过一层)
- [4. 用 "Consider" / "Try to" 写约束](#4-用-consider--try-to-写约束)
- [5. 多语言示例](#5-多语言示例)
- [6. 叙事性内容](#6-叙事性内容)
- [7. 通用标签](#7-通用标签)
- [8. 给 AI 太多等价选择](#8-给-ai-太多等价选择)
- [9. @ 强制加载大文件](#9--强制加载大文件)
- [10. CLAUDE.md / AGENTS.md 超 60 行](#10-claudemd--agentsmd-超-60-行)
- [11. 不测试就部署](#11-不测试就部署)
- [12. Description 只有英文（或只有中文）](#12-description-只有英文或只有中文)
- [13. Gotchas 表用假设性案例](#13-gotchas-表用假设性案例)
- [14. Reference 文件互相引用](#14-reference-文件互相引用)
- [15. 缺少领域 Slop Catalog](#15-缺少领域-slop-catalog)
- [16. 无 Direction Lock 直接开工](#16-无-direction-lock-直接开工)
- [17. 忽略平台差异](#17-忽略平台差异)
- [快速自检表](#快速自检表)

---

## 1. Description 包含 Workflow 摘要

```
NO: "Analyzes code structure, identifies anti-patterns, generates
     refactoring plan, applies changes with minimal diff, and validates
     through comprehensive test suite."

OK: "Use when the user wants to refactor code, reduce duplication,
     simplify complex functions, or asks 'this code is messy'."
```

**为什么是问题**：AI 从 description 获得了 workflow 的摘要后，认为自己已经理解了 skill，跳过正文。结果：执行步骤缺失、细节规则被忽略。

**来源**：CSO 规则实测。

---

## 2. SKILL.md 超 500 行

```
NO: 一个 800 行的 SKILL.md，包含所有规则、例子、和参考信息

OK: 一个 400 行的 SKILL.md + 3 个 reference 文件，通过条件引用加载
```

**为什么是问题**：Liu et al.（TACL 2024）的受控实验显示，相关信息位于长上下文中部时，部分模型和任务的表现会明显下降；幅度随模型、任务和输入长度变化。这不等于“中间规则必然失效”，但足以要求把关键规则前置、压缩并通过压力测试验证。

**来源**：Agent Skills 规范的渐进披露设计，以及 Liu et al. 的长上下文位置实验；公开链接见仓库 README。

---

## 3. References 嵌套超过一层

```
NO: SKILL.md → references/style.md → references/color-details.md

OK: SKILL.md → references/style.md（包含颜色详情）
OK: SKILL.md → references/style.md + SKILL.md → references/colors.md
```

**为什么是问题**：AI 对嵌套引用做 `head -100` 而非完整阅读。两层以上的引用实际上等于内容丢失。

**来源**：多项目实测观察。

---

## 4. 用 "Consider" / "Try to" 写约束

```
NO: "Consider keeping your description concise."
NO: "Try to limit the file to 500 lines."
NO: "You might want to add tests."

OK: "Description 必须 ≤1024 字符。"
OK: "SKILL.md ≤ 500 行；超出必须论证或拆进 references。"
OK: "部署前必须通过触发测试（3 命中 + 3 未命中）。"
```

**为什么是问题**：`Consider` / `Try to` 在语义上允许跳过，因此不能承载真实要求。普通规则用祈使句并说明原因；只有安全、不可逆或真非协商项使用 MUST / NEVER。Meincke et al.（PNAS 2026）的说服实验只能作为“模型对权威框架敏感”的间接证据，不能外推成 Skill 指令合规率提升；直接证据必须来自该 Skill 自己的 run-compare。

---

## 5. 多语言示例

```
NO:
  JavaScript 版本: [20 行代码]
  Python 版本: [20 行代码]
  Go 版本: [20 行代码]

OK:
  [一个覆盖核心模式的 20 行代码例子]
```

**为什么是问题**：如果多个例子只重复同一模式，它们会增加上下文成本而不增加新的决策信息。保留一个能覆盖核心模式的例子；只有语言差异会改变行为时才增加对应版本。

**来源**：上下文预算原则；实际取舍用目标技能的任务评测验证。

---

## 6. 叙事性内容

```
NO: "In session 2025-10-03, we discovered an interesting pattern
     where the AI would occasionally skip the validation step,
     especially when the user seemed to be in a hurry. After much
     deliberation, we decided to..."

OK:
  | What happened | Rule |
  |---|---|
  | AI 在用户催促时跳过验证 | 验证步骤不可跳过。加 Iron Law。 |
```

**为什么是问题**：叙事消耗大量 token 但信息密度低。AI 需要从叙事中自行提取规则——增加了一次"理解"的不确定性。表格直接给出场景和规则的映射，AI 可以精确匹配。

**来源**：信息密度原则。

---

## 7. 通用标签

```
NO: helper1.md, step3.md, pattern4.md, doc2.md, utils.md

OK: screenshot-analysis.md, api-patterns.md, qa-checklist.md
```

**为什么是问题**：AI 用文件名推断文件内容——通用标签不提供语义信息，增加了 AI 判断"是否需要读这个文件"的不确定性。

**来源**：架构原则。

---

## 8. 给 AI 太多等价选择

```
NO: "你可以用方案 A（简单）、方案 B（中等）、方案 C（复杂）、
     方案 D（创新）或方案 E（传统）来组织 skill。"

OK: "默认使用 三层 progressive disclosure（SKILL.md + references/ + scripts/）。
     当 skill 内容 < 200 行且无外部验证需求时，可以用单文件结构。"
```

**为什么是问题**：AI 面对多个等价选择时，倾向于做"折中"选择（选中间的或混合多个）。这通常不是任何一个方案的最佳执行，而是所有方案的低质量平均。给一个默认方案 + 一个明确的 escape hatch 条件，比 5 个等价选择可靠。

**来源**：自由度控制原则。

---

## 9. @ 强制加载大文件

```
NO: @references/complete-design-system.md（600 行）

OK: 当需要设计系统信息时，读 `references/design-system.md`
```

**为什么是问题**：显式附加大文件会占用当前会话的上下文，即使任务只需要其中一小部分。条件引用减少不相关内容，但不保证模型一定关注正确位置；仍需在目标宿主中验证加载与使用行为。

**来源**：上下文预算原则；具体注入方式以目标宿主文档和实测为准。

---

## 10. CLAUDE.md / AGENTS.md 过度膨胀

```
NO: 一个 200 行的 AGENTS.md，包含编码规范、提交规范、
     测试规范、文档规范、部署规范...

OK: 一个 50 行的 AGENTS.md，只包含跨 skill 共享的纪律，
     领域规范分别放在各自的 skill 里。
```

**为什么是问题**：AGENTS.md 会在每个相关会话中占用上下文。把低频领域规则常驻其中，会持续挤压任务上下文；应根据宿主的实际加载方式和使用频率决定保留范围。

**来源**：Context 预算原则。

---

## 11. 不测试就部署

```
NO: 写完 SKILL.md → 直接放到 skills/ 目录 → 期望它工作

OK: 写完 → 新 session 触发测试 → 新 session 功能测试 → 修复 → 部署
```

**为什么是问题**：skill 作者"知道"skill 的意图，会无意识地补偿 skill 的缺陷。只有在新 session 中（无历史 context）测试，才能暴露 skill 作为独立文档的真实效果。

**来源**：TDD for Skills 方法论。

---

## 12. Description 漏掉真实用户语言

```
NO: "Use when writing skills or optimizing prompts."

OK: "Use when writing new skills, optimizing existing skills,
     reviewing skill quality, or designing agent instructions.
     Triggers on 写 skill / 改 skill / skill 质量 / 提示词工程 /
     指令设计 / create skill / optimize skill / prompt engineering."
```

**为什么是问题**：路由依赖 description 中可匹配的意图与词汇。如果真实用户会用多种语言，而 description 只覆盖其中一种，就会漏掉另一种；如果受众始终单语，则无需为了形式强行双语。

**来源**：真实用户语料与分语言 routing fixture。

---

## 13. Gotchas 表用假设性案例

```
NO:
  | What happened | Rule |
  |---|---|
  | 如果 AI 可能跳过测试 | 不要跳过测试 |

OK:
  | What happened | Rule |
  |---|---|
  | AI 在用户说"赶时间"后跳过了 Step 6 校验 | 校验步骤不可跳过。Iron Law: No step is optional under time pressure. |
```

**为什么是问题**："如果 AI 可能..."是猜测，不是模式匹配的有效输入。"AI 在 X 场景下做了 Y" 是具体场景——AI 的注意力机制可以直接在类似场景中匹配并激活对应规则。

**来源**：Gotchas 模式 + LLM 模式匹配特性。

---

## 14. Reference 文件互相引用

```
NO:
  style.md: "关于颜色细节，参见 colors.md"
  colors.md: "关于样式整合，参见 style.md"

OK:
  style.md: 包含颜色相关内容（内联或从 SKILL.md 同级引用 colors.md）
  colors.md: 独立完整，不引用其他 reference
```

**为什么是问题**：AI 在两个文件间反复跳转，浪费 token 且增加"中途遗忘"风险。每个 reference 必须独立可读。

**来源**：一层引用规则。

---

## 15. 缺少领域 Slop Catalog

```
NO:
  在 SKILL.md 中只写 "避免 AI 味"

OK:
  为特定领域建立具体的 slop catalog：
  | AI 默认输出 | 改为 |
  | 段末 "这说明..." | 删除，或用具体数据替代 |
  | "随着...的发展" 开头 | 用具体事件开头 |
  | 三张相同卡片布局 | 错落网格或非对称布局 |
```

**为什么是问题**：每个领域有不同的 AI 默认模式。通用的“避免 AI 味”没有可检查对象；先从该领域 baseline 样本提取重复模式，再写领域专属 NO/OK。

**示例**：一份 50+ 条的中文 AI 味模式清单。

---

## 16. 无 Direction Lock 直接开工

```
NO:
  用户说 "做一个页面" → 直接写代码

OK:
  用户说 "做一个页面" → 先问 3-5 个约束性问题（谁用？方向？约束？）→ 确认后再动手
```

**为什么是问题**：方向错误的产出，无论质量多高都是浪费。对于确实存在重大方向分叉的 skill，先锁定少量关键约束通常能减少返工；是否有效仍应从真实迭代记录中验证。

**示例**："先锁定方向"（Lock the Direction First）模式。

---

## 17. 忽略平台差异

```
NO:
  在 skill 中写 "始终使用 <某宿主专用工具>"
  （没有声明只支持该宿主，也没有能力检测）

OK:
  ## 文件读取
  - 先使用当前宿主提供的专用读取工具
  - 只有宿主明确缺少该能力时，才使用兼容的只读替代
  - 如果该 skill 只支持一个宿主，在 compatibility 中声明
```

**为什么是问题**：同一个 skill 在不同平台可能需要不同行为——可用工具、路径格式、模型能力都不同。不处理平台差异 = skill 只在一个平台工作。

**来源**：agentskills.io compatibility 字段。

---

## 快速自检表

写完 skill 后过一遍：

- [ ] Description 没有 workflow 步骤
- [ ] SKILL.md 默认 ≤500 行；501–700 有保留理由或拆分计划
- [ ] References 一层深度，无必需的 peer-load 链
- [ ] 非协商约束用 MUST / NEVER；普通规则用祈使句 + 理由
- [ ] 一个好例子（不是多语言多版本）
- [ ] 没有叙事性内容
- [ ] 文件名有语义
- [ ] 给了默认方案（不是等价选择）
- [ ] 没有 @ 强制加载大文件
- [ ] AGENTS.md 只保留每个 session 都需要的共享纪律
- [ ] 在新 session 中测试过（4 层 Eval：Routing / Contract / Content / Regression）
- [ ] Description 覆盖真实用户会使用的语言
- [ ] Gotchas 是真实案例
- [ ] 有领域 Slop Catalog（不是通用"避免 AI 味"）
- [ ] 涉及大方向选择的 skill 有 Direction Lock
- [ ] 多工具/多策略选择用 Decision Tree
- [ ] 跨平台使用时有平台适配说明
