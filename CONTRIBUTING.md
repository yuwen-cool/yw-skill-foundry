# 参与贡献

谢谢你愿意改进 YW SkillFoundry。

这个项目的目标很直接：让人把 skill 写得更贴需求、更容易触发、也更容易验证效果。贡献时优先想用户会怎么用，而不是只堆内部抽象。

## 提交前

1. 先搜一下现有 issue / PR，避免重复
2. 变更尽量聚焦，说清楚对用户有什么用
3. 只提交可公开的 fixture；不要提交原始 provider/session ID、transcript、个人日志、机器路径或私有快照
4. 不要引入第三方 Python 依赖

## 开发环境

- Python 3.10+
- Bash 3.2+
- macOS 或 Linux；WSL 通常可用，但尚未纳入 CI

## 本地验证

```bash
bash scripts/regress.sh
python3 scripts/privacy_lint.py
git diff --check
```

- 改解析器、写文件、路径处理、证据校验：在 `scripts/self-check.sh` 补正向和咬测
- 改触发元数据：同时补 train / holdout 案例
- 声称内容效果变好：补可公开的对比证据，并写清边界

## Pull Request

请写明：

- 改了什么，为什么改
- 考虑过哪些风险
- 跑过哪些验证
- 有没有触及隐私 / 证据边界

更完整的社区约定见 `CODE_OF_CONDUCT.md` 和 `PRIVACY.md`。
