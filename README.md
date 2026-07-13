# YW SkillFoundry

帮你把 Agent Skill 写好、审清楚、改到真正有用。

AI 会不会按你想的方式做事，很大程度取决于 skill 写得怎么样。YW SkillFoundry 本身也是一个 skill：告诉你什么时候该做 skill，怎么写触发更准、指令更贴需求，以及怎么检查它是不是在糊弄你。

适合这些场景：

- 从零写一个新 skill，准备拿去用
- 现有 skill 效果不好，想定位问题并优化
- 合并前 / 发布前，给 skill 做一轮审查
- 把一段好用的对话，提炼成可复用的 skill

不适合：写业务代码、搭多智能体运行时、补模型本身做不到的能力。那些不是改 `SKILL.md` 能解决的。

## 它到底解决什么

很多人会写一堆规则，然后说「这个 skill 应该挺好」。真正难的是另一件事：它会不会被触发、触发后会不会按契约做事、相对不带 skill 的基线有没有更好。

YW SkillFoundry 把这件事拆开：

1. **写**：Scaffold 先做出能试用的版本；要上线再走 Production
2. **审**：按结构、触发、契约、证据边界打分，不靠自我感觉
3. **改**：效果不好时先诊断，再定点改，不盲目堆规则
4. **验**：用可跑脚本和可复查的 fixture，而不是口头保证

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

## Scaffold 和 Production

- **Scaffold**：默认先做这个。结构完整、能触发、能按契约输出，适合标成「试用」。
- **Production**：在 Scaffold 之上补可复查证据，比如对比基线、重复跑、盲评和回归。结构检查通过不等于效果已被证明。

## 环境要求

- Python 3.10+（只用标准库）
- Bash 3.2+
- macOS 或 Linux
- 支持 Agent Skills / `SKILL.md` 约定的宿主（Codex、Cursor、Claude Code 等）

WSL 一般能用，但目前没有进 CI。原生 Windows `PowerShell` / `cmd` 不支持这套 Bash 工具。

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

## 发布前自检

```bash
bash scripts/regress.sh
python3 scripts/privacy_lint.py
git diff --check
```

## 标准与研究引用

- [Agent Skills 规范](https://agentskills.io/specification.md)
- [Anthropic：用 Agent Skills 装备真实世界中的 agent](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Lost in the Middle (TACL 2024)](https://aclanthology.org/2024.tacl-1.9/)：长上下文位置效应，不是普适阈值阈值
- [Meincke et al. (PNAS 2026)](https://doi.org/10.1073/pnas.2535868123)：说服会影响模型顺从，这里只当间接参考，不当 skill 合规增益证明

## 安全与限制

工具会拦 symlink 覆盖、路径逃逸、畸形元数据和常见密钥形态，但不会替你沙箱执行 agent，也不会保证生成 skill 在所有环境都安全。用之前先自己看一遍。漏洞报告见 `SECURITY.md`，公开内容政策见 `PRIVACY.md`。

## 参与贡献

见 `CONTRIBUTING.md`。改触发或行为时，请附上最小、可公开的 fixture 或 bite test；不要提交原始 provider/session ID 或私有快照。

## License

MIT © 2026 yuwen-cool
