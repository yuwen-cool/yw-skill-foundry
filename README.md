# YW SkillFoundry

**把 Agent Skill 从「写了但不好使」，变成「写完就能用、经得起检查」。**

大多数 skill 效果不好，不是因为道理没写对，而是因为：该触发的时候没触发，触发了也没按预期执行，或者写的人自己也说不清「这次真的变好了」还是「感觉好像变好了」。YW SkillFoundry 就是解决这件事的 skill——装上它以后，直接跟 AI 说「帮我写一个 skill」「看看这个 skill 写得怎么样」「这个 skill 效果不好，帮我改一下」，剩下的交给它。

## 能帮你做到什么

| 场景 | 你会得到 |
|---|---|
| **从零写一个新 skill** | 一版结构完整、能触发、能按约定输出的初版，而不是一堆规则堆在一起就交差 |
| **现有 skill 效果不好** | 定位到具体是触发不准、指令太模糊、还是缺校验，给出针对性的改法，而不是整篇重写 |
| **合并 / 发布前想把关** | 按 7 个维度打分并指出具体哪一行有问题，而不是一句「看起来还行」 |
| **一次好对话想变成能复用的能力** | 抽出这次对话里真正起作用的指令，剔除项目相关的细节，产出一个别人也能用的 skill |

不做什么：写业务代码、搭多智能体运行时、补模型本身做不到的能力。那些问题不是改一份 `SKILL.md` 能解决的，硬改只会让文档变长、效果不变。

## 举个例子，看得更直接

同一个「优化 React 组件」的 skill，两种写法，AI 的反应完全不同：

```
❌ "A comprehensive skill for optimizing React components with
    memoization, code splitting, and lazy loading strategies."
```

这句话把「怎么做」提前塞进了触发描述里。AI 读完会觉得自己已经懂了，很可能直接按记忆里的套路处理，根本不会打开正文去看你写的具体方法论。

```
✅ "Optimizes React rendering performance. Use when React components
    render slowly, the user asks to optimize performance, or the
    profiler shows unnecessary re-renders."
```

这句话只说「做什么 + 什么时候用」，把「怎么做」留给正文——AI 知道该在什么场景激活它，但必须读完整套方法才能动手，你写在正文里的经验才真正派上用场。

YW SkillFoundry 不只是告诉你这个道理，而是会强制你把改完的 description 拿去跑一遍触发测试（`trigger_eval.py`），用真实案例验证它到底触不触发，而不是「读起来顺就行」。

## 为什么可信，不是空口号

很多写法教程停在「怎么排版一个 SKILL.md」。这里往前多走了几步，把提示词工程里容易口头化的部分，尽量变成可检查、可复跑的东西：

- **触发不是拍脑袋写关键词**。Description 按「做什么 + 什么时候用」拆开写，中英文口语词、错误信息、症状词分层覆盖，再用 3 正例 + 3 反例（含 holdout）跑评测打分——写完就知道触不触发，不用等上线后才发现。
- **约束是分级的，不是一路 MUST/NEVER**。只有不可逆、安全相关的规则才用强制词；普通规则用「怎么做 + 为什么」，避免规则堆多了反而互相稀释。
- **专门堵 AI 会用来"绕过规则"的说法**。提前列出 AI 常见的自我开脱句式（比如"这个改动太小不用测"）配预设回应；用一句话封死"我理解精神不拘字面"这类借口；等待确认期该做什么、不能做什么写成穷举清单，而不是笼统说"等用户确认"。
- **产出是否达标，能跑脚本判定，不靠自我感觉**。契约检查、结构检查、证据校验都是确定性脚本；效果类主张要求持久化的对比证据（重复跑、盲评、位置互换），不允许自我担保。
- **检查工具自己也被测过**。不只测「好输入能过」，还专门测「坏输入必须被拒」，避免校验脚本本身形同虚设。

每条规则背后都有对应的检查或案例，不是一句无法验证的断言。目标很直接——让不是提示词工程专家的人，也能按这套流程写出经得起检查的 skill。

## 安装

把仓库放到宿主的 skills 目录，目录名必须是 `yw-skill-foundry`：

```bash
# Codex
git clone https://github.com/yuwen-cool/yw-skill-foundry.git ~/.codex/skills/yw-skill-foundry

# Cursor
git clone https://github.com/yuwen-cool/yw-skill-foundry.git ~/.cursor/skills/yw-skill-foundry

# Claude Code（项目级）
git clone https://github.com/yuwen-cool/yw-skill-foundry.git .claude/skills/yw-skill-foundry
```

装好后，直接跟 AI 说「帮我写一个 skill」或「看看这个 skill 写得怎么样」即可。

## 先跑通一次

比如：

> 帮我写一个上线前审查数据库 migration 的 Agent Skill。

写完后可以本地检查：

```bash
python3 scripts/trigger_eval.py lint --skill path/to/new-skill
bash scripts/validate-skill.sh path/to/new-skill
python3 scripts/citation_lint.py --skill path/to/new-skill
```

触发测试建议先写案例，再改正文。可从 `evals/trigger_cases.example.jsonl` 起步。

## Scaffold 和 Production：先能用，再谈证明

- **Scaffold**：默认先做这个。结构完整、能触发、能按契约输出，适合标成「试用」。
- **Production**：在 Scaffold 之上补可复查证据，比如对比基线、重复跑、盲评和回归。结构检查通过不等于效果已被证明。

## 工具一览

| 工具 | 做什么 |
|---|---|
| `scripts/validate-skill.sh` | 检查结构、元数据、引用和常见风险 |
| `scripts/trigger_eval.py` | 触发面 lint、盲测工作表、打分 |
| `scripts/contract_eval.py` | 检查产出是否满足约定 |
| `scripts/evidence.py` | 创建和校验 run-compare 证据包 |
| `scripts/skill_library_audit.py` | 检查一组 skill 的触发冲突 |
| `scripts/citation_lint.py` | 扫描正文里不该出现的私有引用 |
| `scripts/privacy_lint.py` | 扫描源码、历史和发布包里的隐私风险 |
| `scripts/regress.sh` | 一键跑完整本地回归 |

新产出的协议 ID 使用 `yw-skill-foundry.*`；旧的 `skill-foundry.*` / `skill-craft.*` 仍可校验。细节见 `references/evidence-schema.md`。

## 环境要求

- Python 3.10+（只用标准库）
- Bash 3.2+
- macOS 或 Linux
- 支持 Agent Skills / `SKILL.md` 约定的宿主（Codex、Cursor、Claude Code 等）

WSL 一般能用，但目前没有进 CI。原生 Windows `PowerShell` / `cmd` 不支持这套 Bash 工具。

## 仓库里有什么

```text
SKILL.md        主 skill（给 AI 读的工作流）
references/     按需加载的方法论与协议
scripts/        校验与证据工具
templates/      Scaffold / Production 模板
examples/       可对照的写法示例
evals/          脱敏后的触发测试材料
```

发布归档只打进终端用户需要的文件，不含 `.github`、私有日志、机器路径和原始会话 ID。政策见 `PRIVACY.md`。

## 证据边界（说清楚，避免误读）

仓库里附带一份脱敏的触发优化记录：`evals/routing-2026-07-13-v3/`（14 个案例）。

它只说明那一组案例上的触发结果，不证明「用了就一定更好」，也不等于 2.0.0 已有 Production 级效果证据。原始 run/judge ID、对话 transcript、个人日志和私有快照都不会公开。

## 你自己的迭代记录不会被误传

装好之后你大概会想记点东西——什么场景失败了、改了哪一版。直接在这个 skill 目录里建 `log.md` 就行，不用额外配置：仓库自带的 `.gitignore` 已经排除了 `log.md`、`HANDOFF.md`、`private/`、`notes/`、`memory/`、`workspaces/`。即使你把这份 skill 也纳入自己的 Git 仓库并推送，这些文件也不会被带上去。想确认，跑一遍 `python3 scripts/privacy_lint.py`。

## 发布前自检

```bash
bash scripts/regress.sh
python3 scripts/privacy_lint.py
git diff --check
```

## 标准与研究引用

- [Agent Skills 规范](https://agentskills.io/specification.md)
- [Anthropic：用 Agent Skills 装备真实世界中的 agent](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Lost in the Middle (TACL 2024)](https://aclanthology.org/2024.tacl-1.9/)：长上下文位置效应，不是普适阈值
- [Meincke et al. (PNAS 2026)](https://doi.org/10.1073/pnas.2535868123)：说服会影响模型顺从，这里只当间接参考，不当 skill 合规增益证明

## 安全与限制

工具会拦 symlink 覆盖、路径逃逸、畸形元数据和常见密钥形态，但不会替你沙箱执行 agent，也不会保证生成 skill 在所有环境都安全。用之前先自己看一遍。漏洞报告见 `SECURITY.md`，公开内容政策见 `PRIVACY.md`。

## 参与贡献

见 `CONTRIBUTING.md`。改触发或行为时，请附上最小、可公开的 fixture 或 bite test；不要提交原始 provider/session ID 或私有快照。

## License

MIT © 2026 yuwen-cool
