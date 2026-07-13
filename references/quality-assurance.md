# 质量保证

## 目录

- [Quality Gate 层级](#quality-gate-层级)
- [验证预算按风险投放](#验证预算按风险投放)
- [Anti-Slop 检查](#anti-slop-检查)
- [脚本验证设计](#脚本验证设计)
- [密度检查](#密度检查)
- [Pre-Ship Checklist](#pre-ship-checklist)
- [Review 评分框架](#review-评分框架)
- [Run-Compare: 用实跑评估 skill 是否有用](#run-compare-用实跑评估-skill-是否有用)
- [Citation Discipline: 正文不出现读者打不开的名字](#citation-discipline-正文不出现读者打不开的名字)
- [规则单一真源](#规则单一真源)

---

## Quality Gate 层级

从最可靠到最不可靠：

```
Tier 1: 确定性脚本 — HTML 语法、文件大小、格式规范、链接有效性
Tier 2: 渲染检查 — Playwright 截图、浏览器验证、视觉回归
Tier 3: AI 结构检查 — 检查产出是否包含所有必需部分
Tier 4: AI 质量判断 — 主观评估"好不好"
```

规则：**能用 Tier 1 检查的不用 Tier 4。** 按层级分配检查任务，不要全靠 AI 判断。

### 每层适用的检查

**Tier 1 — 确定性脚本**：
- HTML/JSON/YAML 语法验证
- 文件大小在范围内（如图片 < 500KB）
- 必需字段存在（frontmatter 有 name 和 description）
- Token 数量在预算内
- 行数在限制内
- 链接指向存在的文件

**Tier 2 — 渲染检查**：
- 页面在目标尺寸下无溢出（Playwright）
- 文字不被截断
- 图片正确加载
- 交互功能正常工作

**Tier 3 — AI 结构检查**：
- 生产型产出包含已声明的 Outcome Contract 字段
- Workflow 步骤连续编号
- Reference Map 中的文件都存在
- Hard Rules 使用 Authority 用词
- Gotchas 表有真实案例（不是假设）

**Tier 4 — AI 质量判断**：
- Opening Statement 是否设定了正确的 mental model
- NO/OK 例子是否真实代表 AI 的默认行为
- 自由度设置是否合理
- 整体是否连贯

## 验证预算按风险投放

Quality Gate 层级回答"用哪种检查"；这一节回答"**贵的检查砸在哪**"。对抗式复核（起 reviewer 反向挑错）、盲评、多轮重跑都很贵——铺满全部产出等于没有策略。

例如，AI 生成一批“建议删除”的候选片段时，可以先按错删代价决定哪些候选值得派对抗 reviewer 复核：

| 风险层 | 判据 | 处理 |
|---|---|---|
| 低风险 | 已由前后文证明是语义重复，且末端人工可完整恢复 | 免昂贵复核，交末端人工兜底 |
| 高风险 | 整句删除、"开头撞结尾岔"、长片段——**可能藏着别处没有的内容** | 必须复核 |

三条可泛化的规则：

1. **按"错的代价"分层，不按"错的概率"**。它的判据是"删字安全、删意思危险"——错删（丢内容）代价远高于漏删（啰嗦），所以复核投放在错删侧。先问你的 skill 里哪一侧的错误更贵。
2. **末端有便宜兜底的，前端不重复投放**。低风险项交给最后一道人工/确定性检查即可；在它前面再铺 AI 复核是重叠支出。
3. **有真实数据才带数字**。量化 Gotcha 必须附可复算样本；没有原始记录时只陈述风险逻辑，不补一个看起来精确的比例。

何时使用：skill 产出**一批候选判断**（删除建议、修复建议、审查发现）且逐项复核成本显著时。单一产出的 skill 直接走 Run-Compare。

## Anti-Slop 检查

"Slop" 是 AI 的默认高频模式——看起来合理但实际上是低质量的模板化输出。

### Skill 文件中的 AI Slop 信号

| 信号 | 问题 | 修复 |
|---|---|---|
| "Consider doing X" / "You might want to" | 不是约束，AI 可以忽略 | 普通规则改成祈使句 + 原因；只有安全/不可逆/真非协商项用 MUST |
| 三段式重复（概述-详述-总结） | 三次说同一件事，浪费 token | 只保留一次 |
| 多语言示例（JS + Python + Go） | 注意力稀释 | 一个最佳例子 |
| 叙事性描述（"In our experience..."） | 不是指令，浪费 token | 改为直接规则或删除 |
| 通用标签（helper1, step3） | 不传达语义 | 用描述性名称 |
| 过度结构化（每个点都有子点的子点） | 层级太深失去重点 | 拍平到 2 级 |
| "确保" / "请注意" / "需要注意的是" | 语气软弱 + 信息冗余 | 直接写规则或删除前缀 |

### 内容产出中的 AI Slop 信号（skill 用于生成内容时）

一份视觉类 skill 的反模式清单示例：
- 过度使用渐变和投影
- 三段式结构（开场-要点-收束 永远是 3 个）
- 通用配色（蓝+白 或 深色+金色）
- 过长的标题（中文超过 15 字）
- 内容重复但换了表达方式

对于每个 skill 的领域，识别该领域中 AI 的 slop 模式，写进 Gotchas 或 reference 里。

## 脚本验证设计

### 何时写脚本

当一条规则满足以下条件时写脚本：
1. 可以表达为布尔判断（通过/不通过）或数值范围
2. 会被反复执行（不是一次性检查）
3. 错误时的代价高于写脚本的成本

### 脚本结构

```
scripts/
├── validate.py    # 验证产出是否符合规范
├── build.py       # 构建/编译流程
└── stabilize.py   # 自动修复常见问题（可选）
```

### Validate 脚本的标准输出

```json
{
  "pass": false,
  "errors": [
    {"rule": "SKILL.md ≤500 lines by default", "actual": 623, "fix": "Justify resident content or move low-frequency sections to references/"}
  ],
  "warnings": [
    {"rule": "Description ≤1024 chars", "actual": 980, "note": "Close to limit"}
  ]
}
```

关键：**输出修复建议，不只是报错**。AI 收到错误报告后可以直接按建议修复，不需要重新分析问题。

### Stabilize 脚本

一种进阶模式：当验证发现特定类型的问题（如文字溢出容器）时，stabilize 脚本自动尝试修复（调整字号、截断文本），然后重新验证。

这是 Tier 1.5 级别的 QA——脚本不只检查，还自动修复可确定性修复的问题。

## 密度检查

一种 4 波段密度检查：

### 概念

内容密度直接决定用户体验。过疏 → 感觉空洞。过密 → 无法阅读。对于不同类型的 skill 产出，需要校准不同的密度标准。

### 4 波段模型

```
封面: 标题 + 副标题 + 1 张图 → 信息密度 Low
正文: 段落 + 配图 + 标注 → 信息密度 Medium-High
数据页: 数字 + 标签 + 对比 → 信息密度 High
结尾: CTA + 联系方式 → 信息密度 Low
```

每种内容类型都有最优的信息密度范围。超出范围 → 要么拆分，要么压缩。

### 在 Skill 文件中的应用

SKILL.md 的密度目标：

```
Opening Statement: 1-2 句 → High density（每句都有信息量）
Outcome Contract: 4 行 → Medium-High（格式化但紧凑）
Workflow Steps: 每步 5-15 行 → Medium（步骤+说明+引用指令）
Hard Rules: 每条 1 行 → High（零废话）
Gotchas Table: 每行 2 列 → High（场景+规则）
```

## 4 层 Eval 框架

一套比单纯 "3+3 + 功能测试" 更完整的 eval policy：

| 层 | 检查什么 | 方法 | 通过标准 |
|---|---|---|---|
| **Routing** | Skill 是否在正确场景触发？ | 3 命中 + 3 未命中 prompt | 全部正确 |
| **Contract** | 产出是否符合 Output Format 契约？ | `contract_eval.py` 跑确定性检查；主观项提交逐项 evidence | 确定性全过，manual 无 pending |
| **Content** | 内容质量是否比基线更好？ | 优先受控业务指标；否则 persisted run-compare | 效果方向稳定，边界明确 |
| **Regression** | 修改后是否破坏了之前正常的功能？ | 重跑所有受影响的已通过 gate | 受影响 gate 全部仍通过 |

**最常被忽略的是 Contract 层和 Regression 层。** AI 可能产出看起来对的内容，但格式不符合契约（缺字段、错结构）。修改规则后可能修好了 A 问题但引入了 B 回归。Routing 若一次同时评分 train 与 holdout，两个 phase 都必须过线；不能让完美 holdout 掩盖 train 回归。

### 跨模型测试（分发型 skill 必做）

如果 skill 声明支持多个模型/平台，尽量跑完整支持矩阵；资源不足时至少选一强一弱两个代表，并明确其余组合未验证：

- **强模型看上限**：skill 的设计空间是否被充分利用，有没有过度约束压制了强模型的能力
- **弱模型保下限**：指令是否足够明确，弱模型按字面执行是否还能产出合格结果

常见失败是：在强模型上开发的 skill 依赖模型自行补全意图，换到弱模型后退化。只声明单一模型/宿主时，不为“看起来全面”虚构跨模型覆盖。

## 领域 Slop Catalog 方法论

领域 slop catalog 从真实 baseline 样本中提取重复模式。

### 核心洞察

Anti-Slop 不是一个通用清单——**每个领域都有自己独特的 AI 默认模式**。

- **中文写作 slop**：段末总结句（"这说明..."）、过度使用"随着...的发展"、三段式结构
- **代码 review slop**：泛泛的"考虑优化"建议、未引用具体行号
- **UI 设计 slop**：Inter 字体、蓝白配色、三张相同卡片、紫蓝渐变
- **Skill 文件 slop**："Consider doing X"、多语言示例、叙事性描述

### 方法论：如何为你的 skill 建 slop catalog

1. **观察 baseline**：不使用 skill，让 AI 执行同一任务 3 次，记录重复出现的默认模式
2. **标记 slop**：哪些模式是"看起来对但实际低质量"的？
3. **写 NO/OK**：每个 slop 模式给一个具体的 NO 版本（AI 的默认输出）和 OK 版本
4. **放入 Gotchas 或 reference**：作为该领域的 Anti-Slop 清单

领域 catalog 的价值来自真实 baseline 中反复出现的模式，不来自条目数量。先收集样本，再决定 catalog 应该多长。

## Design Invariants: 不可变公理

一种 "10 invariants"（不可变公理）模式。

### 概念

在 skill 的规则体系中，区分两类规则：

1. **Invariants（不可变公理）**：无论 skill 怎么迭代，这些永远不变
2. **Rules（可变规则）**：会随着迭代调整的具体数值、策略

### 示例（10 invariants）

```
1. 每个文档类型有且只有一个模板
2. 模板必须能独立运行
3. 中文标题不超过 15 字
4. 一种风格一个模板，不用参数切换
...
```

### 为什么有用

当 Gotchas 表超过 15 条时，很难判断哪些规则是"绝对不能碰"的、哪些是"可以调整"的。Invariants 把这个区分显式化——迭代时先检查 Invariants 是否被保护，然后再调整 Rules。

## Pre-Ship Checklist

部署 skill 前的最终检查清单：

### Metadata
- [ ] name 字段唯一，不与已有 skill 冲突
- [ ] description 包含 capability + trigger conditions；不强制固定开头
- [ ] description 不包含 workflow 步骤
- [ ] description 覆盖真实用户会使用的语言；只有双语用户群才要求中英文
- [ ] description ≤1024 字符

### Architecture
- [ ] SKILL.md ≤500 行；若 501–700 行，有明确保留理由或拆分计划；>700 未通过
- [ ] 所有 references 从 SKILL.md 直接引用（一层）
- [ ] 每个 reference 可独立使用，没有必需的 peer-load 链
- [ ] > 100 行的 reference 有目录
- [ ] 种子模板（如有）可独立运行

### Instructions
- [ ] Scaffold 至少有 opening / workflow / hard rules / output；Production 按实际复杂度增加模块
- [ ] 有外部可检查交付物时，Outcome Contract 明确 Outcome + Done when + Output
- [ ] 安全/不可逆/真正非协商规则用 MUST / NEVER；普通规则用祈使句 + 原因
- [ ] 不用 "consider" / "you might want to" / "try to"
- [ ] Gotchas 如存在，只包含真实案例（没有案例时删除该模块）
- [ ] NO/OK 例子中的 NO 版本真实代表 AI 默认行为

### Behavior Control
- [ ] 观察到捷径时，Anti-Rationalization 有对应修正；未观察到时不造表
- [ ] 存在不可逆操作时，Hard Stop 覆盖失败路径
- [ ] 存在真实边界时，Capability Circle 明确声明；单域简单 skill 可省略
- [ ] 需要多轮澄清时有提问预算

### Testing
- [ ] 触发测试：3 命中 + 3 未命中
- [ ] 每个被评分 phase 覆盖完整；合并评分时 train 与 holdout 都过线
- [ ] 跨模型测试（仅分发型 skill）：强模型 + 弱模型各跑一遍
- [ ] 新 session 功能测试：至少 1 个完整任务
- [ ] AI 读了 SKILL.md 正文（不只是 description）
- [ ] AI 在正确步骤加载了正确 reference
- [ ] 产出符合 Output Format
- [ ] Scaffold 若未跑 Content 层，明确标为 unproven trial，不宣称有效
- [ ] Production 有 persisted comparative evidence：受控业务指标或 run-compare
- [ ] 改动后所有受影响的 Routing / Contract / Content 路径已回归

## Review 评分框架

7 个维度，每个 1-5 分：

| 维度 | 检查什么 | 1 分 | 5 分 |
|---|---|---|---|
| **触发精准度** | Description + 触发词 | 模糊，无具体触发词 | CSO 优化，有正负例测试 |
| **信息架构** | 文件结构 + 引用方式 | 单文件 >500 行 | 三层 progressive disclosure |
| **指令清晰度** | Hard Rules + 约束 | "consider doing X" | Bright-line rules + NO/OK 对照 |
| **行为可控性** | Anti-Rationalization + 门控 | 无防护 | Red Flags + Rationalization Table + Hard Stops |
| **产出可靠性** | 验证方式 | 纯 AI 判断 | 脚本验证 + 种子模板 |
| **迭代支撑** | Gotchas + 版本管理 | 无 | 真实失败案例 + 版本追踪 |
| **Token 效率** | 加载策略 | 全部内联 | 条件加载 + 脚本执行 |

### 评分规则

- 每个维度必须引用具体的行/段落作为证据
- 不接受 "总体感觉还行" 这种评语
- 总分 < 20 → 需要重写
- 总分 20-28 → 针对性优化
- 总分 29-35 → 结构成熟，可进入 Production eval；分数本身不证明效果

## Diagnosis-Revision Split: 分离诊断与修复

AI 的常见模式：发现问题，立即改。这在 skill QA 中是危险的——因为"诊断"和"修复"是两个不同的认知任务，混在一起导致三种错误：

1. **修过头**：诊断说"这段太 AI 味"，修复时把整段重写，改变了作者的本意
2. **诊断不充分**：急于修复第一个发现的问题，忽略了更深层的问题
3. **修复引入新问题**：改了 A，破了 B，因为没有在修复前评估影响范围

诊断阶段的硬规则：
> 在能用一句话说清根因之前，不要碰代码。

修复阶段的校准规则：
> 如果删掉一个 AI 模式会改变原意，保留原文。

一种可借鉴的实践：先截图 + 逐项标注问题，全部标完后再动手改。

**Skill QA 中的应用**：review 阶段只输出诊断列表（问题 + 位置 + 为什么是问题 + 影响范围估计），不附带修复方案。revise 阶段从诊断列表出发，逐项修复并验证。如果诊断列表为空，那是一个合法结果——不要为了"显得有用"而制造问题。

## Run-Compare: 用实跑评估 skill 是否有用

这是 YW SkillFoundry 最容易被跳过、却最重要的一层。Routing 证明 skill **会被触发**，Contract 证明产出**符合契约**；效果还需要比较证据。业务系统有受控 outcome metric 时优先用真实指标，否则用 run-compare 作为默认替代。

### 核心原则

**Anti-Rationalization：看一眼输出说“没 slop、挺好的”不算验证。** AI 自评自己的产出会偏乐观。没有直接业务指标时，最小可信替代是同任务的 baseline 与 with-skill 比较；它仍只证明这组任务与模型上的差异。

### 协议(在 Cursor / 支持 subagent 的环境)

1. 从 fixture 里挑**最难的 1-2 个**任务 prompt(不是最简单的——简单任务 AI 裸跑也能做好,显不出 skill 价值)。
2. 对每个 prompt,在**同一轮**起 baseline 与 with-skill 子 agent。Exploratory 可各跑 1 次；Production 至少各跑 2 次，避免把单次采样运气当成方法价值:

   **带 skill 的子 agent:**
   ```
   Read the skill at <skill-path>/SKILL.md and follow it to complete this task:
   <task prompt>
   Save the full output to: <workspace>/with_skill.md
   ```

   **裸跑基线子 agent(同一 prompt,不给 skill):**
   ```
   Complete this task using your default approach:
   <task prompt>
   Save the full output to: <workspace>/baseline.md
   ```

3. **先持久化原始产物,再写结论。** 每次 run-compare 建目录 `evals/run-compare-<date>-<slug>/`，保存 task、全部 raw outputs、blind candidates、judge prompt、mapping、verdict，以及：
   - `runs.json`：`evaluation_level`、baseline/with-skill 的 run number、真实 model identity、output file；记录 token/time，或明确写出宿主为何不提供。
   - `judges.json`：每次 judge 的 model、`run_number`、A/B 逻辑映射、它实际读取的 candidate/prompt/evidence 文件与 verdict。
   - `manifest.json`：由 `scripts/evidence.py create` 生成，记录上述文件 SHA-256。Production 必须有 ≥2 matched run pairs；每一对都要在同一 judge model 下跑两个 A/B 位置，候选文件字节必须和对应 source output 一致。`verify` 只证明协议与工件真实完整，不替代对结论的判断。完整字段见 `evidence-schema.md`。

4. 按该 skill 自己的 **Outcome Contract 逐条 diff** 两份输出,写进 `verdict.md`:

   ```markdown
   ## Run-Compare <date> — task: <prompt 摘要>
   | Outcome Contract 标准 | baseline(裸跑) | with-skill | delta |
   |---|---|---|---|
   | <标准1> | <裸跑表现> | <带skill表现> | 改善/持平/变差 |
   | <标准2> | ... | ... | ... |

   结论:skill 的净价值 = <一句话>。证据薄弱处 = <哪几条没拉开差距>。
   ```

### 判读

- **多数标准 delta = 改善** → skill 真在起作用,过。
- **delta 普遍持平** → skill 没起作用。诊断:(a) 正文规则太弱/太抽象?(b) AI 根本没读正文(回到 Routing:description 是否泄漏了 workflow)?(c) 这个能力 AI 裸跑就会,skill 没必要存在?
- **某标准 delta = 变差** → skill 过度约束,压制了 AI 本来的能力。删掉对应的过度规则再跑。

### 噪声底:单跑一次的 delta 不算数

强模型的输出有随机性——同一个 baseline 跑两次,质量本就可能不同。**单次 run-compare 里看到的 delta,可能是 skill 的真实价值,也可能只是这一次抽样的运气;n=1 区分不了这两者。** 一份"中等 delta"的结论如果只跑过一次,其实没有证明力。

规则：Exploratory 可以 n=1 用于发现问题，但不得宣称稳定增益；Production 每侧至少 2 次，对结论模糊或关键标准跑 3 次，只认方向稳定的 delta。

- delta 只在某一次出现、重跑就消失 → 噪声,不算证据。
- delta 在多次重跑里方向一致(幅度可以波动)→ 真信号。
- routing 同理:worksheet 判定摇摆的 prompt 多判几次——触发率 2/3 是信号,1/3 是噪声。

不必重造完整 benchmark UI，但必须把每次 run、模型与可得成本指标写入 `runs.json`。需要均值/方差和规模化执行时，优先采用现成 runner；YW SkillFoundry 的 evidence spine 负责可审计协议，不冒充执行平台。

### 盲评:diff 的人不该知道哪份是 with-skill

run-compare 最隐蔽的偏差:**逐条 diff 两份输出的是作者本人,而且知道哪份带 skill——你当然会希望自己的 skill 赢。** 这和 routing 里 worksheet 藏标签防的是同一种偏差,只是 content 层很容易忘了藏。

盲评变体(主观产出尤其必做):

1. 把 baseline 与 with-skill 两份输出**去掉来源、随机编号 A/B**。
2. 起一个**没读过这个 skill** 的 subagent,只给该 skill 的 Outcome Contract,让它判 A/B 哪个更好、为什么。
3. judge 选完再揭晓编号。选中 with-skill 才是干净证据;选中 baseline → skill 没价值,或在帮倒忙。

这就是 worksheet 那个 trick 搬到 content 层:同一套"去标签 + 独立判官"纪律,只是判的对象从"会不会触发"换成"产出好不好"。

### 盲评的 4 个去偏强化

裸“盲 A/B”还能更稳——下面四项各自堵一个可观察偏差：

1. **位置交换去偏**:judge 可能受候选顺序影响。每对 A/B **跑两次、交换位置**,两个方向都赢才算赢;只赢一次 = 顺序敏感,记平。
2. **hard-gate 事实注入**:把能确定性数出来的事实塞进 judge prompt 当硬约束,堵 judge 幻觉质量——例:"该输出含 0 处 Outcome Contract 标准的证据,所以'完整性'一项不得高于 2 分"。判官不能给不存在的质量打高分。
3. **逐维独立判官 + Unknown 逃生口**:别用一个 judge 一次评所有维度;每个标准开一个独立判断,并给它"证据不足就返回 Unknown"的出口——逼它要么拿证据,要么认不知道,而不是编个分。
4. **人审校准一次**:自己先手判几条,再比对 judge 的判,看它系统性偏松还是偏紧,把偏差写回 rubric。校准过一次后,后续只偶尔人审。

不想自己搭时，选择能保存 raw outputs、位置交换、hard-gate、成本指标和版本回归的现成 runner；在采用前用一个小 fixture 验证它真的记录这些工件。

### 轻量降级(无 subagent 时)

单 session 里没法真“裸跑对比”（当前上下文已经读过 skill）。降级方案：先在干净 session 里保存 baseline，再开带 skill 的 session 跑同一任务并盲评。它比同一上下文自评更可信，但仍要标注模型与环境差异。

### 何时必须做 / 可跳过

- **Production 效果声明** → 必须有比较证据：受控业务指标优先，否则 run-compare。
- **主观产出**(写作风格、视觉设计)→ run-compare 的逐条 diff 换成盲选 + rubric，不能由作者自评。
- **Scaffold 试用版** → 可暂缓 Content 层，但必须标为 unproven，不能写“已提升”。
- **纯一次性、不复用的 skill** → 本就不该做成 skill(见 Discover 的资格判断)。

## Citation Discipline: 正文不出现读者打不开的名字

**正文（会被加载进 context 的 SKILL.md + references）里不点名任何私有/内部 skill。** 一个读者打不开的名字，对他没有任何价值：它既不能被核实，也不带公认权威，纯粹占 context、读着像在打广告。技术和证据才是承重的——把它们留下，把名字去掉。

判断一条引用该不该留在正文，只看一个问题：**读者能不能就地用上它？**

| 类型 | 留还是去 |
|---|---|
| **技术 / 模式本身**（"用 .5 步骤做静默检查点"、"4 波段密度模型"） | **留**——直接讲清楚，不挂出处 |
| **可就地验证的证据**（规则原文、NO/OK 片段、具体数值） | **留**——内联进来，让读者当场就能验 |
| **公开、可核、有权威的引用**（Meincke et al. PNAS 2026、Lost in the Middle、Anthropic 官方规范、agentskills.io） | **留**——读者真能去查，是承重证据 |
| **私有 / 内部 skill 名**（读者打不开的） | **去**——保留它旁边的技术和证据，删掉名字这个前缀 |

**铁律：陈述一条做法时，正文给的是"技术 + 可就地验证的证据"，不是"某某 skill 这么做的"。** 公开出处属于一次性致谢（放 `CHANGELOG.md` 或 evidence note），不属于每条规则的前缀。

去名的写法（不是删内容，是删署名前缀；下面用 `<某私有skill>` 代指任何读者打不开的名字）：
- `"<某私有skill> 记录了 94%…"` → 有原始样本就内联可复算数据；没有就只写 `"能力不可用时，先停下并报告，不自行替代。"`
- `"Registry 模式（<某私有skill> 验证）"` → `"Registry 模式"`
- `"来自 <某私有skill> 的硬规则:‘…’"` → 直接把那条规则作为陈述写出来

自检（可用 `scripts/citation_lint.py` 自动跑）：正文里是否还出现任何读者打不开的 skill 名？出现即删——把它旁边的技术和证据留下即可。`examples/worked-example.md` 用"写 commit message"这个谁都能复现的领域，零私有引用地把全套工艺演示了一遍,是这条纪律的范例。

## 规则单一真源

跨文件重复的阈值和门控统一由 `invariants.md` 定义。本文负责解释为什么和怎么验证，不另起一套数字。改动 metadata、行数、模块、reference、routing 或 evidence 规则时：

1. 先更新 `invariants.md`；
2. 再更新 validator / eval 脚本；
3. 最后同步解释性文档并补 bite test。

如果解释性文档与 invariants 冲突，以 invariants 为准；冲突本身算回归缺陷。
