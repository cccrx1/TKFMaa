# Maa 技能与工具流程

本项目使用 `maa-*` 技能组。技能提供工作规范，MCP/CLI 提供运行能力，项目 Pipeline 和 Interface 是实际行为的来源。技能安装成功不代表 MCP 已连接，也不代表游戏流程已验证。

## 按任务选择技能

| 工作                                     | 首选技能                     | 产物或边界                                    |
| ---------------------------------------- | ---------------------------- | --------------------------------------------- |
| 完整新任务、跨页面主流程或需求尚不明确   | `maa-workflow-build`         | 任务契约、真实页面观察、状态机、验收证据      |
| 初始化、刷新项目上下文                   | `maa-project-init`           | 根目录 `basic_info.md`，仅作静态缓存          |
| Pipeline 编写与审查                      | `maa-pipeline-guide`         | 保持本项目 v2 结构、节点名和安全恢复规则      |
| OCR、ROI、模板及截图派生节点             | `maa-pipeline-generate`      | 经当前页面验证的识别与动作节点                |
| Interface V2 审查和已有字段调整          | `maa-interface-guide`        | 路径、导入、控制器、任务与选项引用检查        |
| 添加选项及 Override/Agent 接线           | `maa-pipeline-option`        | Option 定义、task 注册、预定义目标节点同步    |
| 识别、资源、Custom 注册与端到端测试      | `maa-pipeline-testing`       | 区分资源可加载、识别命中和任务完成            |
| 已发生失败且责任方仍不明                 | `maa-diagnose`               | 只读证据与失败归属，不直接修复                |
| 节点关系图与跨文件引用可视化             | `maa-pipeline-graph`         | 按明确图谱需求生成本地交互图                  |
| Git 历史、Custom/Option 演进审查         | `maa-pipeline-history-audit` | 历史报告，当前行为仍须复核                    |
| 官方 API、Schema、版本与语义依据         | `maa-wiki`                   | 从目录导航回到指定版本的原始官方来源          |
| 创建或维护 create-maa-project 管理的项目 | `maa-project-create`         | 先核对 `maa-project.json`；本项目目前无此清单 |
| 可复现的设备发现、资源检查与短操作       | `maa-cli-operate`            | 固定 CLI 版本、JSON 输出和明确设备会话        |

旧的 `pipeline-guide`、`pipeline-option`、`pipeline-generate`、`pipeline-testing` 仅作为缺少新版技能时的备用。不要对同一任务同时套用新旧两套流程；缺失技能要明确报告，不能继续引用未安装的 `maaframework`。

## 环境与上下文检查

1. 检查工作区已有修改，读取 `AGENTS.md`、对应任务文档和自动化策略。
2. 确认项目 Python、实际 native runtime 与校验版本一致；MCP/CLI 的独立 Python 环境也要核对版本。
3. 主 Interface 为 `assets/interface.json`，当前资源声明为相对 Interface 的 `./resource`，Agent 为 `../agent/main.py`。涉及路径变更时重新读取声明，不按其他项目示例猜测。
4. `basic_info.md` 存在时先读第 0 节和任务对应章节，再核对当前源码。它被 Git 忽略，不能替代任务文档或当次设备证据；源码较新时标明过期。
5. 只有明确初始化或刷新请求才运行 `maa-project-init`；已有上下文不静默覆盖。图谱也按需要生成，不作为每个任务的固定前置步骤。

## MCP 可用性与后端选择

按以下三个层次记录状态，不能只看配置就宣称工具可用：

- **已配置**：Codex 配置中存在启用的 `maa-mcp`，命令和固定包版本正确。
- **可启动**：独立进程能完成 MCP `initialize` 和 `tools/list`；输出帮助或列出配置不足以证明握手成功。
- **会话可调用**：当前聊天实际提供设备发现、连接、OCR、截图、运行与停止函数；随后才能在明确设备上观察和验证。

MaaMCP 用于持久探索、截图/OCR、Interface Case 和多文件 Pipeline 测试。CLI 用于重复性检查和短操作，遵循 `maa-cli-operate` 的固定版本契约，并输出 JSON。不要让两个后端同时控制同一会话；不要停止已有的外部 daemon 或清空他人的控制器。

MCP 的配置位置、stdio 参数和启动超时参照 [Codex 官方 MCP 文档](https://developers.openai.com/codex/mcp)。MCP 未出现在当前聊天工具目录时，先检查命令可执行性、下载缓存和启动日志，再在重新加载配置后的会话确认专用工具；不得把“已启用”记为“已完成设备验证”。

## 开发与验收顺序

1. 明确入口、成功态、失败态、用户选项、允许的资源消耗和停止点。新任务或跨页面重构先观察完整真实路径并记录于 `docs/zh_cn/tasks/`。
2. 以观察证据设计 Pipeline 状态机。生成的识别节点需接入成功、异常恢复和安全退出分支；只有复杂计算交给 Agent。
3. Option 修改同步三处接线；CustomAction 和 CustomRecognition 精确匹配注册名，新增模块在 `agent/main.py` 导入。
4. 运行 Prettier、`maa-tools check`、JSON Schema、体力配置同步与交互稳定性检查。具体命令见 [开发环境](development_environment.md)。
5. 已知稳定页面先做临时 `DoNothing` 探针。识别命中后才测试交互，动作后重新确认页面；关闭 Agent 不会把 Click 节点变成纯识别探针。
6. 多文件流程提供完整依赖、资源根、Case Override 和必要的 Agent；设置人工超时。切换测试集合前停止自己的任务并清理其驻留资源。
7. 按正常、已完成、选项关闭、失败恢复等分支验收，再进行已授权的资源消耗路径。结果记录日期、客户端、设备、覆盖分支和日志/截图位置。
8. 聚焦失败先回到识别、选项或状态机负责模块；责任方仍不明才使用 `maa-diagnose`。静态检查通过不能替代实机结果。

当前工具、依赖和验证状态记录在 [环境验收记录](../records/environment.md)。没有设备证据的分支继续标记待验证。
