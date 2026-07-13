# Description 设计与触发优化

## 目录

- [CSO: Claude Search Optimization](#cso-claude-search-optimization)
- [Description 写法规则](#description-写法规则)
- [触发词设计](#触发词设计)
- [触发测试方法](#触发测试方法)
- [平台特定字段](#平台特定字段)
- [NO/OK 对照表](#nook-对照表)

---

## CSO: Claude Search Optimization

Description 是 skill 的路由层——AI 读它来决定是否激活 skill。CSO 的核心发现：

**Description = 干什么 + 什么时候用，绝不写怎么做。**

Agent Skills 规范要求 description 同时说明这个 skill *做什么*（"what"）和 *何时用*（"when"）。缺 "what" 会让能力边界不清；缺 "when" 会让触发条件不清。不要把第三件事——**"how"（workflow 步骤）**——塞进 description：流程摘要可能让宿主或模型只依据元数据行动而不读取完整正文。是否发生必须用目标宿主的路由与执行评测确认。

原理：AI 的行为模式是"已有足够信息时不主动寻找更多"。如果 description 让 AI 觉得自己已经理解了执行方式，它就不会读正文。"what + when" 给的是路由信息，"how" 给的是（残缺的）执行信息——前者引导它进门，后者让它以为不用进门。

如果路由评测显示触发不足，可以在 description 中补充真实用户的同义词和口语说法，再用 "Not for X" 排除句收紧边界；如果出现过度触发，则反向收窄。不要预设哪一类失败更常见，以实际 fixture 分项为准。

## Description 写法规则

### 1. What + When，用 "Use when..." 组织

一句话说清能力（what），再接具体的用户行为或场景（when）。

```
NO: "A comprehensive skill for optimizing React components with
     memoization, code splitting, and lazy loading strategies."

OK: "Optimizes React rendering performance. Use when React components
     render slowly, the user asks to optimize performance, or the
     profiler shows unnecessary re-renders."
```

第一个把技术手段（memoization、code splitting——这是 how）塞进了 description，且没有触发场景——AI 读完觉得自己会了，还不知道何时用。第二个是能力 + 触发条件——AI 读完知道何时激活，但必须读正文才知道怎么做。

### 2. 第三人称

Description 用第三人称描述用户行为（"the user asks..."），不用第一人称（"I help..."）或第二人称（"You should..."）。

```
NO: "I help you write better tests."
NO: "You should use this when writing tests."
OK: "Use when the user asks to write tests, improve test coverage,
     or diagnose flaky tests."
```

### 3. 包含具体关键词

AI 的 skill 匹配依赖关键词。包含：
- **用户可能说的自然语言短语**（中英文都要）
- **错误信息关键词**（"ENOENT"、"segfault"、"OOM"）
- **工具名/技术名**（"React"、"Playwright"、"WeChat"）
- **近义词和变体**（"PPT" / "slides" / "幻灯片" / "演示文稿"）

```
NO: "Use when creating presentations."

OK: "Use when the user asks to create slides, make a presentation,
     generate a deck, PPT, 做 PPT, 幻灯片, or 演示文稿."
```

### 4. ≤1024 字符

Description 是 Layer 0，对所有 session 可见。太长 = 浪费全局 context。

一个优秀的 description 通常在 200-400 字符之间。

### 5. 禁止 workflow 步骤

```
NO: "Analyzes code, identifies patterns, generates refactoring plan,
     applies changes, and runs tests."

OK: "Use when the user wants to refactor code, reduce duplication,
     or simplify complex functions."
```

### 6. 可选：负面触发（不该触发的场景）

如果你的 skill 容易和其他 skill 混淆，用 "Not for..." 明确边界：

```
OK: "Use when the user asks to write tests. Not for debugging
     existing test failures (use a dedicated debugging skill instead)."
```

## 触发词设计

### 语言 × 精度覆盖

```
              精确触发词              模糊触发词
中文    "写 skill"、"创建 skill"    "怎么调教 AI"、"提示词设计"
英文    "create skill"、"write SKILL.md"   "prompt engineering"、"instruction design"
```

先从真实请求确定语言分布。用户同时使用中英文时覆盖四个象限；用户群明确单语时，只覆盖该语言的精确与模糊表达，不为“看起来全面”硬塞翻译。

### 错误信息触发

对于诊断型 skill，把常见错误信息作为触发词：

```
"Use when the user encounters 'ENOENT: no such file or directory',
 'MODULE_NOT_FOUND', 'Permission denied', or file system related errors."
```

### 症状触发

用户不一定知道原因，但会描述症状：

```
"Use when the user says the page is 'ugly', 'cluttered',
 'doesn't look right', 'looks AI-generated', or 'too generic'."
```

## 触发测试方法

最低标准：3 命中 + 3 未命中。

### 命中测试（应触发）

在新 session 中（无历史 context），输入以下 prompt，检查 AI 是否选择了你的 skill：

1. **精确触发**："帮我写一个新的 skill"
2. **模糊触发**："这个 AI 的效果不太好，有什么办法优化？"
3. **英文触发**："How do I create an agent skill?"

### 未命中测试（不应触发）

1. **相邻场景**："帮我写一篇文章" → 不应触发 yw-skill-foundry
2. **关键词重叠**："help me write better code" → 不应触发（虽然有 "write"）
3. **不相关场景**："今天天气怎么样"

### 诊断

- 应触发但没触发 → description 太窄，缺少关键词
- 不该触发但触发了 → description 太宽，或关键词与其他 skill 重叠
- 触发了但 AI 没读正文 → description 包含了 workflow 信息，AI 认为已经够了

### 路由不过时:生成候选 → 各自打分 → 按 holdout 选

`trigger_eval score` 只是评判半截。当 `score` FAIL(或 UNDER/OVER-TRIGGER 反复出现),不要凭手感临场改一版就完事——**那是 n=1 的赌博**。改成一个结构化的小循环(agent 执行,无需自动 LLM 子进程,守 stdlib-only):

1. **生成 2-3 个候选 description**,每个针对一类失败下不同的赌注:
   - 一个**加宽**(补上 UNDER-TRIGGER 缺的同义词/口语/错误串关键词);
   - 一个**收窄**(给 OVER-TRIGGER 加 `Not for X (use Y instead)` 排除句);
   - 一个**换框架**(换一组触发词的措辞,而不是增删)。
2. 对每个候选,在 `train` 上跑 `worksheet → 判定 → score` 调,再在**未见过的 `holdout`** 上验。
3. **按 holdout 分数选赢家,不按 train 选**——train 是你调过的,在它上面赢证明不了泛化(这也是 holdout 字段存在的全部理由)。holdout 并列时,选更短、排除句更明确的那个。

为什么要多候选而不是改一版:单改一版你只知道"它比上一版好/坏",不知道"加宽 vs 收窄哪个方向对"。三个候选同台对比,直接暴露失败的方向,而不是症状。

## 平台特定字段

开放标准（agentskills.io）只要求 `name` 和 `description`；其余字段按平台分层。**写错平台字段不报错——宿主会静默忽略它**，所以格式必须对着规范写，不能凭印象。

### 开放标准可选字段（agentskills.io specification）

```yaml
---
name: my-skill
description: "Optimizes X. Use when..."
license: MIT
compatibility: "Requires git and network access"   # ≤500 字符的自由文本，不是嵌套对象
allowed-tools: Read Write Shell                     # 空格分隔的字符串（实验性字段）
metadata:
  author: someone
---
```

- `compatibility`: **一段 ≤500 字符的文本**，描述环境要求（所需工具、网络等）。大多数 skill 不需要它。不是 `platforms:/models:` 嵌套对象——那种写法会被忽略。
- `allowed-tools`: **空格分隔的字符串**（规范标记为实验性），限制 skill 激活期间可用的工具。不是 YAML 列表。
- `metadata`: 任意键值对，宿主各自解释。

### Cursor 扩展字段

```yaml
---
name: my-skill
description: "Use when..."
paths: ["src/**/*.tsx"]
disable-model-invocation: true
---
```

- `paths`: 只在会话涉及匹配路径的文件时才让 skill 参与路由。适用于框架/目录特定的 skill。
- `disable-model-invocation`: **阻止模型自动触发这个 skill**——skill 只能由用户显式调用（如 `/name`）。适用于有副作用、只该手动启动的流程。（它管的是"谁能激活 skill"，与调用什么模型无关。）

### Claude Code 扩展字段

- `context: fork` + `agent`: 让 skill 在隔离的子代理中执行。
- 预算行为由宿主决定，可能随模型、上下文窗口和已加载技能集合变化。不要把某一宿主当前的预算或截断策略当成跨平台常量；description 越长，通常越需要关注集合级上下文成本。

规范原文以 agentskills.io/specification 与各宿主文档为准——平台字段可能随版本变化，发布前应核对目标宿主，而不是凭记忆填写。

## NO/OK 对照表

| 维度 | ❌ NO | ✅ OK |
|---|---|---|
| 开头 | "A comprehensive tool for..." | "Use when the user asks to..." |
| 内容 | "Analyzes, plans, executes, and validates" | "Use when debugging, fixing errors, or investigating regressions" |
| 语气 | "I can help with..." | "Use when..." |
| 长度 | 2000 字符的完整功能介绍 | 200-400 字符的触发条件 |
| 关键词 | 只有英文 | 中英文 + 错误信息 + 症状描述 |
| 边界 | 无 | "Not for X (use Y instead)" |
| 人称 | "I help you..." / "You should..." | "Use when the user..." |
| Workflow | "Step 1: analyze. Step 2: plan." | 不包含任何步骤信息 |
