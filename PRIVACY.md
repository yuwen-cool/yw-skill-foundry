# 隐私与公开内容政策

YW SkillFoundry 不收集遥测。本地脚本不会把源码、证据、标识符或使用数据发到外部服务。

## 不要公开这些

不要提交、打包、附件，或粘贴到公开材料里：

- 个人邮箱、本机家目录绝对路径
- 密钥、token、私钥、`.env*` 文件
- 日志、`HANDOFF.md`、个人笔记、memory 目录、本地数据库
- 聊天 / transcript / 对话导出
- 原始 provider、session、run、judge、agent 标识
- 私有 skill 快照或私有工作区
- 宿主专属 agent 状态、缓存、编辑器状态

平台公开元数据不算个人联系方式：GitHub 的 `noreply` / `support`、带数字前缀的 `users.noreply.github.com`（含 Dependabot），以及公开的 Cursor agent 共著地址。维护者提交和 annotated tag 请用 GitHub noreply，不要用个人邮箱。

发布前跑：`python3 scripts/privacy_lint.py`。在 Git 仓库里，默认会扫当前公开文件，以及可达的 commit / tag 元数据和 blob。`--working-tree-only` 只给刻意清理历史时用；正式发布必须过默认历史扫描。

## 公开证据怎么写

公开证据必须是为公开准备的。用发布内本地标签，比如 `run-a1`、`judge-b1`；用合成 fixture，不要带真实账号或 provider 标识。模型与宿主信息只写到能界定主张边界为止。

仓库可以附脱敏后的触发 fixture 和汇总结果。不要为了「看起来更完整」去公开原始 transcript、个人日志、私有快照或导出的 provider 记录。

## 贡献者流程

实验性证据先放在仓库外，或忽略目录里。拷进 `evals/` 之前：

1. 把外部标识换成发布内本地标签
2. 只保留任务、fixture、结果和主张边界所需的最小材料
3. 确认每份输入都是刻意为公开准备的
4. 跑 `python3 scripts/privacy_lint.py --working-tree-only`
5. 发布前再跑默认历史扫描，并扫描构建好的归档

如果问题出现在可达历史里，只删工作区文件不够。先重写公开历史，再跑默认扫描。
