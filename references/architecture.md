# Skill 信息架构

## 目录

- [核心问题：为什么需要架构](#核心问题为什么需要架构)
- [三层 Progressive Disclosure](#三层-progressive-disclosure)
- [Token 预算](#token-预算)
- [文件引用策略](#文件引用策略)
- [种子模板模式](#种子模板模式)
- [脚本验证 vs AI 判断](#脚本验证-vs-ai-判断)
- [多 Skill 管理](#多-skill-管理)
- [架构决策清单](#架构决策清单)
- [Cross-Skill Ecosystem 注意事项](#cross-skill-ecosystem-注意事项)
- [跨 Skill 流水线：交接物契约](#跨-skill-流水线交接物契约)

---

## 核心问题：为什么需要架构

LLM 的注意力不是均匀分布的。

长上下文研究反复观察到：关键信息放在中间时，检索表现可能低于开头或结尾，但幅度取决于任务、模型和 context 长度。

实际影响必须在目标任务中验证：如果中间规则被漏掉，把关键约束前移/后移并重跑该 case。

这就是为什么需要架构——不是为了"整齐"，而是为了让每一条指令都落在 AI 注意力的有效区间内。

## 三层 Progressive Disclosure

```
Layer 0: Metadata（~100 tokens）
├── description → 路由决策：激活还是跳过
├── name → 人类识别
└── 此层对所有 skill 可见，每次对话都消耗

Layer 1: SKILL.md Body（< 5000 tokens）
├── Opening Statement → 设定 mental model
├── Workflow → 主执行流程（包含条件引用指令）
├── Hard Rules → 绝对约束
├── Output Format → 交付形态
├── Outcome Contract → 外部可检查时添加
├── Mode Router → 存在 2+ 执行路径时添加
├── Gotchas → 出现真实失败后添加
└── 仅在 skill 被激活时加载

Layer 2: References（按需加载，无上限）
├── 专题深度内容
├── 种子模板
├── 校验脚本
└── 仅在 workflow 特定步骤时加载
```

### 为什么是三层

- **Layer 0 对所有 session 可见**——所以必须极度精简。每多一个 token 都在消耗全局 context。
- **Layer 1 只在激活时加载**——可以放更详细的内容，但仍受 Lost in the Middle 影响。500 行是 review/split 触发线，不是物理极限；默认 validator 在 700 行以上失败。
- **Layer 2 按需加载**——减少无关常驻内容，并让当前步骤的 reference 更靠近使用时机；它只降低中部检索风险，不保证注意力，仍需用目标任务验证。

### 关键设计原则

**Layer 0 和 Layer 1 的界限是最重要的分割线。** Description 多一句 workflow 摘要 → AI 以为已经理解了 skill 全貌 → 跳过 Layer 1 正文。

这是通过 CSO 规则实测验证的：description 写了 "dispatches subagent per task with code review between tasks"，结果 AI 只执行了 1 次 review 而非规定的 2 次——它从 description 就"理解"了工作流，没有读正文中的完整规则。

## Token 预算

| 层 | 预算 | 原因 |
|---|---|---|
| Description | ≤1024 chars；目标通常 200–400 | 对所有 session 可见，成本最高 |
| SKILL.md body | ≤500 行；501–700 行需说明或拆分；>700 默认失败 | 兼顾注意力、可读性与复杂 skill 的必要空间 |
| 单个 Reference | 无硬限制，但 > 100 行加目录 | 按需加载，但仍需保持可读 |
| 全部 References 总计 | 考虑目标平台 context window | 只加载当前步骤需要的文件，不假设宿主有固定百分比预算 |

### 计算方法

粗略估算：1 行 ≈ 10 tokens（中文偏高，英文偏低）。SKILL.md 500 行 ≈ 5000 tokens。

如果 SKILL.md 超过 500 行，先说明哪些内容必须常驻；其余低频内容拆到条件 reference。不要为了数字压缩掉关键规则，也不要无理由继续增长。完整阈值见 `invariants.md`。

## 文件引用策略

5 种方式，效果差别巨大：

### 1. 无条件内联（❌ 避免）

```markdown
所有规则如下：
[300 行规则直接写在 SKILL.md 里]
```

问题：SKILL.md 膨胀，中间内容被忽略。

### 2. @ 强制加载（❌ 慎用）

```markdown
@references/all-rules.md
```

问题：无论是否需要都消耗 context。在 Cursor 中，@ 引用会把整个文件打包进 context。

### 3. 条件引用（✅ 推荐）

```markdown
当用户提供了截图时，读 `references/screenshot-analysis.md`。
当需要生成 API 相关内容时，读 `references/api-patterns.md`。
```

优势：最优 token 效率。只在需要时加载，且加载时内容在 context 末端（最高注意力区）。

### 4. 步骤内引用（✅ 推荐）

```markdown
### Step 3: 架构决策
读 `references/architecture.md`，回答以下问题：
1. ...
```

优势：引用和使用紧密绑定。AI 读完文件后立刻执行相关步骤，利用了刚加载的注意力优势。

### 5. 脚本执行（✅ 最佳，当适用时）

```markdown
### Step 6: 校验
运行 `scripts/validate.py --input output.html`，如果有错误，根据报告修复。
```

优势：零 AI 判断依赖。脚本输出是确定性的，且输出远小于完整规则文件。

### Reference Map 排序策略

SKILL.md 尾部的 Reference Map 不是目录——它是 AI 的**文件发现指南**。排序影响 AI 的加载行为：

```
NO（字母序）：
  background-systems.md   ← AI 可能在 Step 1 就加载，浪费 token
  category-cookbook.md
  components.md
  ...

OK（按大概率的访问时序）：
  platform-specs.md       ← Step 1 确定尺寸
  style-system.md         ← Step 3 选风格
  theme-presets.md        ← Step 3 选 palette
  layout-recipes.md       ← Step 4 选骨架
  components.md           ← Step 5 查规格
  background-systems.md   ← Step 5 Editorial 模式时
  qa-checklist.md         ← Step 7 用户要求时
```

reference 较多时，按访问时序排列：前半段放主路径，后半段按触发频率从高到低。

**规则**：始终需要的文件排最前，条件触发的按触发概率从高到低排最后。

### 引用深度规则

**一层发现，零必需依赖。**

```
✅ SKILL.md → references/style.md
✅ SKILL.md → references/qa.md
✅ references/style.md → "延伸阅读：color-details.md"（可选）
❌ references/style.md → "执行前必须读取 color-details.md"
```

问题不在于出现文件名，而在于 **A 依赖 B 才能执行**。这会制造隐式加载链，让正文无法知道实际上下文成本，也让宿主的局部读取行为丢掉必要内容。

解决方案：如果 A 确实需要 B，把必要规则直接写在 A（合并），或让 SKILL.md 在同一步骤直接加载 A 与 B（拍平）。可选的延伸阅读可以保留。完整规则见 `invariants.md`。

## 种子模板模式

当 skill 需要 AI 生成结构化内容时（HTML、配置文件、报告格式），提供一个接近完成的模板，比写一堆生成规则可靠得多。

### 为什么有效

直觉解释：如果每个开放决策都有独立出错机会，决策点越多，全部一致的概率越低。种子模板预先固定布局、结构与接口，让模型只处理真正需要变化的部分。这个方向需要用目标任务验证，不从假设概率推导实际提升幅度。

### 实例

例如，卡片生成可以提供完整 HTML 骨架，只让 AI 填标题、内容与主题变量；图表生成可以提供少量按场景路由的 SVG 骨架，只替换数据与标签。模板是否值得其 context 成本，仍由 run-compare 或业务指标决定。

### 种子模板设计规则

1. **模板必须能独立运行**——不缺少依赖、不需要额外构建步骤
2. **明确标记可修改区域**——用注释标记 `<!-- FILL: 标题 -->` 或 CSS 变量 `--primary-color`
3. **固定的部分 > 灵活的部分**——模板的价值在于减少决策点，如果什么都可改，不如没有模板
4. **一种风格一个模板**——不要一个模板里用参数切换多种风格

## 脚本验证 vs AI 判断

| 检查类型 | AI 判断 | 脚本判断 |
|---|---|---|
| HTML 语法有效性 | 容易漏掉边界错误 | 解析器可确定验证 |
| 图片尺寸是否正确 | 可能凭描述猜测 | 读取文件元数据可确定验证 |
| 文字是否溢出容器 | 静态阅读难判断 | 浏览器渲染检测更可靠 |
| 风格是否美观 | 适合基于 rubric 评审 | 无通用确定性脚本 |
| 代码逻辑是否正确 | 适合提出假设与风险 | 可靠性取决于测试覆盖率 |

规则：**如果一个规则可以被表达为确定性检查（布尔值 / 数值范围），就用脚本。** 把 AI 判断留给真正需要主观评估的场景。

### 脚本放置

```
skill-name/
├── SKILL.md
├── references/
│   └── ...
└── scripts/
    ├── validate.py     # 校验产出
    ├── build.py        # 构建流程
    └── stabilize.py    # 自动修复（如溢出修复器）
```

在 SKILL.md 的 workflow 中直接调用脚本，而不是让 AI 读取脚本内容后"理解并执行"。

## 多 Skill 管理

当 skill 数量、描述预算或触发重叠开始造成维护成本时，启动生态治理审计；数量只是一项信号，不设通用硬阈值：

### Registry 模式

用 `registry/skills.json` 作为唯一数据来源：

```json
{
  "skills": [
    {
      "id": "yw-skill-foundry",
      "version": "2.0.0",
      "status": "active",
      "triggers": ["写 skill", "create skill"],
      "dependencies": []
    }
  ]
}
```

CI 脚本从 registry 自动生成 README 中的 skill 列表——消除 README 和实际文件不同步的问题。

### CLAUDE.md / AGENTS.md 的 Token 预算

全局指令文件对每个 session 都消耗 context。规则：
- 只保留每个 session 都需要的共享纪律；用实际 context 成本决定长度
- 具体指令放在 skill 里，全局文件只放 skill 间共享的纪律（编码风格、提交规范、语言偏好）
- 不在全局文件里 @ 引用大文件

## Bootstrap Injection: 确保关键行为永远生效

用 session-start hook 实现。

### 问题

有些行为需要在**每个 session**中生效，不依赖用户是否触发了特定 skill。比如"所有操作前先检查 git status"、"永远先读 skill 再回答"。

### 模式

用 `hooks/session-start` 脚本在每次 session 启动时注入一个核心 skill 的内容：

```bash
core_skill_content=$(cat "${PLUGIN_ROOT}/skills/<core-skill>/SKILL.md")
session_context="<EXTREMELY_IMPORTANT>\n${core_skill_content}\n</EXTREMELY_IMPORTANT>"
```

这确保了无论用户说什么，AI 都先读到了核心行为指令。

### 适用场景

- 跨 skill 共享的安全规则
- "永远读 skill 再回答"这类元规则
- 项目级别的全局约束

### 替代方案

如果平台不支持 hooks，把真正每个 session 都需要的核心行为放在 AGENTS.md / CLAUDE.md，并用实际 context 成本控制长度。

## 平台适配

参考 agentskills.io 的 compatibility 字段。

### 问题

同一个 skill 在不同平台（Cursor、Claude Code、OpenAI Codex）可能需要不同的行为：
- 可用工具不同（Cursor 有 browser MCP，Claude Code 没有）
- 文件系统路径不同
- 目标模型的能力与工具支持不同

### 模式

在 SKILL.md 中用条件分支处理平台差异：

```markdown
## 平台适配
- **Cursor**: 使用 Read 工具读取文件
- **Claude Code**: 使用 cat 命令读取文件
- **通用**: 如果不确定平台，使用最保守的方案
```

agentskills.io 的 compatibility 字段声明支持的平台：

```yaml
compatibility: "Requires cursor or claude-code. Uses Read tool and Shell."
```

### 设计原则

写 skill 时默认针对最广泛的平台兼容性。平台特定功能作为增强，不作为必需。

## Sub-agent 编排

两种典型模式：多 inspector 分工，和 pipeline 流水线。

### 问题

复杂 skill 可能需要多个视角或多个阶段的工作。单一 AI 实例在长 context 中容易丢失早期信息。

### 模式 1：分工 Inspector

```
主 agent → 分派任务
├── Inspector A: 检查 context 漂移
├── Inspector B: 检查可维护性
└── Inspector C: 检查安全性
主 agent ← 汇总结果
```

每个 inspector 有独立的 context，不互相干扰。

### 模式 2：Pipeline

```
Stage 1: 分析 → Stage 2: 生成 → Stage 3: 验证 → Stage 4: 修复
```

每个 stage 可以是独立的 sub-agent，stage 间传递结构化的中间结果。

### 在 SKILL.md 中的指导

```markdown
当任务涉及 3 个以上独立维度时，考虑使用 sub-agent：
1. 为每个 sub-agent 写明确的 prompt（包含所有必需 context）
2. 定义 sub-agent 的输出格式
3. 主 agent 汇总和仲裁 sub-agent 的结果
```

## 架构决策清单

写 skill 时回答以下问题。如果答案触发了 → 执行对应动作：

| 问题 | 触发条件 | 动作 |
|---|---|---|
| SKILL.md 估计多少行？ | > 500 行 | 说明常驻理由并拆出低频内容；>700 默认校验失败 |
| 有哪些内容只在特定场景需要？ | 非主路径、低频或高成本内容 | 拆到条件加载的 reference |
| 有规则可以被确定性检查吗？ | 有布尔/数值规则 | 写 scripts/ |
| 需要 AI 生成结构化内容吗？ | HTML / 配置 / 报告 | 提供种子模板 |
| 有多种执行模式吗？ | 有 2+ 种不同的用户意图 | 加 Mode Router |
| 需要跨 skill 共享规则吗？ | 多个 skill 重复且每个 session 都需要 | 评估后提取到 AGENTS.md |
| Skill 生态出现预算、冲突或漂移了吗？ | 审计发现问题 | 采用 Registry 或自动一致性检查 |
| Skill 之间有委托关系吗？ | A 调用 B 的能力 | 定义 Skill Delegation Protocol |

## Cross-Skill Ecosystem 注意事项

当描述预算、路由冲突或跨 skill 维护开始显著时，需要考虑**生态治理**：

- **Config 共享**：一组同系 skill 可以共享 `EXTEND.md` 里的设置（如 `preferred_image_backend`），避免每个 skill 单独问一遍。统一的偏好路径（XDG → home → project）减少用户配置负担。
- **Skill 委托**：一个卡片 skill 需要截图能力但不自己实现——它调用 Playwright；一个配图 skill 需要图像生成但不绑定后端——它通过 backend resolution protocol 委托。设计 skill 时问"这个能力是我的核心还是可以委托？"
- **学习同步**：生成 → 用户反馈 → 更新 `EXTEND.md` 的 `style_learnings`。这个模式只在**用户确认的反馈**上更新，不从推断中学习。
- **避免隐式耦合**：一个借用了另一套风格系统的 skill 应明确声明"本 skill 自包含——它借用了那套视觉原则，但绝不修改原 skill"。

## 跨 Skill 流水线：交接物契约

当多个 skill 串成流水线（A 的产出是 B 的输入），最脆弱的一环是交接。可采用三层交接设计：

1. **固定文件名的交接包**。上游 skill 的最后一步是把产物整理成一组**命名稳定的文件**（`source_cut.mp4` + `subtitles.srt` + 可选 `assets/`），下游按这些名字读取。文件名是契约，避免下游猜“哪个输出最新”。
2. **给机器消费者的产物契约单独成文**。当产物要被脚本/渲染器消费，契约精确到接口级（根节点、消息协议、渲染参数），并由 SKILL.md 只在实现阶段加载：**契约按消费时机进入 context**。
3. **文件头微契约**。每个文件头部用三行注释声明 `input / output / pos`（输入、输出、在流水线中的位置），AI 和人都能在不读全文的情况下判断"这个文件与当前阶段是否相关"。

两个常见反面教训：

- **注释式同步提醒挡不住漂移**。跨文件一致性（清单 ↔ 目录、Reference Map ↔ 实际文件）用脚本检查；注释只说明意图。
- **正文不要写死作者机器的绝对路径**。分发型 skill 的脚本调用相对安装目录解析，不能假设安装位置。
