# Prompt 模式库

## 目录

- [Opening Statement: 设定 Mental Model](#opening-statement-设定-mental-model)
- [Outcome Contract: 完成标准](#outcome-contract-完成标准)
- [Mode Router: 多路径入口](#mode-router-多路径入口)
- [Step Machine: 结构化执行](#step-machine-结构化执行)
- [Hard Rules: 绝对边界](#hard-rules-绝对边界)
- [Gotchas Table: 从失败中学习](#gotchas-table-从失败中学习)
- [条件引用: 按需加载](#条件引用-按需加载)
- [NO/OK 对照例: 模式矫正](#nook-对照例-模式矫正)
- [形式匹配失败: 先诊断失败类型再选模式](#形式匹配失败-先诊断失败类型再选模式)
- [Authority 用词: 说服原则](#authority-用词-说服原则)
- [自由度控制](#自由度控制)
- [Context Preflight: 执行前检查](#context-preflight-执行前检查)
- [Output Format: 交付物定义](#output-format-交付物定义)
- [Direction Lock: 先约束再执行](#direction-lock-先约束再执行)
- [Premise Breakdown: 假设前审查](#premise-breakdown-假设前审查)
- [Decision Tree: 结构化选择](#decision-tree-结构化选择)
- [Truth-Source Precedence: 输入冲突裁决](#truth-source-precedence-输入冲突裁决)
- [Reasoning Model 注意事项](#reasoning-model-注意事项)
- [写作顺序建议](#写作顺序建议)

---

## Opening Statement: 设定 Mental Model

SKILL.md 的第一句话（title 之后、Outcome Contract 之前）设定 AI 理解整个 skill 的框架。

### 为什么重要

LLM 是自回归模型——前面的 token 影响后面所有 token 的生成概率。Opening Statement 相当于给后续所有行为设定了概率分布的偏置。

### 写法

一到两句话。不解释 skill 做什么（那是 description 的工作），而是说明**为什么需要这种做法**，或**默认行为有什么问题**。

```
NO: "This skill helps you write better prompts."

OK: "AI 可能回退到宽泛的默认模式。
     这个 skill 用明确词汇、可运行检查和对照证据约束关键决策。"
```

第二种写法告诉 AI 两件事：1）具体失败模式是什么，2）替代方案如何被验证。它比泛泛承诺“更好”更可执行，但实际影响仍要在目标任务中测量。

## Outcome Contract: 完成标准

防止 AI 漫游（做超出范围的事）或提前收工（跳过验证直接交付）。

### 标准结构

```markdown
## Outcome Contract
- **Outcome**: [一句话描述成功是什么样的]
- **Done when**: [可验证的完成条件]
- **Evidence**: [结论/产出必须基于什么证据]
- **Output**: [具体交付物和格式]
```

### 关键：Done when 必须可验证

```
NO: Done when: the skill works well.
OK: Done when: trigger_eval score 在 holdout 上通过、run-compare 显示
    with-skill 相对 baseline 的真实 delta、citation_lint 与 validate-skill 干净。
```

"works well" 是主观的——AI 可以在任何时候声称自己做完了。"通过可运行的检查" 是客观的——没通过就不能交付，且不能自我声称通过。

### Evidence 字段的作用

约束 AI 的结论来源。没有 Evidence 字段，AI 可以凭训练数据中的"常识"下结论。有了它，AI 必须引用具体来源。

## Mode Router: 多路径入口

当一个 skill 服务于多种用户意图时，用 Mode Router 在入口处分流，而不是在执行中处处判断。

### 表格形式（推荐）

```markdown
| 信号 | 模式 | 行为 |
|---|---|---|
| "从零开始写" | Write | 走完整 7 步 |
| "优化现有的" | Optimize | 诊断 → 修复 |
| "检查质量" | Review | 评分 + 建议 |
```

### 为什么表格 > 条件语句

表格是视觉化的路由表，AI 可以一次扫描所有路径并选择。if/else 条件语句容易在中间位置被忽略。

### 模式数量

2-4 个。超过 4 个说明 skill 范围太大，应该拆分成多个 skill。

### 互斥模式 vs 可叠加模式

默认假设：模式互斥——选一条路走完。但方法论 skill（诊断、审查、研究）的模式通常是**可叠加的工具**——Bisect 找到问题提交后进入 Scope Blast 扫描同类 bug，两者在同一次执行中依次激活。

```
互斥模式（生成 skill）：
| "杂志风" | Editorial | — |
| "数据风" | Swiss | — |
→ 选一个，执行完毕

可叠加模式（方法论 skill）：
| "以前是好的" | Bisect | 找到 culprit 后可叠加 Scope Blast |
| "举一反三" | Scope Blast | — |
→ 一次诊断可能经过多个模式
```

如果你的 skill 的模式之间有**输入-输出依赖**（A 的结果是 B 的输入），它们就是可叠加的。把它们放在同一个 SKILL.md 中（不要拆成独立文件），确保模式间共享 context。

## Step Machine: 结构化执行

按编号步骤组织工作流，每步有明确的输入、动作、和验证。

### 基本形式

```markdown
### Step 1: 目标拆解
回答 3 个问题：
1. ...
2. ...
3. ...

### Step 2: Description 设计
读 `references/description.md`，执行 CSO 规则。

### Step 3: ...
```

### 高级：小数步骤

用 .5 步骤作为静默检查点：

```markdown
### Step 2: 内容生成
...

### Step 2.5: 静默校验（不输出给用户）
检查内容是否超出容器。如果超出，修复后继续。

### Step 3: 排版
...
```

.5 步骤的作用：在 AI 对用户说"完成"之前，强制执行一次自我检查。用户看不到这个步骤，但它能捕获大量错误。

### 步骤引用整合

每个步骤在需要时才指向 reference 文件：

```markdown
### Step 3: 架构决策
读 `references/architecture.md`，回答以下问题：
```

不要在 SKILL.md 顶部一次性列出所有 reference。那样 AI 可能在 Step 1 就把所有文件都读了——浪费 context 且信息太早加载会被遗忘。

## Hard Rules: 绝对边界

没有灰度的规则——要么做，要么不做。

### Authority 原则（三档语域，与 SKILL.md Hard Rules 一致）

语气强度必须匹配规则的赌注，不是一律最强：

1. **不可协商 / 不可逆 / 安全类** → MUST / NEVER / No exceptions。
2. **普通规则** → 祈使句 + 理由（"Do X, because Y"）。理由让规则可以迁移到未列举情形；把 MUST 堆在普通规则上还会模糊真正不可协商的少数规则。
3. **任何档位都禁止**弱词："consider"、"try to"、"you might want to"——它们授予跳过许可。

```
NO: "Try to keep the file under 500 lines."        (弱词，任何档位都不行)
NO: 15 条规则全部 MUST/NEVER                        (稀释，AI 分不清哪条真的碰不得)

OK: "Description 禁止包含 workflow 摘要。"           (档位 1：违反即路由失效)
OK: "把能脚本验证的规则写成脚本，因为文字规则每次执行
     都要靠 AI 自觉，脚本不会。"                      (档位 2：祈使 + 理由)
```

证据边界要诚实：Meincke et al.（PNAS 2026）的说服实验测的是“说服技巧能否提高模型对受限请求的顺从”，不是 Skill 指令合规。它至多说明模型可能受权威框架影响，不能换算成“多写 MUST 就提升多少合规率”。这里真正承重的理由是语义：弱词允许跳过，强祈使不允许；直接效果必须用目标 skill 的 run-compare 验证。

### 数量控制

Hard Rules 从真正非协商的最小集合开始。规则变多时，检查冲突、重复和中间规则是否在压力测试中被跳过；把低频领域规则放进按需 reference，而不是追求固定条数。

## Gotchas Table: 从失败中学习

Gotchas 是实际发生过的失败案例——不是假设性的风险，而是真实的教训。

### 格式

```markdown
| What happened | Rule |
|---|---|
| [具体场景描述] | [对应的约束规则] |
```

### 为什么比抽象规则有效

LLM 的模式匹配能力远强于抽象推理能力。"始终检查工作目录" 是抽象的——AI 不知道在什么场景下会出错。"Moved files to ~/project, repo was at ~/www/project → 结果删错文件" 是具体的——AI 能在类似场景中直接匹配。

### 来源

Gotchas 来自：
1. 你自己使用 skill 时遇到的问题
2. 别人使用你的 skill 时报告的问题
3. 你在测试中发现的 edge case

一个成熟 skill 的 Gotchas 表会记录已泛化、已去除私人上下文的连续迭代
失败案例。具体任务记录留在仓库外；公开 skill 只保留可复用且隐私安全的
模式。

## 条件引用: 按需加载

```markdown
当 [条件] 时，读 `references/[文件].md`。
```

### 两种条件类型

**场景条件**（推荐）：

```markdown
当用户提供了截图时，读 `references/screenshot-analysis.md`。
当需要处理多语言内容时，读 `references/i18n-rules.md`。
```

**步骤条件**：

```markdown
### Step 4: 起草 SKILL.md
读 `references/prompt-patterns.md` 获取详细写法。
```

### Reference Map 表格

在 SKILL.md 尾部用表格汇总所有引用关系——方便人类审查，也帮助 AI 建立全局文件地图：

```markdown
## Reference Map
| 文件 | 加载条件 |
|---|---|
| `references/style.md` | Step 2 或涉及视觉设计时 |
| `references/qa.md` | Step 5（校验）|
```

## NO/OK 对照例: 模式矫正

展示 AI 的默认行为（NO）和期望行为（OK），利用 LLM 的模式匹配能力直接矫正。

### 为什么有效

告诉 AI "不要写得太长" 是抽象指令。展示一个 150 字的 NO 版本和一个 50 字的 OK 版本，AI 可以直接从对比中学习"长度"的具体含义。

### 写法

```markdown
```
NO: "I'll now explain the comprehensive methodology for analyzing
     React component performance, including detailed profiling
     strategies and optimization approaches."

OK: "你的 UserList 组件每次父组件更新都重新渲染。原因是传入了
     新的 inline function 作为 onClick prop。用 useCallback 包裹。"
```
```

关键：NO 版本必须是 **AI 真的会写出来的东西**，不是刻意编造的糟糕例子。如果 NO 版本太离谱，AI 不会觉得自己和它有关系。

### 一个好例子 > 五个平庸例子

```
NO（信息过载）:
  例1: JavaScript 版本
  例2: Python 版本
  例3: Go 版本
  例4: 简单版
  例5: 复杂版

OK（精准打击）:
  例: [一个中等复杂度、覆盖核心模式的例子]
```

多语言/多难度例子稀释注意力。一个覆盖核心模式的好例子比五个分散注意力的例子有效。

## 形式匹配失败: 先诊断失败类型再选模式

本文件的每个模式各治一种病。最常见的误用是"默认全上"——给每个 skill 都配齐 Router、Interceptor、Hard Rules、Anti-Rationalization。**先看 baseline 到底怎么失败，再选对应形式**：

| 失败类型 | 症状 | 对应形式 |
|---|---|---|
| **做了不该做的** | AI 加了不需要的东西（过度工程、编造链接） | 禁令 + 理由（Hard Rule / NO 例） |
| **不知道怎么做** | AI 缺领域流程，输出结构混乱 | 配方（Step Machine / 模板） |
| **知道但顺序错** | AI 会做每一步，但跳步、乱序 | 结构约束（编号步骤 + gate） |
| **只在特定条件下错** | 平时对，遇到某类输入才错 | 条件规则（"当 X 时，做 Y"+ Gotcha） |
| **给自己找借口跳过** | transcript 里出现"这次情况特殊…" | Anti-Rationalization / Thought Interceptor |

诊断来自 Step 1 的 baseline 和 Step 7 的 transcript，不来自想象。用禁令去治"不知道怎么做"（AI 更迷茫），用配方去治"找借口"（AI 照着配方继续找借口），都是形式错配——写得再精致也不起作用。

## Authority 用词: 说服原则

间接证据：Meincke et al.（PNAS 2026）观察到说服框架会改变模型对受限请求的顺从，但那是另一个任务域，不能直接换算成 Skill 规则合规率。真正承重的理由是语义：弱词允许跳过，强祈使不允许。且这**不是“全用 MUST”的许可证**——见下面的分层。

### 关键张力：MUST 不是越多越好

两者如何统一：**权威措辞只留给不可协商的少数；普通规则优先解释原因。** 规则越多，冲突、重复和注意力竞争的机会越多；这不是一个固定比例定律，必须通过组合压力测试确认。给出 why 是为了让规则能迁移到未列举情形，不是因为任何模型都保证会“理解精神”。

### 三档措辞分层（按 stakes 选）

| 档 | 适用 | 写法 | 例 |
|---|---|---|---|
| **Authority** | 不可逆 / 安全 / 会造成损害的少数 | MUST / NEVER / No exceptions | "发布前 NEVER 跳过 run-compare。" |
| **Imperative + Why** | 绝大多数规则 | "做 X，因为 Y" | "diff 已经显示改了什么，正文唯一的价值是讲清为什么——重述 diff 等于浪费读者注意力。" |
| **禁用** | 任何场景 | ~~consider / try to / you might want to~~ | 软词给了跳过的许可，删掉或升档 |

注意第二档**不是**第三档：解释 why 仍然是祈使 + 给出理由，不是"建议你考虑"。"Do X because Y" 既有方向性又有可理解性，比裸 MUST 更经得起前沿模型的迁移。

### Authority（用于第一档）

```
MUST / NEVER / 必须 / 禁止 / No exceptions
"Description 禁止包含 workflow 摘要。"（这条属不可协商：泄漏会让 AI 跳过正文）
```

适用：不可逆 / 安全 / 核心契约级的少数 Hard Rules——不是全部。

### Commitment（适量使用）

让 AI 先声明意图，然后更可能遵守。

```
"开始执行前，先说明你将采用哪个 Mode。"
"首先确认你已经理解了 Outcome Contract 的完成标准。"
```

适用：关键分支点。

### Scarcity（谨慎使用）

```
"IMMEDIATELY read the skill before proceeding."
"在做任何其他事情之前，先完成 Step 1。"
```

适用：容易被跳过的初始步骤。

### 不使用的原则

- **Reciprocity**（"我帮了你，你也该..."）：对 AI 无意义
- **Liking**（"作为你的朋友..."）：对 AI 无意义
- **Social Proof**（"其他 AI 都这么做"）：有微弱效果但不够可靠

## 自由度控制

每条指令都可以被放在一个自由度频谱上：

```
高自由度                                   低自由度
"写一些测试" → "为每个公开方法写测试" → "用这个模板写 3 个测试"
```

### 选择自由度的原则

- **AI 擅长的领域**（代码逻辑、语言翻译）→ 给更多自由度
- **AI 不擅长的领域**（视觉设计、风格一致性）→ 低自由度，提供模板
- **关键约束**（安全、格式、不可逆操作）→ 零自由度，Hard Rule

### 默认方案 + Escape Hatch

不要给 AI 5 个等价选择。给一个默认方案 + 一个替代条件：

```
NO: "你可以选择 A、B、C、D 或 E 方案。"

OK: "默认使用 A 方案。当 [具体条件] 时，改用 B 方案。"
```

AI 面对多个等价选择时会纠结并做出低质量的折中。给一个默认方案消除选择焦虑。

## Context Preflight: 执行前检查

在 workflow 开始前确认 AI 有所需的上下文。

```markdown
## Context Preflight
在开始前确认：
- [ ] 用户提供了目标 skill 的用途描述
- [ ] 有明确的触发场景（至少 3 个）
- [ ] 知道目标平台（Cursor / Claude Code / OpenAI）
如果缺少以上任一项，先向用户询问，不要假设。
```

### 弱先验策略

当需要向用户提问时，先基于已有信息给出一个"弱假设"，然后请用户确认或修正：

```
NO: "请问这个 skill 是用在什么场景的？"

OK: "从你的描述来看，这个 skill 的主要场景应该是代码审查。
     除此之外还有哪些触发场景？"
```

弱先验降低用户的回答负担（确认比从零描述容易），同时展示 AI 的理解程度。

### 提问预算

每轮提问不超过 3 个问题。问太多 → 用户疲劳。问太少 → 关键信息缺失。

3 个以内的问题，每个都应该指向不同维度（场景、约束、偏好），不要在同一维度追问。

## Output Format: 交付物定义

明确 AI 应该交付什么。不同精度有不同效果：

```
低精度: "输出一个 skill"
中精度: "输出 SKILL.md + references/"
高精度: "输出 SKILL.md（默认 ≤500 行），references/ 目录下按需拆分深度内容，
         可选 scripts/ 目录放验证脚本。SKILL.md 包含 Outcome Contract、
         Mode Router、Workflow、Hard Rules、Gotchas Table。"
```

具体格式可以减少歧义，但不是越长越好。只约束下游真正依赖的结构，
并用 Contract 或 run-compare 验证它是否改善目标结果。

## Direction Lock: 先约束再执行

"Lock the Direction First"——在开始昂贵且方向分叉明显的工作之前，用少量约束性问题缩小解空间。它的价值是提前暴露方向错误；节省多少返工取决于任务，不能预设固定倍数。

### 一组示例：设计类 skill 的 5 个方向问题

1. 谁在用？什么场景？
2. 美学方向是什么？（"干净现代"不是方向——要具体到属性）
3. 设计签名是什么？
4. 硬约束是什么？
5. 标志性微交互是什么？

"Do not proceed until all five are answered."

### 泛化

任何 skill 都可以定义自己的 Direction Lock 问题。关键：
- 问题指向**不可逆决策**——选错后所有后续工作浪费
- 问题的答案**消除歧义**——从多种可能收窄到一种方向
- 数量 **3-5 个**——太少不够约束，太多用户疲劳

## Premise Breakdown: 假设前审查

一种通用的执行前审查模式。在执行复杂任务前，列出所有隐含假设，标记证据强度：

```
前提: [假设] → 证据: 硬（已验证） / 软（部分推测） / 无
```

"软"或"无"的假设 → 先验证再执行。不要带着未验证的假设行动。

AI 的默认行为是"带着所有假设一起跑"——Premise Breakdown 强制 AI 暴露认知盲区。对简单任务跳过。

## Decision Tree: 结构化选择

适用于工具选择、Bisect 诊断等场景。当 AI 面对多个工具/方法/路径时，用决策树替代自由选择：

```markdown
- 图片 < 500KB 且是照片？→ cwebp
- 图片 < 500KB 且是截图？→ pngquant
- 图片 > 500KB？→ 先缩放再按上述压缩
```

为什么通常比"自己选"稳定：决策树把开放选择收窄为可检查的条件匹配，减少训练偏见带来的路径漂移。它不能保证正确；条件写错、输入缺失或边界重叠时仍会失败，必须用目标任务 eval 验证。

## Truth-Source Precedence: 输入冲突裁决

Evidence Ladder（behavior-control.md）排的是 AI 自产证据的可靠性；这个模式排的是**用户给的多个输入源互相矛盾时，谁说了算**。

多输入 skill（视频+字幕+文稿、代码+文档+注释、数据+分析报告）可能遇到来源冲突。不写裁决顺序时，模型可能自行选择最容易处理的来源，而不是最可靠或最新的来源。

例如，视频剪辑可以这样定义：

```markdown
真相源优先级：
实际音频 / 字幕 > 剪后视频画面 > 素材文件 > 文稿草稿

如果文稿和实际字幕不一致，以字幕和音频为准。
```

写法要点：**一行排序 + 一句冲突裁决规则**，放在输入定位（Context Preflight）之后。对应到代码类 skill：运行时行为 > 测试 > 代码 > 注释 > 文档。

何时使用：skill 接受 2+ 个可能互相矛盾的输入源时。单输入 skill 不需要。

## Reasoning Model 注意事项

支持 extended reasoning 的模型会自行展开推理。

**核心原则：State the goal, not the procedure。**

```
NO（对 reasoning model 过度约束）:
  "Step 1: 分析问题。Step 2: 列出原因。Step 3: 评估每个原因。"
→ 触发冗余推理，增加延迟

OK（给目标和约束）:
  "找到这个错误的根因。必须基于运行时证据。3 次假设失败就停下来。"
```

Step Machine 用于引导**工具调用和文件读取顺序**，不约束推理过程。对推理能力较弱或不稳定的目标模型，显式外部步骤仍可能有价值，但要实测。

## Progressive Depth: 模式作为可叠加阶段

Mode Router 的默认模型是「分叉」——选一条路走完。但优秀的 skill 设计中，模式可以是**可叠加的 pipeline 阶段**：

```
翻译类 skill:
  quick（直译）→ 交付
  normal（分析+翻译）→ 交付 → 用户说「继续润色」→ refined（review+polish，在已有产出上追加）

研究类 skill:
  Quick Reference → Phase 1-2 → 交付笔记
  Deep Research → Phase 1-6 → 交付长文
  （Phase 3-6 不是重跑，而是在 Phase 2 产出上继续）
```

关键设计：**升级不重跑**——refined 模式在 normal 的已有产出上追加 review + polish，不需要重新翻译。这降低了首次交付的摩擦（用户先拿到一个能用的版本），同时保留了高质量出口。

何时使用：当 skill 的模式之间存在**包含关系**（A 是 B 的子集）而非互斥关系时。在 Mode Router 中标注：

```markdown
| 信号 | 模式 | 可升级到 |
|---|---|---|
| "快翻" | Quick | Normal, Refined |
| "翻译" | Normal | Refined |
| "精翻" / "继续润色" | Refined | — |
```

升级钩子写在交付步骤中（不是单独的 step）：交付后显示一行升级提示即可。

## Completion State Protocol: 完成态状态码

Outcome Contract 定义"什么算完成"。Completion State Protocol 更进一步——定义**完成的不同状态**和每种状态的后续行为：

```
DONE                 全部完成，无遗留
DONE_WITH_CONCERNS   完成但有风险/遗留项需用户知晓
BLOCKED              无法完成，列出阻塞原因和缺失信息
```

一个发布校验实践：推草稿箱只有"命令完成 + 回读 + 校验图片 + 校验尾标"四项全过才能报 DONE。不能只凭 media_id 判断成功。

Publish Stop Boundary：报告"ready to publish"后**硬停**——不自动上传、发布、分享，除非用户显式要求。

何时使用：任何涉及**外部系统交互**（发布、推送、API 调用）的 skill。纯文本生成类 skill 通常不需要。

## 写作顺序建议

不要从 Opening Statement 开始写——那是最难写好的部分。

推荐顺序：
1. **Outcome Contract** → 先想清楚完成标准
2. **Hard Rules** → 然后想清楚绝对约束
3. **Workflow Steps** → 用步骤串联执行流程
4. **Gotchas Table** → 从已知问题中提取教训
5. **Mode Router** → 如果需要多路径
6. **Reference Map** → 确认引用关系
7. **Opening Statement** → 最后写，因为此时你已经完全理解了 skill 的核心
8. **Description** → 最最后写，因为它需要精确到每个词
