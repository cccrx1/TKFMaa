# Repository Guidelines

## 开始工作前

本仓库是基于 MaaFramework 的自动化助手。先检查工作区状态，只修改本次任务涉及的内容。
按下表读取对应专题；专题规则是仓库协作规则的一部分，无需每次读取全部发布细节。

| 工作类型                                       | 必读文档                                                                                                             |
| ---------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| 所有修改                                       | 本文件；[开发与验收](docs/zh_cn/contributing/development.md)                                                         |
| 文档、提示词或验证记录                         | [文档与验证资料](docs/zh_cn/contributing/documentation.md)、[模板](docs/zh_cn/templates/README.md)                   |
| Pipeline、Interface、Agent、活动配置、设备测试 | [Maa 开发规则](docs/zh_cn/contributing/maa.md)及对应[任务说明](docs/zh_cn/tasks/README.md)                           |
| 环境、依赖或版本升级                           | [运行环境与版本](docs/zh_cn/contributing/runtime.md)                                                                 |
| 构建、工作流、资源通道或发布                   | [构建与发布操作约束](docs/zh_cn/contributing/build_release.md)、[资源包与完整包构建](docs/zh_cn/resource_updates.md) |

## 项目地图与事实来源

- `agent/`：Python 自定义逻辑；新增模块须由 `agent/main.py` 导入以触发注册。
- `assets/resource/pipeline/`：Pipeline v2；`assets/resource/image/`：识别模板，统一 720x1280 竖屏基准。
- `assets/interface.json`：任务与选项；体力活动生成字段只能通过 `assets/stamina/active.yaml` 和 `tools/build_stamina_activities.py` 修改。
- `tools/`：构建、生成与校验脚本；`deps/tools/`：固定版本 Schema。
- `docs/zh_cn/`：公开入口；`contributing/` 为通用规范，`tasks/` 为行为说明，`templates/` 为空白模板。
- `docs/zh_cn/develop/`、`docs/zh_cn/records/`、`tools/test_*.py`：被忽略的本地资料；新检出可不存在，不得强制暂存。
- `basic_info.md`：本地扫描缓存；存在时先看接力章节，路径、节点和状态仍须与当前源码核对，不自动覆盖旧缓存。

代码与配置描述当前实现；任务文档描述功能行为；实测记录只证明指定环境和路径的结果。出现冲突时核对源码与证据，不以过期文档覆盖当前实现，也不把静态检查当作实机验证。

## 不可省略的约束

- 新增或重构跨页面主流程前观察实际游戏流程；页面流转优先用 Pipeline 状态机表达，不凭需求描述推测界面。
- 交互遵循“识别 → 动作 → 再识别”；带识别的交互默认 `pre_wait_freezes: 300`，豁免须登记原因；重试与滚动有上限。
- 新增选项同步定义、任务注册和预先存在的 Override 目标；自定义注册名必须与 Pipeline 一致。
- 生成配置与源数据同改同验，禁止手工修补生成字段。节点名及跨文件引用保持稳定。
- `maa-tools check` 与 JSON Schema 校验均须执行；行为修改还须验证受影响路径。购买、资源消耗及账号操作在合并前完成端到端实机验证。
- 未执行、失败、受阻与通过分开报告。纯文档修改无需设备测试，不会自动获得发布或远端操作授权。
- 功能说明与逐次测试记录分开；公开文档不得链接本地资料。远端仅保留必要且脱敏的验证摘要，日志、截图、缓存、模型和个人配置不自动上传。

## 常用检查

使用 Python 3.12；Windows 优先 `.venv312/`，设置 `PYTHONUTF8=1`。版本及构建锁定范围以[运行环境与版本](docs/zh_cn/contributing/runtime.md)所列配置为准。
首次配置按[本地开发环境](docs/zh_cn/contributing/setup.md)创建独立环境；明确调用环境内解释器，避免将依赖误装进系统的其他 Python 版本。

- `python tools/build_stamina_activities.py --check`：生成配置一致性。
- `python tools/add_interaction_stability.py --check`：交互稳定等待。
- `npx prettier --check .`：格式；`npm ci` 安装锁定的 Node 工具。
- `npx @nekosu/maa-tools check`：结构诊断与资源加载。
- `python tools/validate_schema.py --schema-dir deps/tools --resource-dirs assets/resource --exclude-dirs assets/resource/announcement --interface-files assets/interface.json`：Schema。
- `python tools/check_environment.py --load-resource`：环境与资源加载；Agent 注册在独立进程检查。
- 本地测试文件存在时运行 `python -m unittest discover -s tools -p 'test_*.py'`；远端 CI 不执行这些本地单元测试。

OCR 缺失时按 `tools/ocr_model.json` 使用 `python tools/configure.py --download` 恢复，不能仅依赖当前缺少 gitlink 的子模块声明。默认 GPU 检查崩溃时先保留日志，再按[构建命令索引](docs/zh_cn/contributing/build_release.md)执行 CPU 检查，不能据此宣称 GPU 验收通过。

## 文档同步

协作规则、目录或验证门槛变化时同步本文件及对应专题；行为变化时同步对应任务说明；完成实机测试后写本地验证记录。公开模板不填写个人数据。具体触发条件见[开发与验收](docs/zh_cn/contributing/development.md)。

## 提交与 Pull Request 规范

提交信息必须遵循 Conventional Commits：`<type>(<scope>): <中文摘要>`。`type` 使用 `feat`、`fix`、`docs`、`refactor`、`test`、`chore`、`ci`、`build` 或 `perf`；`scope` 可选，优先填写任务或模块英文名。冒号后的摘要、提交正文和 `BREAKING CHANGE:` 后的说明必须使用中文，摘要简短明确且不以句号结尾，例如：

- `feat(stamina): 添加体力不足安全退出`
- `fix(shop): 修复协会商店售罄识别`
- `docs(dispatch): 更新每日派遣流程记录`

一个提交只处理一个可独立说明和验证的改动。若同时修改多个任务，必须按任务分别提交，不得用一个 `feat` 或 `fix` 混合商城、体力、派遣等多个任务；被多个任务复用的公共节点、工具或基础设施改动单独提交，再分别提交各任务适配。仅属于同一任务且必须同时生效的 Pipeline、Interface、Agent、素材和文档应放在同一提交中，避免产生无法运行的中间状态。

分支使用 `feat/<name>`、`fix/<name>` 等明确格式。PR 目标分支为 `main`，每个 PR 只处理一个主题，并说明动机、影响范围、提交拆分和实际执行的验证命令。适用时使用 `Closes #123` 关联 Issue；涉及 UI、识别、工作流或行为变化时提供验证摘要；必要日志片段或截图经脱敏并获得上传授权后附上。未完成的改动请提交为 Draft PR。

## 版本控制安全

- 未经用户在当前对话中明确要求，不得执行 `git add`、`git commit`、`git push`、创建或删除分支、打标签、创建 PR 或触发发布；默认将修改保留在工作区供用户检查。
- 不得把“完成修改”“提交代码”等模糊表述自行解释为允许推送、打标签或发布；每类远程操作都需要明确指令。
- 用户要求提交时，先检查 `git status` 和目标文件差异，只暂存本次任务相关路径，不使用 `git add .`，不夹带用户已有修改、日志、缓存或生成产物。
- 提交前报告拟提交文件和验证结果；若发现同一文件含有无法安全拆分的用户改动，先停止并说明情况。
- 未经明确许可，不得执行 `commit --amend`、交互式 rebase、`reset`、强制推送、删除标签或绕过提交钩子。禁止使用 `git reset --hard`、`git clean -fd` 等可能丢失工作区内容的命令。
- 版本标签和 GitHub Release 视为发布操作。只有用户明确给出版本号并要求发布时才能执行，且发布前必须确认工作区、目标提交、验证结果和发布说明。
