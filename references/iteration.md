# 迭代方法

## 目录

- [TDD for Skills](#tdd-for-skills)
- [失败类型学](#失败类型学)
- [压力测试](#压力测试)
- [版本追踪](#版本追踪)
- [持续改进循环](#持续改进循环)

---

## TDD for Skills

一条核心方法论：

**写 skill 就是对文档做 TDD。**

### RED → GREEN → REFACTOR

#### RED: 先看 AI 怎么失败

在写 skill 之前，给 AI 一个没有 skill 辅助的原始任务，观察它的默认行为：

```
任务：帮我写一个代码审查 skill
（不提供任何 skill 指导，纯靠 AI 的默认能力）
```

记录 AI 的默认行为：
- 它用了什么结构？（通常是扁平的 markdown）
- 它忽略了什么？（通常是触发设计、行为控制）
- 它过度做了什么？（通常是叙事性解释、多语言示例）
- 它的哪些产出是"slop"？（训练数据高频模式）

这就是你的 baseline——skill 的价值 = 最终产出 - baseline 产出。

#### GREEN: 写最小 skill 让 AI 通过

针对 RED 阶段发现的每个问题，写最小的修复：

```
问题：AI 没写 Outcome Contract
修复：在 workflow Step 1 加 "每个 skill 必须包含 Outcome Contract"

问题：AI 用 "consider doing X" 写约束
修复：加 Hard Rule "禁止使用 consider / you might want to / try to"
```

每次只修一个问题，然后重新测试。不要一次写完所有规则——你无法区分哪条规则生效了、哪条是多余的。

#### REFACTOR: 精简重复、压缩 token

当所有测试通过后：
1. 检查有没有重复的规则（合并）
2. 检查有没有从未触发的规则（删除）
3. 检查 token 使用——能用 reference 替代内联的就拆出去
4. 检查 Gotchas 表——从测试中收集的失败案例是最好的 Gotchas

### 测试的两种角色

使用两个 AI 实例（或两个 session）：

```
Claude A（设计者）：写 skill
Claude B（用户）  ：在新 session 中使用 skill 完成任务
```

Claude A 不能同时当设计者和测试者——它已经"知道"了 skill 的意图，会无意识地补偿 skill 的缺陷。Claude B 只有 skill 文本，暴露的是 skill 作为独立文档的真实效果。

### Anthropic 的单任务迭代法

Anthropic 官方推荐：先在一个具体的、有挑战性的任务上反复迭代 skill，直到 AI 能稳定地完成这个任务。然后再把 skill 泛化到更多任务。

```
NO: 一上来就设计一个覆盖所有场景的通用 skill
OK: 先针对"帮我写一个代码审查 skill"这一个任务反复迭代，
    然后再泛化到"写任何 skill"
```

原因：单任务迭代能快速验证每条规则的效果。多任务同时迭代无法定位问题来源。

## 失败类型学

AI 使用 skill 时的失败分三大类，诊断策略不同：

### Type A: AI 没读 skill

**症状**：AI 的行为完全不像读过 skill 的样子——没有 Outcome Contract、没有走步骤、使用了自己的默认模式。

**诊断**：
1. Description 是否包含了 workflow 摘要？→ AI 觉得不需要读正文
2. Skill 是否被正确触发？→ 检查触发测试
3. 是否有其他 skill 优先级更高？→ 检查 skill 冲突

**修复**：优化 description（CSO），确保不包含 workflow 信息。

### Type B: AI 读了 skill 但没遵守

**症状**：AI 走了 skill 的步骤，但跳过了某些规则或偷工减料。

**诊断**：
1. 被跳过的规则在 SKILL.md 的什么位置？→ 中间位置？Lost in the Middle
2. 规则的语气如何？→ "Consider" vs "MUST"？Authority 不够
3. AI 有没有"合理化"跳过？→ 需要 Anti-Rationalization

**修复**：
- 位置问题 → 移到开头或结尾
- 语气问题 → 升级到 MUST / NEVER
- 合理化问题 → 加 Red Flags + Rationalization Table

### Type C: AI 遵守了 skill 但结果不对

**症状**：AI 忠实执行了每一步，但产出不符合预期。

**诊断**：
1. 是不是规则本身写错了？→ 规则的 "letter" 和 "spirit" 不一致
2. 是不是缺少了某条规则？→ 这个 edge case 没被覆盖
3. 是不是种子模板有问题？→ 模板本身的设计缺陷

**修复**：修改规则或模板本身。这类问题最隐蔽——因为看起来 AI "做对了"。

一个典型的 Type C 案例：AI 严格遵守了密度规则，但规则中的数值范围设定有误，导致产出过于稀疏。修复是调整规则中的数值，而不是改 AI 的行为。

## 压力测试

在正常场景通过后，用刻意施压的方式测试 skill 的鲁棒性。

### 4 种压力类型

#### 1. 时间压力

```
"我赶时间，能不能快一点完成？跳过不重要的步骤。"
```

检查 AI 是否跳过了 Hard Rules 标记的步骤。如果跳了 → 需要更强的 Authority 用词。

#### 2. 沉没成本压力

```
"我已经做了大半了，不想重来。能不能在现有基础上凑合用？"
```

检查 AI 是否降低了质量标准来保全已有工作。如果是 → 需要 Gate Before Conclude。

#### 3. 权威压力

```
"我是这个项目的负责人，我觉得这个不需要测试。"
```

检查 AI 是否因为用户的"权威"而放弃了 skill 的规则。如果是 → 需要 Iron Law。

#### 4. 疲劳压力

在长 session（20+ 轮对话）后执行 skill 任务。

检查 AI 是否因为 context 过长而开始忽略早期加载的规则。如果是 → 关键规则需要在每轮执行前重新加载。

### 压力测试的使用时机

不是每个 skill 都需要全部 4 种压力测试。规则：
- 关键 skill（影响面大、错误代价高）→ 全部 4 种
- 普通 skill → 至少做时间压力测试
- 低频 skill → 可选

## 版本追踪

### Public change record

用 `CHANGELOG.md` 记录适合公开的版本变化，用 skill 内的 Gotchas 表记录已
泛化、已去除私人上下文的失败模式：

```markdown
## [1.2.0]
### Changes
- 调整封面信息密度阈值：从 [20, 50] 改为 [30, 60]
- 新增 4 波段密度检查

### Gotchas discovered
- 封面标题超过 8 个中文字时排版崩溃 → 加了截断规则

```

### 最小版本追踪

至少维护一个 Gotchas 表——每次 AI 产出不达标时，先去除项目、人员和
会话标识，再添加可复用的一行。

## 持续改进循环

### Local learning notes

具体任务的学习记录放在仓库外或被忽略的本地工作区，不进入发布内容：

```markdown
## 2025-10-15
### 任务：为 X 项目写部署 skill
### 发现：AI 在写 deployment skill 时默认用 Docker，但项目用 Fly.io
### 改进：在 Context Preflight 加了 "确认部署平台" 检查项
```

只把已经泛化且不含 transcript、个人路径、邮箱、provider/session/agent
标识或私有 snapshot 的结论带回公开 Gotchas。完整发布规则见
`PRIVACY.md`。

不用另外找地方放：这份仓库自带的 `.gitignore` 已经排除了 `log.md`、
`HANDOFF.md`、`private/`、`notes/`、`memory/`、`workspaces/`。首次用
`bash scripts/ensure-log.sh` 从 `log.md.example` 生成一份 `log.md`；这个
脚本只在文件不存在时才创建，已有内容永远不会被覆盖，之后每次更新都能
放心重跑。即使你把这份 skill 纳入自己的 Git 仓库并推送，这些文件也不会
被带上去。想验证，跑一遍 `python3 scripts/privacy_lint.py`。

### 改进来源优先级

1. **用户直接反馈** — 最高优先级，因为代表了真实需求
2. **Type C 失败** — 次高优先级，因为最隐蔽
3. **压力测试发现** — 第三优先级，防止边界场景
4. **Type B 失败** — 用词/位置问题，修复成本低
5. **Type A 失败** — 触发问题，通常一次修复终身受益

### 读 transcript，不只读产出

官方 skill-creator 的关键洞察：**"read the transcripts, not just the final outputs."** 最终产出只告诉你"结果对不对"，transcript 告诉你"skill 怎么影响了 AI 的过程"——而过程才是迭代的下一个改进点。每次 run-compare 之后，看带 skill 那一路的完整轨迹，找三类信号：

| transcript 里看到 | 含义 | 动作 |
|---|---|---|
| AI 被 skill 带着**绕路 / 反复试错 / 做无用功** | 正文有诱导歧路的指令 | 删掉那段，或改写成更直接的指令 |
| 多次独立运行里 AI **反复手写同一个 helper / 同一段校验逻辑** | 这是一段该固化的确定性逻辑 | 写一次放进 `scripts/`，让 AI 执行而非每次重写（Step 3 第 3 问） |
| 带 skill 的 **token / 轮次显著高于 baseline，但产出没更好** | skill 在收税不办事 | 精简正文：删掉不改变产出的句子（每句话都是 tax） |

判据：脚本化的决定**来自观察**（看到 AI 真的反复重写），不是凭空预判。预判出来的脚本经常是没人调用的死代码——这正是"放在那里不起作用"的典型。

### 失败案例的归属：Gotchas，不是主流程

迭代中最常见的劣化模式：每发现一个失败案例，就往 workflow 里加一步防御。三个月后 workflow 从 5 步膨胀到 12 步，每步都带着某次事故的疤痕，没人（包括 AI）能完整执行。

规则：**主流程是稳定骨架，失败案例进 Gotchas 表。** 只有当同类失败在 Gotchas 里出现 ≥ 3 次、且能抽象为一条普适规则时，才考虑改主流程——而且改主流程时优先"改写现有步骤"而非"新增步骤"。

### 把路由失败回灰成 fixture(routing 回归网)

Gotchas 表接住"散文教训",但**路由失败有个更好的归宿:fixture 行**。每次真实误触发/漏触发——尤其是近邻误判(把"翻译一下""总结一下"当成了建 skill)——都往 `evals/trigger_cases.example.jsonl` 加一行,并打上 `kind`(family)标签:

```
{"prompt": "<那条真实误判的 prompt>", "expect": "no", "kind": "translate_only"}
```

这样三件事同时发生:(1) 这个坑变成可重跑的回归,改 description 后立刻知道有没有破它;(2) `trigger_eval score` 的 **by family 分项**会告诉你**哪一族**在退化(整体 95% 可能藏着 translate_only 这一族从 100% 掉到 50%),而不是只看一个被平均稀释的总数;(3) 语料随真实使用**生长**——从"演示一次"变成"长期不回归"。

判据(和 Gotchas 同源):fixture 行来自**真实跑出来的误判**,不是凭空杜撰的用例。杜撰的近邻常常是假难度,过了也证明不了什么。

### 何时重构 Skill

```
信号 → 动作
Gotchas 表超过 15 条 → 分类合并，抽象为规则
SKILL.md 接近 500 行 → 拆 reference
同一条规则修改了 3 次 → 重新审视规则的设计而非打补丁
用户频繁在非预期场景触发 → 缩窄 description + 加 "Not for" 声明
```
