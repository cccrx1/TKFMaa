# Repository Guidelines

## 项目结构与模块组织

本仓库是基于 MaaFramework 的自动化助手。Python 自定义动作逻辑位于 `agent/`，其中 `agent/main.py` 负责注册处理器并启动 Maa Agent 服务。声明式自动化流程位于 `assets/resource/pipeline/`，识别模板应放入 `assets/resource/image/` 下对应的功能目录。面向用户的任务与选项在 `assets/interface.json` 中声明。通用 OCR 模型通过 `assets/MaaCommonAssets` 子模块管理。构建、Schema 校验和数据生成脚本位于 `tools/`，贡献者文档位于 `docs/zh_cn/develop/`。目前没有独立的单元测试目录。

## 构建、测试与开发命令

- `git submodule update --init --recursive`：克隆后初始化 Maa 通用资源。
- `npm ci`：安装 CI 使用的锁定版本 Node.js 工具。
- `python -m pip install -r tools/requirements.txt`：安装打包和配置生成脚本依赖。
- `npx @nekosu/maa-tools check`：校验 Maa Pipeline 与 Interface 资源。
- `python -m pip install jsonschema==4.26.0 referencing==0.37.0`：安装 Schema 校验依赖。
- `python tools/validate_schema.py --schema-dir deps/tools --resource-dirs assets/resource --exclude-dirs assets/resource/announcement --interface-files assets/interface.json`：执行与 CI 相同的 JSON Schema 校验。
- `python tools/build_stamina_activities.py`：修改 `assets/stamina_activities.yaml` 后重新生成体力活动配置。
- `python tools/build_stamina_activities.py --check`：只检查体力活动配置与 `assets/interface.json` 是否同步，不写文件。
- `python tools/add_interaction_stability.py --check`：检查带识别结果的交互动作是否配置点击前稳定等待。

`.github/workflows/install.yml` 会为 `v1.2.3` 等版本标签构建发布包。本地打包需要预先下载 MaaFramework 运行时，不属于常规开发验证流程。

## 生成配置与派生产物

`assets/stamina_activities.yaml` 是“体力消耗关卡”选项的唯一源数据，`assets/interface.json` 中对应的 `default_case` 和 `cases` 由 `tools/build_stamina_activities.py` 生成，不应手工修改。修改 YAML，或修改生成脚本中会影响输出的模板、校验和 Override 逻辑后，必须运行生成命令，并将源文件、脚本改动和生成后的 `assets/interface.json` 放在同一提交中。

同一活动包含多个关卡时使用 `activity_groups`：活动名称、页面 marker 和公共 Override 放入 `base`，各关卡差异放入 `cases`；`templates` 仅描述可跨活动复用的内部 UI 路线，不写具体活动名称。四类模板、字段要求和示例见 `docs/zh_cn/develop/stamina_activity_config.md`。

不确定是否需要重新生成时，先运行 `python tools/build_stamina_activities.py --check`：退出码为 0 表示已同步，无需生成；提示 `is not in sync` 时运行不带 `--check` 的生成命令，再次执行 `--check`。仅修改其他任务、文档或不影响输出的脚本注释时不需要生成，但提交前仍建议执行检查。生成后还必须运行 Prettier、`maa-tools check` 和 JSON Schema 校验，生成成功不等于 Pipeline 行为已通过实机验证。

## 代码风格与命名约定

统一使用 LF 换行和空格缩进。Prettier 配置为 4 空格、每行最多 120 字符，YAML 使用 2 空格；配置类改动提交前运行 `npx prettier --check .`。Python 使用 4 空格缩进，函数和模块采用 `snake_case`，类采用 `PascalCase`，在接口含义不明确时补充类型标注，并将导入集中放在文件顶部。Pipeline JSON 和图片目录按功能命名，例如 `daily_shop.json`、`DailyRecruitment/`。节点使用带功能前缀的 `PascalCase`，例如 `DailyShopOpenExchangeTab`；仅供文件内部使用的节点以 `__` 开头。节点名必须保持稳定，因为 Pipeline、Interface Override 和 Agent 均可能通过名称引用。

## MaaFramework Pipeline 开发规范

- 延续仓库现有的 Pipeline v2 结构，将 `type` 和参数分别放入 `recognition`、`action` 的 `param` 中。流程遵循“识别 -> 动作 -> 再识别”，不能假设点击后一定进入目标页面。
- `next` 按命中优先级覆盖成功、加载、弹窗和异常页面；可恢复的中断使用 `[JumpBack]` 返回父节点继续判断。滚动或重试节点应设置 `max_hit`，避免无限循环和重复点击。
- 跨页面流程优先用 `next` 与 `[JumpBack]` 组成 JSON 状态机。只有复杂运行时计算或 Pipeline 难以表达的识别决策才放入 `agent/`，不要用 Python `for`/`while` 串行调用任务来模拟页面状态机。
- 不滥用 `pre_delay`、`post_delay` 和长 `timeout`。确需等待动画或加载稳定时使用 `pre_wait_freezes`/`post_wait_freezes`，动作后仍须识别目标状态。
- 带明确识别结果的 `Click`、`Swipe`、`LongPress` 等交互动作默认配置 `pre_wait_freezes: 300`，确认识别区域连续稳定后再操作。只在控件仅短暂出现或页面持续动画时豁免，并在 `tools/add_interaction_stability.py` 中记录原因。
- 坐标、ROI 和模板统一基于 720x1280 竖屏基准。ROI 应尽量缩小但完整包围目标；OCR 的 `expected` 优先填写完整界面文本，需要兼容误识别时显式列出变体。OCR 不稳定时先调整 ROI 并多次验证，不要立即改用图片匹配。
- 新增 TemplateMatch 素材时使用无损原图裁剪，路径相对 `assets/resource/image/`。提交前检查图片、节点引用及大小写完全一致。

## 任务开发流程

- 新增任务或重构跨页面主流程前，必须先在模拟器中观察实际游戏流程，并在 `docs/zh_cn/task_flows/` 建立流程记录。
- 流程记录至少包含前置状态、页面流转、识别依据、异常分支和完成状态；不能只按需求描述推测界面行为。
- 局部识别或动作修复只需复现并验证受影响路径，可将截图、日志和结果记录在 Issue 或 PR 中；纯文档及非行为改动无需运行模拟器。
- 涉及购买、资源消耗、账号操作等高风险行为时，合并前必须完成端到端实机验证。
- 从其他项目或旧分支迁入的文档只能作为线索；必须核对本仓库路径、节点、选项和当前客户端，未经本项目复测的“已验证”记录统一标为待验证。
- 具体分级、操作步骤、记录模板和验收要求见 `docs/zh_cn/develop/task_workflow.md`。

## 文档同步时机

- 仓库目录、必需命令、编码约定、验证门槛或协作规则改变时，必须在同一 PR 更新 `AGENTS.md`；具体功能实现变化不写入本文件。
- 流程采集方法、变更分级、记录模板或验收标准改变时，更新 `docs/zh_cn/develop/task_workflow.md`。
- 新增任务，或现有任务的页面顺序、识别依据、Option 行为、Agent 决策、异常恢复、资源消耗或结束条件改变时，更新对应的 `docs/zh_cn/task_flows/task_*.md`。
- ROI、OCR 文本或模板调整如果改变识别目标、适用页面或已知风险，需要同步任务文档；仅微调数值且流程含义不变时，在 PR 验证记录中说明即可。
- 完成新的实机验证后，更新任务文档的“验证记录”，注明日期、客户端版本、设备和覆盖路径；未覆盖分支继续保留为待验证。
- 纯格式化、无行为重构或未被文档引用的内部节点重命名通常无需更新任务文档；若文档引用的路径、节点或命令发生变化，必须同步修正。

## Interface、Option 与 Agent 联动

新增运行时选项必须同步完成三处修改：在 `assets/interface.json` 的 `option` 字典定义选项、在对应 `task.option` 数组注册选项、在 `assets/resource/pipeline/` 预先定义 Override 的目标节点。`pipeline_override` 只合并属性，不会创建节点。仅切换 `next`、`enabled`、识别文本或动作参数时优先使用纯 Override；确需 Python 决策时，再通过 `context.get_node_data()` 读取预定义配置节点。

自定义识别和动作使用 `@AgentServer.custom_recognition`、`@AgentServer.custom_action` 注册，注册名必须与 Pipeline 中的 `custom_recognition`、`custom_action` 完全一致。返回失败结果时保留可诊断的 `detail`，并为缺失或非法参数提供安全默认值。新增 Agent 模块后须在 `agent/main.py` 中导入以触发注册。

## Maa MCP 使用规范

`maa-mcp` 不是 TKFMaa 的运行依赖，仅在本地环境提供该工具时用于辅助采集和调试。使用时先通过 `find_adb_device_list` 与 `connect_adb_device` 明确连接设备；首次缺少模型时运行 `check_and_download_ocr`。`ocr` 已包含截图步骤，不要在调用前重复截图。通过 `load_pipeline`/`save_pipeline` 读写结构化 JSON，保留原有节点；遇到同名节点默认停止，只有明确确认后才覆盖。

`run_pipeline` 应设置人工超时；长时间无返回时停止任务并截图确认实际页面。验证单节点或无跨文件依赖的子流程时可只加载目标文件；验证跨文件流程时必须按依赖顺序传入完整的 Pipeline 文件列表，并指定项目资源目录。切换测试集合前先执行 `stop_pipeline` 和 `clear_pipeline_resources`，避免已驻留节点污染结果。验证 Interface Case 时还须提供对应的 `pipeline_override`，涉及自定义逻辑时启动并绑定 Agent。MCP 结果用于定位 ROI、识别文本和流程问题，不能替代 `maa-tools check`、Schema 校验及端到端验证。

## Agent 技能使用指引

处理 MaaFramework API、控制器或自定义逻辑前参考 `maaframework` 技能；编写或审查 Pipeline JSON 时参考 `pipeline-guide`；新增 UI 选项时参考 `pipeline-option`；通过设备 OCR 生成节点或扫描 ROI 时参考 `pipeline-generate`。技能中的示例路径可能来自其他仓库，落地时必须换成本仓库的 `assets/resource/pipeline/`、`assets/resource/image/` 和 `assets/interface.json`，并以当前代码及 Schema 为准。

## 测试规范

`maa-tools check` 与 JSON Schema 校验均为必做检查。修改识别或动作逻辑后，还应在当前开发环境中运行受影响任务；本地提供 MaaMCP 时优先使用其多文件 `run_pipeline` 完成设备集成测试，并记录相关日志、截图或修改前后行为。坐标、ROI 和模板须遵循 MaaFramework 的 720p 基准。不要提交运行日志、调试截图、缓存或下载的大型模型文件。

## 提交与 Pull Request 规范

提交信息必须遵循 Conventional Commits：`<type>(<scope>): <中文摘要>`。`type` 使用 `feat`、`fix`、`docs`、`refactor`、`test`、`chore`、`ci`、`build` 或 `perf`；`scope` 可选，优先填写任务或模块英文名。冒号后的摘要、提交正文和 `BREAKING CHANGE:` 后的说明必须使用中文，摘要简短明确且不以句号结尾，例如：

- `feat(stamina): 添加体力不足安全退出`
- `fix(shop): 修复协会商店售罄识别`
- `docs(dispatch): 更新每日派遣流程记录`

一个提交只处理一个可独立说明和验证的改动。若同时修改多个任务，必须按任务分别提交，不得用一个 `feat` 或 `fix` 混合商城、体力、派遣等多个任务；被多个任务复用的公共节点、工具或基础设施改动单独提交，再分别提交各任务适配。仅属于同一任务且必须同时生效的 Pipeline、Interface、Agent、素材和文档应放在同一提交中，避免产生无法运行的中间状态。

分支使用 `feat/<name>`、`fix/<name>` 等明确格式。PR 目标分支为 `main`，每个 PR 只处理一个主题，并说明动机、影响范围、提交拆分和实际执行的验证命令。适用时使用 `Closes #123` 关联 Issue；涉及 UI、识别、工作流或行为变化时附上日志或截图。未完成的改动请提交为 Draft PR。

## 版本控制安全

- 未经用户在当前对话中明确要求，不得执行 `git add`、`git commit`、`git push`、创建或删除分支、打标签、创建 PR 或触发发布；默认将修改保留在工作区供用户检查。
- 不得把“完成修改”“提交代码”等模糊表述自行解释为允许推送、打标签或发布；每类远程操作都需要明确指令。
- 用户要求提交时，先检查 `git status` 和目标文件差异，只暂存本次任务相关路径，不使用 `git add .`，不夹带用户已有修改、日志、缓存或生成产物。
- 提交前报告拟提交文件和验证结果；若发现同一文件含有无法安全拆分的用户改动，先停止并说明情况。
- 未经明确许可，不得执行 `commit --amend`、交互式 rebase、`reset`、强制推送、删除标签或绕过提交钩子。禁止使用 `git reset --hard`、`git clean -fd` 等可能丢失工作区内容的命令。
- 版本标签和 GitHub Release 视为发布操作。只有用户明确给出版本号并要求发布时才能执行，且发布前必须确认工作区、目标提交、验证结果和发布说明。
