# 项目开发指南

## 项目结构

- `agent/`：自定义识别、动作和 Agent 服务入口。
- `assets/resource/pipeline/`：声明式 Pipeline。
- `assets/interface.json`：用户任务、选项和 Override。
- `assets/resource/image/`：TemplateMatch 识别素材。
- `tools/`：配置生成、Schema 校验和辅助检查。
- `docs/zh_cn/tasks/`：统一任务流程文档。

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
