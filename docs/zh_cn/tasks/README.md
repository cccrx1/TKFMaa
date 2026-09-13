# 功能流程总览

任务文档使用统一结构：功能目标、前置条件、流程图、关键分支、选项、实现映射、当前限制和状态。

流程图展示当前代码中的页面流转，并不代表所有分支均已实测；验证日期、覆盖路径和待验证分支见各文档的“当前状态”。
后续优化页面顺序、识别条件、重试或结束逻辑时，同步更新流程图和文字说明；复杂任务分别绘制主流程与子流程。
图中应保留加载、弹窗、无可处理内容、重试上限、结束确认和已实现的错误路径，不把计划中的恢复能力画成现有行为。

```mermaid
flowchart TD
    Main[主界面]
    Login[启动游戏] --> Main
    Main --> Friend[好友体力]
    Main --> Rewards[任务奖励]
    Main --> Alchemy[炼金订单]
    Main --> Dispatch[每日派遣]
    Main --> Shop[商城购买]
    Main --> Training[调教]
    Main --> Recruitment[全境征才]
    Main --> Stamina[消耗体力]
    Manual[手动进入常规活动关卡列表] --> AutoBattle[自动战斗]
```

总览表示各功能的主要入口关系，不表示任务执行顺序；各任务的返回与异常分支见对应详情图。

| 功能     | 入口节点                  | 风险 | 文档                                |
| -------- | ------------------------- | ---- | ----------------------------------- |
| 启动游戏 | `GameLoginStart`          | 低   | [启动游戏](game_login.md)           |
| 商城购买 | `DailyShopStart`          | 高   | [商城购买](daily_shop.md)           |
| 领取体力 | `DailyFriendStaminaStart` | 低   | [领取体力](daily_friend_stamina.md) |
| 炼金订单 | `DailyAlchemyOrdersStart` | 中   | [炼金订单](daily_alchemy_orders.md) |
| 每日派遣 | `DailyDispatchStart`      | 中   | [每日派遣](daily_dispatch.md)       |
| 消耗体力 | `DailyStaminaStart`       | 高   | [消耗体力](daily_stamina.md)        |
| 调教     | `DailyTrainingStart`      | 高   | [调教](daily_training.md)           |
| 全境征才 | `DailyRecruitmentStart`   | 高   | [全境征才](daily_recruitment.md)    |
| 奖励领取 | `DailyTaskRewardsStart`   | 低   | [奖励领取](daily_task_rewards.md)   |
| 自动战斗 | `AutoBattleStart`         | 高   | [自动战斗](auto_battle.md)          |

详细 OCR、ROI、节点名和素材路径只在对应任务文档的实现映射中维护。

加载等待、礼包关闭与主界面恢复见 [公共主界面恢复](common_navigation.md)。
