# 体力活动配置维护指南

本文说明如何在活动换期时维护 `assets/stamina_activities.yaml`。页面流转、异常分支和实机验证记录见 [`../task_flows/task_daily_stamina.md`](../task_flows/task_daily_stamina.md)。

## 配置边界

- `templates` 描述可跨活动复用的内部 UI 路线，不写具体活动名称。
- `activity_groups.<id>.base` 描述一个活动共用的名称、页面 marker 和 Override。
- `activity_groups.<id>.cases` 描述各关卡之间的差异，也可包含自动通关 Case。
- 顶层 `activities` 只用于不值得建立活动组的独立关卡，例如常驻日常关卡。
- `assets/interface.json` 中“体力消耗关卡”的 Case 是生成结果，不直接编辑。

生成器按以下顺序深度合并配置，右侧覆盖左侧：

```text
defaults <- templates[template] <- activity_groups.<id>.base <- cases[i]
```

因此活动名和公共 marker 应放在 `base`，单个关卡的 OCR、体力消耗或特殊 Override 放在对应 `case`。

## 公共字段

| 字段                   | 用途                                                |
| ---------------------- | --------------------------------------------------- |
| `case_prefix`          | 自动生成 `<活动名> - <case_suffix>`                 |
| `description_template` | 可使用 `{activity}`、`{stage}`、`{case}`            |
| `template`             | 选择内部 UI 路线                                    |
| `activity_name`        | 外部活动栏位名称 OCR；仍是区分活动的依据            |
| `stage.expected`       | 目标关卡 OCR 文本及兼容写法                         |
| `stage.any_selectable` | 用于确认已经进入正确的关卡页面                      |
| `stamina.cost`         | 单次关卡体力消耗；放在活动组或 Case 中              |
| `stamina.reserve`      | 结束后希望保留的体力，默认 0                        |
| `mode`                 | 特殊生成模式；常规自动通关使用 `regular_auto_clear` |
| `extra_overrides`      | 仅在现有模板字段不足以表达差异时使用                |

ROI 均以游戏画面 `720x1280` 为基准。活动名称、关卡文字和 marker 必须来自当前客户端截图，不能直接沿用上期活动。

## UI 模板

| 模板                          | 适用 UI            | 活动组 `base` 必填内容                                     |
| ----------------------------- | ------------------ | ---------------------------------------------------------- |
| `regular_paged_list`          | 常规活动分页列表   | `activity_name`、`stage.any_selectable`、第一页 marker     |
| `rerun_activity_map`          | 复刻活动二维地图   | `activity_name`、`rerun.column`、地图 marker               |
| `large_activity_stage_icon`   | 大型活动关卡图标页 | `activity_name`、`inner_title`、`stage_entry`、列表 marker |
| `large_activity_direct_stage` | 大型活动直接关卡页 | `activity_name`、`inner_title`                             |
| `daily_affairs_list`          | 日常政务分类列表   | `activity_section`、`activity_name`、分类、列表 marker     |

`large_activity_direct_stage` 底层沿用历史 `challenge_button` 路线名，表示大型活动内部按钮形态，与活动开放数天后出现的挑战活动无关。

## 常规活动示例

```yaml
activity_groups:
    example_regular:
        case_prefix: "活动名称"
        description_template: "选择 {activity}，进入关卡列表后刷取{stage}。"
        base:
            template: regular_paged_list
            stamina:
                cost: 30
            activity_name:
                expected: ["活动名称"]
                roi: [70, 770, 580, 80]
            stage:
                any_selectable:
                    expected: ["活动页面固定文字"]
                    roi: [0, 90, 720, 180]
            extra_overrides:
                DailyStaminaPresetFirstPageMarker:
                    enabled: true
                    recognition:
                        type: OCR
                        param:
                            expected: ["第一页关卡名"]
                            roi: [0, 160, 720, 1000]
        cases:
            - case_suffix: "关卡-01"
              stage:
                  expected: ["关卡-01", "关卡01"]
```

同 UI 常规活动换期时通常只需复制活动组，修改活动名、页面 marker、第一页 marker 和 `cases`。

常规活动自动通关 Case 使用 `regular_auto_clear`。生成器会复用活动组的 `stage.any_selectable` 作为列表 marker，并自动切换内部入口：

```yaml
- case_suffix: "自动通关"
  description: "按 NEW 标记推进当前活动未通关关卡。"
  mode: regular_auto_clear
```

当前自动通关仅适配常规活动本体。复刻活动自动通关仍未实现；挑战活动不在适配范围内。

## 复刻活动示例

```yaml
activity_groups:
    example_rerun:
        case_prefix: "复刻活动名称"
        base:
            template: rerun_activity_map
            activity_name:
                expected: ["复刻活动名称"]
            rerun:
                marker:
                    expected: ["Story", "Free Quest"]
                    roi: [0, 160, 720, 1000]
                column: main
        cases:
            - case_suffix: "目标关卡"
              stage:
                  expected: ["目标关卡"]
              stamina:
                  cost: 30
```

`rerun.column` 可选 `main`、`left`、`right`，表示目标关卡所在横向区域。活动地图布局变化后必须重新确认列位置和上下滑动范围。

## 大型活动示例

关卡图标页使用 `large_activity_stage_icon`：

```yaml
base:
    template: large_activity_stage_icon
    stamina:
        cost: 30
    activity_name:
        expected: ["大型活动名称"]
    inner_title:
        expected: ["活动内部标题"]
    stage_entry:
        type: OCR
        param:
            expected: ["关卡入口文字"]
            roi: [0, 160, 720, 1000]
    stage:
        any_selectable:
            expected: ["关卡列表固定文字"]
```

直接关卡页使用 `large_activity_direct_stage`：

```yaml
base:
    template: large_activity_direct_stage
    stamina:
        cost: 30
    activity_name:
        expected: ["大型活动名称"]
    inner_title:
        expected: ["活动内部标题"]
cases:
    - case_suffix: "目标关卡"
      stage:
          expected: ["目标关卡"]
```

两种大型活动入口的点击目标和进入后的页面不同，不应为了减少节点数量合并状态链。

## 更新步骤

1. 在模拟器中确认活动栏位名称和内部 UI 类型。
2. 保存活动选择页、内部首页、关卡列表和关卡详情截图。
3. 复制匹配的活动组或创建新组，填写真实 OCR 文本、ROI、体力值和关卡 Case。
4. 运行 `python tools/build_stamina_activities.py --print-case "Case 名称"` 检查单个生成结果。
5. 运行 `python tools/build_stamina_activities.py` 更新 `assets/interface.json`。
6. 运行 `python tools/build_stamina_activities.py --check` 确认同步。
7. 执行 Prettier、JSON Schema、`maa-tools check` 和受影响路线的实机验证。

## 需要修改 Pipeline 的情况

以下变化不能只修改 YAML：

- 活动栏位超过三个，或活动选择页需要横向滚动。
- 内部页面不属于现有四种模板。
- 关卡入口需要新的点击、滑动或弹窗处理。
- 复刻地图的列结构、边界或返回落点发生变化。
- 自动通关需要适配复刻或大型活动。

新增路线时先在 `daily_stamina_routes.json` 实现通用状态链，再在生成器的 `ROUTE_START_NODES` 注册稳定的 `route_type`，并在 `ROUTE_ENTRY_MARKER_NODES` 登记能够证明已经进入内部 UI 的 marker。活动名称只负责外部栏位选择，不能代替内部页面确认；最后补充本指南和任务流程文档。
