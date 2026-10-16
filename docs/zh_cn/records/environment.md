# 开发环境验收记录

本文件记录本地开发环境的验收结论；搭建方式、配置位置和检查命令见
[开发环境](../develop/development_environment.md)。

## 2026-09-12 本地验收记录

- Python 3.12.10 x64，`maafw` Python 包和实际加载的原生库均为 5.13.0。
- `pip check` 通过；Agent 在独立进程中导入并注册成功。
- Maa Support 插件 509.0.29，保存的框架选择为 5.13.0；已确认版本设置，尚未确认故障发生时的运行实例。
- 三个 OCR 必需文件存在且非空；未进行设备 OCR 或模型来源一致性验证。
- maa-tools、Pipeline/Interface Schema、体力配置同步、交互稳定性检查通过。
- 原插件 Bug 尚未复现，也没有执行任何购买、体力消耗或游戏任务。后续须在重启插件运行实例后记录具体失败操作、节点和报错，区分启动环境问题与页面流程问题。
- 本轮只进行本地检查，没有上传日志、截图、配置或游戏数据。

## 2026-10-12 环境更新记录

- 已通过 uv 创建 `.venv312`（Python 3.12.14），安装 `maafw==5.14.3` 和 pip；实际加载 native runtime 为 v5.14.3，依赖一致性检查与独立 Agent 导入注册均通过。
- 已运行 `npm ci`，Node.js 24.21.0、npm 11.19.0；依赖审计报告仍有 9 项传递依赖告警，未执行自动修复。
- 已核对官方稳定版本：MaaFramework v5.14.3、MFAAvalonia v2.16.2；CI 与 Maa tools 配置已同步。尚未启动 MFAAvalonia 或执行设备任务，升级兼容性仍需实机回归。
- Codex 全局 MCP 配置已启用 `maa-mcp==1.2.3`，启动使用 uvx 绝对路径、Python 3.12 和 `maafw==5.14.3`，启动超时 60 秒、工具超时 120 秒。修改前配置已在 Codex 本地临时目录备份；当前会话工具目录尚未加载专用函数，需重新加载后在聊天中确认。
- 已生成项目上下文缓存 `basic_info.md`（被 Git 忽略），包含 10 个任务入口、14 个 Pipeline 文件、436 个节点和 6 个模板图片文件；生成器报告未解析引用为 0。
- 已完成 MaaMCP 1.2.3 的 stdio `initialize` 与 `tools/list` 握手，返回 24 个工具；本轮未连接设备或运行游戏任务。探测进程已结束。
- 资源加载 smoke test 通过；`maa-tools check`、Schema、体力配置同步、交互稳定性检查、Prettier 均通过。登录流程新增的 4 个 300ms 稳定等待尚未做设备回归。
- OCR 模型由 MaaCommonAssets `dabcd4681ac990dc4361de26416d986abd80e4aa` 恢复到被 Git 忽略的本地目录，文件存在且非空；该目录不是当前提交中的 gitlink，来源摘要保留在本地 `deps/maa-common-assets-source.json`。
- `maafw-cli==0.1.6` 版本检查通过；其 `pipeline validate assets/resource/pipeline` 返回 `valid:false`、`Resource initialization failed`。这项独立 CLI 验收未通过，项目 Python runtime 的完整 `assets/resource` 加载通过；不可据此认定 CLI 能替代当前项目的多文件/Agent 测试。
- MFAAvalonia v2.16.2 官方源码使用 C# binding 5.10.0、内置 runtime 5.12.3；本项目打包会替换内置 native runtime。已核对 release 与绑定配置，但尚未完成前端与 5.14.3 的实际启动/Agent 连接验证，不能认定升级组合已通过端到端兼容性验收。

## 2026-10-14 环境整理与本地验收

- 沿用 `.venv312`，解释器 Python 3.12.14，Python maafw 包和实际加载的 native runtime 均为 5.14.3。新增环境检查通过，requirements、maa-tools、构建版本与 Python ABI 一致，`pip check` 通过。
- Node.js 仍为本机已有的 24.21.0、npm 11.19.0；CI 使用 Node.js 22，本轮未更换全局 Node，也未处理先前记录的依赖审计告警。
- 六份 Schema 已由固定版本同步脚本重新下载，来源为官方 MaaFramework v5.14.3。资源与 Interface Schema、maa-tools、体力生成配置同步、交互稳定性和 Prettier 检查均通过。
- `assets/resource` 完整资源加载通过；Agent 在另一个独立进程导入注册成功。这两项不操作设备，不能代替前端中的 Agent 连接与任务验收。
- 本机实际 OCR 文件与新登记的来源修订、大小及 SHA256 一致。恢复脚本不再只检查目录存在：完整目录可脱离子模块使用，缺失文件可补齐，不匹配文件会保留并报错。5 项恢复异常测试及原有商城、调教 11 项测试全部通过。
- 已从空目录 `tmp/environment-clean/ocr` 联网恢复三个固定修订的模型文件，并通过只读检查；下载约 31 MB、耗时约 11 分钟，本机网络速度较慢。文件仅保存在被忽略的本地目录，不依赖先前恢复的模型或子模块。
- CI 增加版本核对、固定 OCR 恢复、完整资源加载、Agent 导入、生成配置同步及测试；Schema 同步改为 requirements 对应版本的全部六份文件，下载或校验失败时停止。本轮仅修改本地 workflow，未触发远程构建或发布。
- 前序 MaaMCP 设备回归已覆盖登录冷启动、好友体力、奖励领取、炼金交付、派遣忙碌、调教、招募与商城等实际路径，详情见各任务记录；此前“未执行设备任务”是 10 月 12 日的历史结论。自动通关已取消 Interface 注册，不进入本轮验收。
- 仍待验证：包含本次环境改动的 CI 全平台打包、MFAAvalonia 2.16.2 包内启动、Interface 选项持久化、随包 Agent 连接与连续任务。独立 CLI 的资源初始化失败尚未复测或宣告修复。前端验收方式已写入开发环境文档。
