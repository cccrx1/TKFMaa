# 验证与调试记录

本目录集中存放实机验证、调试结论和覆盖状态，供人工审核使用。

`docs/zh_cn/tasks/` 和 `docs/zh_cn/develop/` 只描述流程、识别依据和实现约束，不再保留带日期的测试记录。
审核流程文档时如果需要判断某条路径是否真的跑过，请到本目录查对应记录。

## 记录文件

任务类记录与 `docs/zh_cn/tasks/` 下的流程文档一一对应。

| 记录                                   | 对应流程                                        |
| -------------------------------------- | ----------------------------------------------- |
| [启动游戏](game_login.md)              | [启动游戏](../tasks/game_login.md)              |
| [公共主界面恢复](common_navigation.md) | [公共主界面恢复](../tasks/common_navigation.md) |
| [好友体力](daily_friend_stamina.md)    | [好友体力](../tasks/daily_friend_stamina.md)    |
| [任务奖励](daily_task_rewards.md)      | [任务奖励](../tasks/daily_task_rewards.md)      |
| [炼金订单](daily_alchemy_orders.md)    | [炼金订单](../tasks/daily_alchemy_orders.md)    |
| [每日派遣](daily_dispatch.md)          | [每日派遣](../tasks/daily_dispatch.md)          |
| [商城购买](daily_shop.md)              | [商城购买](../tasks/daily_shop.md)              |
| [调教](daily_training.md)              | [调教](../tasks/daily_training.md)              |
| [全境征才](daily_recruitment.md)       | [全境征才](../tasks/daily_recruitment.md)       |
| [消耗体力](daily_stamina.md)           | [消耗体力](../tasks/daily_stamina.md)           |
| [自动战斗](auto_battle.md)             | [自动战斗](../tasks/auto_battle.md)             |

非任务类记录：

| 记录                                    | 内容                                                                |
| --------------------------------------- | ------------------------------------------------------------------- |
| [开发环境](environment.md)              | 本地 Python、`maafw`、插件和 OCR 资源的验收结论                     |
| [优化路线进度](optimization_roadmap.md) | [五阶段优化路线](../develop/optimization_roadmap.md) 的阶段执行进度 |
| [文档核对](project_review.md)           | 任务文档与总览的静态核对结论                                        |

## 记录格式

- `## 覆盖状态`：不带日期的状态说明，例如「主流程：已实现」以及仍未验证的分支。
- `## 验证记录`：按时间顺序排列的实测与调试结论，条目自带日期，或整节以 `## YYYY-MM-DD` 作标题。
- 非任务类记录可以按内容命名分节，例如开发环境验收使用 `## 2026-09-12 本地验收记录`。

新增记录时：

1. 在对应记录文件的验证记录末尾按时间顺序追加，写清日期、客户端版本、设备和当轮结论。
2. 覆盖到的路径写明「已覆盖」；未覆盖的分支继续保留在 `## 覆盖状态`，不要因为跑通一条路径就删除其他待验证条目。
3. 只把真实执行过的结果写进 `## 验证记录`，推测和计划留在流程文档或优化路线里。
4. 耗时和资源变化等数值可以记录，但日志、截图、账号信息和本地路径不进仓库。

本目录只保留结论，不保留原始证据。设备日志、截图和配置按
[优化路线](../develop/optimization_roadmap.md) 的调试信息边界只保存在本机 `debug/` 目录。
