# Maa 开发规则

修改 Pipeline、Interface、Agent、活动配置或执行设备测试前阅读。授权边界见[AGENTS.md](../../../AGENTS.md)。

## 生成配置与派生产物

`assets/stamina/active.yaml` 是“体力消耗关卡”选项的唯一源数据，`assets/interface.json` 中对应的选项键、任务选项引用、`default_case` 和 `cases` 由 `tools/build_stamina_activities.py` 生成，不应手工修改。选项键包含列表布局及有序关卡名称的摘要，列表增删或重排时使旧序号失效并默认选中第一个真实关卡；显示名称固定，不添加重选占位项或入口拦截。仅修正 ROI 等而关卡名称和顺序不变时不重置选择。修改 YAML，或修改生成脚本中会影响输出的模板、校验和 Override 逻辑后，必须运行生成命令，并将源文件、脚本改动和生成后的 `assets/interface.json` 放在同一提交中。

同一活动包含多个关卡时使用 `activity_groups`：活动名称、页面 marker 和公共 Override 放入 `base`，各关卡差异放入 `cases`；`templates` 仅描述可跨活动复用的内部 UI 路线，不写具体活动名称。四类路线见[消耗体力](../tasks/daily_stamina.md)，字段以源 YAML 和生成脚本为准。本地 `docs/zh_cn/develop/stamina_activity_config.md` 存在时可作为补充。

不确定是否需要重新生成时，先运行 `python tools/build_stamina_activities.py --check`：退出码为 0 表示已同步，无需生成；提示 `is not in sync` 时运行不带 `--check` 的生成命令，再次执行 `--check`。仅修改其他任务、文档或不影响输出的脚本注释时不需要生成，但提交前仍建议执行检查。生成后还必须运行 Prettier、`maa-tools check` 和 JSON Schema 校验，生成成功不等于 Pipeline 行为已通过实机验证。

## MaaFramework Pipeline 开发规范

- 延续仓库现有的 Pipeline v2 结构，将 `type` 和参数分别放入 `recognition`、`action` 的 `param` 中。流程遵循“识别 -> 动作 -> 再识别”，不能假设点击后一定进入目标页面。
- `next` 按命中优先级覆盖成功、加载、弹窗和异常页面；可恢复的中断使用 `[JumpBack]` 返回父节点继续判断。滚动或重试节点应设置 `max_hit`，避免无限循环和重复点击。
- 跨页面流程优先用 `next` 与 `[JumpBack]` 组成 JSON 状态机。只有复杂运行时计算或 Pipeline 难以表达的识别决策才放入 `agent/`，不要用 Python `for`/`while` 串行调用任务来模拟页面状态机。
- 不滥用 `pre_delay`、`post_delay` 和长 `timeout`。确需等待动画或加载稳定时使用 `pre_wait_freezes`/`post_wait_freezes`，动作后仍须识别目标状态。
- 带明确识别结果的 `Click`、`Swipe`、`LongPress` 等交互动作默认配置 `pre_wait_freezes: 300`，确认识别区域连续稳定后再操作。只在控件仅短暂出现或页面持续动画时豁免，并在 `tools/add_interaction_stability.py` 中记录原因。
- 坐标、ROI 和模板统一基于 720x1280 竖屏基准。ROI 应尽量缩小但完整包围目标；OCR 的 `expected` 优先填写完整界面文本，需要兼容误识别时显式列出变体。OCR 不稳定时先调整 ROI 并多次验证，不要立即改用图片匹配。
- 新增 TemplateMatch 素材时使用无损原图裁剪，路径相对 `assets/resource/image/`。提交前检查图片、节点引用及大小写完全一致。

## Interface、Option 与 Agent 联动

新增运行时选项必须同步完成三处修改：在 `assets/interface.json` 的 `option` 字典定义选项、在对应 `task.option` 数组注册选项、在 `assets/resource/pipeline/` 预先定义 Override 的目标节点。`pipeline_override` 只合并属性，不会创建节点。仅切换 `next`、`enabled`、识别文本或动作参数时优先使用纯 Override；确需 Python 决策时，再通过 `context.get_node_data()` 读取预定义配置节点。

自定义识别和动作使用 `@AgentServer.custom_recognition`、`@AgentServer.custom_action` 注册，注册名必须与 Pipeline 中的 `custom_recognition`、`custom_action` 完全一致。返回失败结果时保留可诊断的 `detail`，并为缺失或非法参数提供安全默认值。新增 Agent 模块后须在 `agent/main.py` 中导入以触发注册。

## Maa MCP 使用规范

`maa-mcp` 不是 TKFMaa 的运行依赖，仅在本地环境提供该工具时用于辅助采集和调试。使用时先通过 `find_adb_device_list` 与 `connect_adb_device` 明确连接设备；首次缺少模型时运行 `check_and_download_ocr`。`ocr` 已包含截图步骤，不要在调用前重复截图。通过 `load_pipeline`/`save_pipeline` 读写结构化 JSON，保留原有节点；遇到同名节点默认停止，只有明确确认后才覆盖。

`run_pipeline` 应设置人工超时；长时间无返回时停止任务并截图确认实际页面。验证单节点或无跨文件依赖的子流程时可只加载目标文件；验证跨文件流程时必须按依赖顺序传入完整的 Pipeline 文件列表，并指定项目资源目录。切换测试集合前先执行 `stop_pipeline` 和 `clear_pipeline_resources`，避免已驻留节点污染结果。验证 Interface Case 时还须提供对应的 `pipeline_override`，涉及自定义逻辑时启动并绑定 Agent。MCP 结果用于定位 ROI、识别文本和流程问题，不能替代 `maa-tools check`、Schema 校验及端到端验证。

## Agent 技能使用指引

下列路由适用于提供对应技能与工具的本地环境；缺少工具时报告无法完成的验证，不把工具视为项目运行依赖。`basic_info.md` 为被 Git 忽略的本地扫描缓存，存在时先读取接力章节，再核对当前源码；不要把静态图中的孤立节点直接当作可删除节点，Option 配置节点可能没有入边。

处理 MaaFramework API、控制器或自定义逻辑前参考 `maa-wiki`，再按需使用 `maa-pipeline-guide`；编写或审查 Pipeline JSON 使用 `maa-pipeline-guide`，新增 UI 选项使用 `maa-pipeline-option`，通过设备 OCR 生成节点或扫描 ROI 使用 `maa-pipeline-generate`，测试与验收使用 `maa-pipeline-testing`，跨页面新流程使用 `maa-workflow-build`，项目上下文扫描使用 `maa-project-init`。重复性设备检查可用固定版本 `maafw-cli`，长连接探索使用已配置的 `maa-mcp==1.2.3`；两者不要同时控制同一设备会话。技能中的示例路径可能来自其他仓库，落地时必须换成本仓库的 `assets/resource/pipeline/`、`assets/resource/image/` 和 `assets/interface.json`，并以当前代码及 Schema 为准。
