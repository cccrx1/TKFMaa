# 项目开发指南

## 项目结构

- `agent/`：自定义识别、动作和 Agent 服务入口。
- `assets/resource/pipeline/`：声明式 Pipeline。
- `assets/interface.json`：用户任务、选项和 Override。
- `assets/resource/image/`：TemplateMatch 识别素材。
- `tools/`：配置生成、Schema 校验和辅助检查。
- `docs/zh_cn/tasks/`：统一任务流程文档。
- `docs/zh_cn/develop/optimization_roadmap.md`：五阶段稳定性优化路线和调试信息边界。

## Pipeline 架构基线

项目采用三层协作：

- **Interface 层**（`assets/interface.json`）声明任务入口、用户选项和 `pipeline_override`。Override 只能合并已存在的节点属性，不能创建节点。
- **Pipeline 层**（`assets/resource/pipeline/`）表达页面状态机：识别页面、执行动作、通过 `next`/`on_error`/`[JumpBack]` 恢复，并用 `max_hit`、`timeout` 限制重试。
- **Agent 层**（`agent/`）只承载 Pipeline 难以表达的运行时计算，例如体力数值解析、道具库存选择、商品去重和招募词条组合。`agent/main.py` 通过导入模块触发自定义识别与动作注册。

公共节点集中在 `common.json` 和 `common_return.json`；任务 Pipeline 通过节点名跨文件引用它们。`regular_activity.json` 是常规活动/自动战斗的共享子流程，体力路线通过 `daily_stamina_routes.json` 与 `daily_stamina_presets.json` 组合。

优化时优先保持“识别 → 动作 → 再识别”，先在 Pipeline 中补充明确状态和安全回退，再考虑 Agent 逻辑；需要改变选项行为时同时检查 Interface、Override 目标节点和对应任务文档。

## 优化路线

1. **建立节点引用清单**：检查入口、跨文件引用、`[JumpBack]` 和锚点，确认每个任务都有可识别的完成态和安全退出态。
2. **核对公共状态**：优先验证 `CommonEnsureMain`、加载/奖励弹窗处理和各任务返回主界面的识别，避免局部任务重复实现返回逻辑。
3. **按风险验证流程**：先登录、领取和派遣，再商城、调教、征才，最后验证体力和自动战斗；高风险任务必须在模拟器中记录实际页面和停止点。
4. **收敛 Agent 边界**：为自定义识别保留可诊断 `detail`，为 OCR 失败提供安全结果；能用 Pipeline 表达的固定分支不继续堆到 Python。
5. **同步文档与检查**：流程变化同步任务 Mermaid 和实现映射，然后运行 Prettier、`maa-tools check`、Schema 校验及交互稳定性检查。

`2026-09-12` 的静态核对已发现：任务文档 Mermaid 围栏存在格式错误（本轮修复）、总览漏列自动战斗（本轮修复）、部分任务文档仍需以当前 Interface 和实际客户端复核。

本地环境设置与检查命令见 [开发环境](development_environment.md)，五阶段进度统一维护在 [稳定性优化路线](optimization_roadmap.md)。

## 开发流程

1. 阅读 `AGENTS.md` 和对应任务流程文档。
2. 明确入口、前置状态、资源条件和安全退出状态。
3. 涉及新任务或跨页面流程时，先观察真实页面并更新流程图。
4. 优先使用 Pipeline 状态机表达页面流转，复杂决策才放入 Agent。
5. 修改 Interface 选项时同步任务注册、Option 定义和 Pipeline Override。
6. 运行适用的格式、`maa-tools check` 和 JSON Schema 检查。
7. 在结果中说明改动范围、检查命令、未覆盖分支和风险。

## 文档更新规则

任务页面顺序、选项行为、资源边界或安全退出改变时，更新对应任务文档。开发命令、目录结构和硬性协作规则改变时，更新本文件和 `AGENTS.md`。不要把历史日志、设备信息和资源前后数值写入公开任务文档。

## AI 协作方式

AI 与人类贡献者使用同一套任务文档。AI 开始工作前应先读取 `AGENTS.md`，再读取对应任务流程和自动化策略；修改前检查工作区已有变更；高风险操作先说明目标、数量、停止点；没有当次命令、截图或日志时不得声称已验证。

## 检查命令

- `npx prettier --check .`
- `npx @nekosu/maa-tools check`
- `python tools/validate_schema.py --schema-dir deps/tools --resource-dirs assets/resource --exclude-dirs assets/resource/announcement --interface-files assets/interface.json`
- `python tools/add_interaction_stability.py --check`
- `python tools/build_stamina_activities.py --check`

## 稳定术语

任务入口节点使用 `Daily...Start` 或 `GameLoginStart`。同一任务的节点保持功能前缀。流程图中的页面名称可以使用玩家可见文本，具体 OCR 变体以任务文档实现映射为准。
