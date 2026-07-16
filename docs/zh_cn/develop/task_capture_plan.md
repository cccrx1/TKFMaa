# 任务页面采集计划

本文用于跟踪 TKFMaa 各任务的模拟器页面截图和实机验证进度。流程事实仍记录在 `docs/zh_cn/task_flows/task_*.md`；本表只管理采集范围和完成状态。

## 状态说明

- **未开始**：尚未基于当前客户端采集。
- **采集中**：已采集部分主流程，仍有关键页面或分支缺失。
- **主流程完成**：主流程截图齐全，异常分支可能仍待补充。
- **完成**：主流程、可复现的关键分支和安全退出均已记录。
- 没有实际出现的可选弹窗标记为“未覆盖”，不得用旧图或推测替代。

## 任务总表

| 顺序 | 任务     | 入口节点                  | 计划采集的关键状态                                             | 风险 | 截图状态   | 实机验证         | 流程文档                                                                     |
| ---- | -------- | ------------------------- | -------------------------------------------------------------- | ---- | ---------- | ---------------- | ---------------------------------------------------------------------------- |
| 1    | 启动游戏 | `GameLoginStart`          | 桌面、资源检查、首登公告/签到、标题页、礼包、主界面            | 低   | 主流程完成 | 修复后行为通过   | [`task_game_login.md`](../task_flows/task_game_login.md)                     |
| 2    | 领取体力 | `DailyFriendStaminaStart` | 主界面、玩家信息、好友加载、有/无一键领取、返回主界面          | 低   | 未开始     | 未开始           | [`task_daily_friend_stamina.md`](../task_flows/task_daily_friend_stamina.md) |
| 3    | 奖励领取 | `DailyTaskRewardsStart`   | 任务入口、六个页签、有/无可领取、奖励弹窗、返回主界面          | 低   | 未开始     | 未开始           | [`task_daily_task_rewards.md`](../task_flows/task_daily_task_rewards.md)     |
| 4    | 炼金订单 | `DailyAlchemyOrdersStart` | 左侧抽屉、炼金页、一键收取、可交付订单、奖励弹窗、返回         | 中   | 未开始     | 未开始           | [`task_daily_alchemy_orders.md`](../task_flows/task_daily_alchemy_orders.md) |
| 5    | 每日派遣 | `DailyDispatchStart`      | 抽屉栏位、总览、归来弹窗、地点/时间、自动/手动编队、出发       | 中   | 未开始     | 未开始           | [`task_daily_dispatch.md`](../task_flows/task_daily_dispatch.md)             |
| 6    | 商城购买 | `DailyShopStart`          | 商城入口、交易所、协会商店、商品详情、购买确认、不足提示、奖励 | 高   | 未开始     | 未开始           | [`task_daily_shop.md`](../task_flows/task_daily_shop.md)                     |
| 7    | 调教     | `DailyTrainingStart`      | 次数状态、筛选面板、可调教房间、道具栏、执行页、不足弹窗       | 高   | 未开始     | 未开始           | [`task_daily_training.md`](../task_flows/task_daily_training.md)             |
| 8    | 全境征才 | `DailyRecruitmentStart`   | 召唤入口、四栏总览、词条、时间、开始招募、结果、立即招募       | 高   | 未开始     | 未开始           | [`task_daily_recruitment.md`](../task_flows/task_daily_recruitment.md)       |
| 9    | 消耗体力 | `DailyStaminaStart`       | 出征、活动选择、关卡列表、详情、扫荡、补充体力、战斗、结算     | 高   | 采集中     | 常规活动部分通过 | [`task_daily_stamina.md`](../task_flows/task_daily_stamina.md)               |

风险为“高”的任务会消耗货币、体力、招募资源或珍贵道具。采集到最终确认页后必须暂停，由用户确认是否继续。

## 启动游戏采集记录

### 当日首次登录

| 序号 | 页面状态     | 截图路径                                                                                                                  | 识别目标与方式                        | 分支类型 | 状态   |
| ---- | ------------ | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- | -------- | ------ |
| 1    | 模拟器桌面   | [`01-emulator-desktop.png`](../task_flows/images/game_login/2026-07-15-first-login/01-emulator-desktop.png)               | 右侧非 EROLABS 游戏图标，视觉         | 主流程   | 已采集 |
| 2    | 启动画面     | [`02-launch-splash.png`](../task_flows/images/game_login/2026-07-15-first-login/02-launch-splash.png)                     | `PINK CORE`/`SCArts`，OCR             | 主流程   | 已采集 |
| 3    | 标题页前公告 | [`03-pre-title-announcement.png`](../task_flows/images/game_login/2026-07-15-first-login/03-pre-title-announcement.png)   | `王城公布栏`，OCR                     | 首登分支 | 已采集 |
| 4    | 标题页       | [`04-title-screen.png`](../task_flows/images/game_login/2026-07-15-first-login/04-title-screen.png)                       | `TAP TO START`/版本号，OCR            | 主流程   | 已采集 |
| 5    | 资源检查     | [`05-resource-check.png`](../task_flows/images/game_login/2026-07-15-first-login/05-resource-check.png)                   | `资源检查中`，OCR                     | 主流程   | 已采集 |
| 6    | 活动登录奖励 | [`06-event-login-reward.png`](../task_flows/images/game_login/2026-07-15-first-login/06-event-login-reward.png)           | `挑战奖励` + `TOUCH SCREEN`，And/OCR  | 首登分支 | 已采集 |
| 7    | 常规签到     | [`07-daily-sign-in.png`](../task_flows/images/game_login/2026-07-15-first-login/07-daily-sign-in.png)                     | `奖励已送至仓库` + `TOUCH SCREEN`     | 首登分支 | 已采集 |
| 8    | 标题页后公告 | [`08-post-title-announcement.png`](../task_flows/images/game_login/2026-07-15-first-login/08-post-title-announcement.png) | `王城公布栏`，OCR                     | 首登分支 | 已采集 |
| 9    | STEP 礼包页  | [`09-gift-screen.png`](../task_flows/images/game_login/2026-07-15-first-login/09-gift-screen.png)                         | 返回按钮 + 顶部页签，And/Template/OCR | 主流程   | 已采集 |
| 10   | 主界面       | [`10-main-screen.png`](../task_flows/images/game_login/2026-07-15-first-login/10-main-screen.png)                         | 出征与调教，And/OCR                   | 结束     | 已采集 |

### 同日再次登录

| 序号 | 页面状态     | 截图路径                                                                                                                       | 与首轮对照           | 状态   |
| ---- | ------------ | ------------------------------------------------------------------------------------------------------------------------------ | -------------------- | ------ |
| 1    | 模拟器桌面   | [`01-emulator-desktop.png`](../task_flows/images/game_login/2026-07-15-repeat-login/01-emulator-desktop.png)                   | 相同官服入口         | 已采集 |
| 2    | 启动资源检查 | [`02-resource-check.png`](../task_flows/images/game_login/2026-07-15-repeat-login/02-resource-check.png)                       | 启动阶段出现资源检查 | 已采集 |
| 3    | 标题页       | [`03-title-screen.png`](../task_flows/images/game_login/2026-07-15-repeat-login/03-title-screen.png)                           | 标题页前公告未出现   | 已采集 |
| 4    | 标题页后检查 | [`04-post-title-resource-check.png`](../task_flows/images/game_login/2026-07-15-repeat-login/04-post-title-resource-check.png) | 点击标题页后再次检查 | 已采集 |
| 5    | STEP 礼包页  | [`05-gift-screen.png`](../task_flows/images/game_login/2026-07-15-repeat-login/05-gift-screen.png)                             | 首登弹窗均未出现     | 已采集 |
| 6    | 主界面       | [`06-main-screen.png`](../task_flows/images/game_login/2026-07-15-repeat-login/06-main-screen.png)                             | 与首轮相同的结束状态 | 已采集 |

| 日期       | 客户端版本 | 模拟器/设备    | 分辨率                       | 服务器     | 操作者 |
| ---------- | ---------- | -------------- | ---------------------------- | ---------- | ------ |
| 2026-07-14 | Ver.2.2.1  | MuMuPlayer v5+ | 桌面 1280x720；游戏 720x1280 | 工口服务器 | Codex  |
| 2026-07-15 | Ver.2.2.1  | MuMuPlayer v5+ | 桌面 1280x720；游戏 720x1280 | 官服       | Codex  |

2026-07-15 首轮出现标题页前公告、活动登录奖励、常规签到和标题页后公告，第二轮均未再次出现，因此记录为
本次实测的当日首登分支。STEP 礼包页和主界面两轮均出现。erolab 服务器、网络异常及其他礼包顺序仍待验证。

修复后的 `GameLoginStart` 已从模拟器桌面自动运行到主界面；最终截图见
[`01-main-screen-after-fixed-pipeline.png`](../task_flows/images/game_login/2026-07-15-pipeline-test/01-main-screen-after-fixed-pipeline.png)。

## 消耗体力采集记录

### 自动通关路线

| 序号 | 页面状态           | 触发操作               | 截图路径                                                                                                                                              | 识别目标与方式                        | 分支类型 | 状态   |
| ---- | ------------------ | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- | -------- | ------ |
| 1    | 游戏主界面         | 无                     | [`01-main-screen.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/01-main-screen.png)                                                   | `出征`、顶部体力，OCR                 | 主流程   | 已采集 |
| 2    | 出征首页           | 点击“出征”             | [`02-expedition-home.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/02-expedition-home.png)                                           | `目前活动`、`限时活动`，OCR           | 主流程   | 已采集 |
| 3    | 常规活动本体选择页 | 选择 `Idol Live`       | [`03-regular-activity-selection-idol-live.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/03-regular-activity-selection-idol-live.png) | 活动名、`进击`，OCR                   | 主流程   | 已采集 |
| 4    | 常规活动第一页     | 点击“进击”             | [`04-regular-activity-page-1.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/04-regular-activity-page-1.png)                           | 活动标题、关卡名、`NEXT!`，OCR        | 主流程   | 已采集 |
| 5    | 常规活动第二页     | 点击 `NEXT!`           | [`05-regular-activity-page-2-new.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/05-regular-activity-page-2-new.png)                   | `直播-04` 上方 `NEW`，TemplateMatch   | 主流程   | 已采集 |
| 6    | 直播-04详情页      | 点击 `NEW` 对应关卡    | [`06-regular-activity-live-04-detail.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/06-regular-activity-live-04-detail.png)           | `stage直播-04`、`开始`、体力消耗 30   | 高风险   | 已采集 |
| 7    | 战前剧情           | 点击“开始”             | [`07-pre-battle-story.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/07-pre-battle-story.png)                                         | `REC`/`SKIP`，OCR                     | 主流程   | 已采集 |
| 8    | 跳过剧情确认       | 点击 `SKIP`            | [`08-skip-story-confirmation.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/08-skip-story-confirmation.png)                           | `确定跳过事件吗`、`确定`，OCR         | 主流程   | 已采集 |
| 9    | 战斗结算           | AUTO 完成战斗          | [`09-battle-clear-result.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/09-battle-clear-result.png)                                   | `CLEAR`、`返回地图`、顶部体力         | 主流程   | 已采集 |
| 10   | 返回地图后的下一关 | 点击“返回地图”         | [`10-return-map-next-new.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/10-return-map-next-new.png)                                   | 下一关 `NEW`，TemplateMatch           | 主流程   | 已采集 |
| 11   | 战后剧情           | 完成后返回地图         | [`11-post-battle-story.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/11-post-battle-story.png)                                       | `REC`/`SKIP`，OCR                     | 分支     | 已采集 |
| 12   | 另一战前剧情       | 点击“开始”             | [`12-immediate-after-start.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/12-immediate-after-start.png)                               | `REC`/`SKIP`，视觉/OCR                | 分支     | 已采集 |
| 13   | AUTO 战斗中        | 确认跳过剧情           | [`13-battle-auto-active.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/13-battle-auto-active.png)                                     | `WAVE`、`TURN`、高亮 `AUTO`           | 主流程   | 已采集 |
| 14   | 魔晶石体力确认页   | 体力不足时点击“开始”   | [`14-stamina-refill-currency-confirmation.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/14-stamina-refill-currency-confirmation.png) | 300 魔晶石兑换 120 体力、剩余次数     | 高风险   | 已采集 |
| 15   | 道具体力空状态     | 切换“使用道具回复”     | [`15-stamina-refill-potion-empty.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/15-stamina-refill-potion-empty.png)                   | `目前没有任何的药水可供使用`，OCR     | 异常     | 已采集 |
| 16   | 购买成功后刷新弹窗 | 确认购买一次           | [`16-after-currency-purchase.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/16-after-currency-purchase.png)                           | 体力 130→250、剩余 24 次、魔晶石 6110 | 高风险   | 已采集 |
| 17   | 购买后关卡详情     | 点击“取消”关闭刷新弹窗 | [`17-purchase-popup-closed-stage-detail.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/17-purchase-popup-closed-stage-detail.png)     | 顶部体力 131、重新出现“开始”          | 主流程   | 已采集 |
| 18   | 购买后战斗结算     | 再次点击“开始”         | [`18-post-purchase-battle-clear.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/18-post-purchase-battle-clear.png)                     | `CLEAR`、顶部体力 101                 | 主流程   | 已采集 |
| 19   | 安全退出主界面     | 返回地图并逐级返回     | [`19-main-screen-safe-exit.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/19-main-screen-safe-exit.png)                               | `出征`、顶部体力，OCR                 | 结束     | 已采集 |
| 20   | 常规活动第三页下方 | 从上方向下浏览         | [`20-regular-page-3-lower-view.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/20-regular-page-3-lower-view.png)                       | `话题-03` 至 `擦边-03`，OCR           | 主流程   | 已采集 |
| 21   | 常规活动第三页上方 | 从下方向上浏览         | [`21-regular-page-3-upper-view-new.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/21-regular-page-3-upper-view-new.png)               | `直播-07/08/09`、`NEW`，OCR           | 主流程   | 已采集 |
| 22   | 第三页下扫节点结果 | 执行向下扫描节点       | [`22-regular-page-3-after-scan-down-node.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/22-regular-page-3-after-scan-down-node.png)   | 仍在关卡列表且未误点，OCR             | 主流程   | 已采集 |
| 23   | 第三页上扫节点结果 | 执行向上扫描节点       | [`23-regular-page-3-after-scan-up-node.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/23-regular-page-3-after-scan-up-node.png)       | 顶部 `NEW`，TemplateMatch 素材来源    | 主流程   | 已采集 |
| 24   | 直播-07 返回地图   | AUTO 通关并返回地图    | [`24-regular-page-3-after-live-07-clear.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/24-regular-page-3-after-live-07-clear.png)     | `直播-08` 成为下一枚 `NEW`            | 高风险   | 已采集 |
| 25   | AUTO 关闭态        | 切为 1x 并关闭 AUTO    | [`25-regular-auto-off-capture.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/25-regular-auto-off-capture.png)                         | `WAVE`/`TURN`、灰色 `AUTO` 模板       | 高风险   | 已采集 |
| 26   | 全部通关后主界面   | 空跑扫描并安全退出     | [`26-regular-final-main-screen.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/26-regular-final-main-screen.png)                       | `出征`、无额外资源消耗，OCR           | 结束     | 已采集 |
| 27   | 有药的体力回复弹窗 | 已通关关卡体力不足     | [`27-stamina-refill-potion-available.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/27-stamina-refill-potion-available.png)           | 临期批次、数量 1、初级药回复 60，OCR  | 高风险   | 已采集 |

### 挑战活动未适配分支

| 页面状态         | 截图路径                                                                                                                                | 说明                         |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- |
| 挑战活动选择页   | [`03a-challenge-activity-selection.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/03a-challenge-activity-selection.png) | 活动开放数天后的附加入口     |
| 挑战活动关卡地图 | [`03b-challenge-stage-list.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/03b-challenge-stage-list.png)                 | 不属于当前自动通关适配范围   |
| 挑战活动关卡详情 | [`03c-challenge-stage-detail.png`](../task_flows/images/daily_stamina/2026-07-15-auto-clear/03c-challenge-stage-detail.png)             | 未执行会消耗体力的“开始”动作 |

| 日期       | 客户端版本 | 模拟器/设备    | 分辨率   | 服务器 | 操作者 |
| ---------- | ---------- | -------------- | -------- | ------ | ------ |
| 2026-07-15 | Ver.2.2.1  | MuMuPlayer v5+ | 720x1280 | 官服   | Codex  |
| 2026-07-16 | Ver.2.2.1  | MuMuPlayer v5+ | 720x1280 | 官服   | Codex  |

活动栏位本体分为常规活动、复刻活动和大型活动，当前采集的是常规活动 `Idol Live`。活动开放数天后出现的
挑战活动是附加入口，暂不在自动通关适配范围内。常规活动第一页没有 `NEW` 时可通过 `NEXT!` 进入第二页，
第二页 `直播-04` 的 `NEW` 位于现有候选 ROI 内并能进入正确详情页。战前和战后剧情均可通过 `SKIP`
加确认跳过。战斗中会识别灰色 AUTO 关闭态并仅在关闭时点击开启；实测从关闭态重新开启后无需输入即可完成。结算页顶部体力可见，
返回地图后能继续识别下一关 `NEW`。体力不足时魔晶石页本次报价为 300 魔晶石兑换 120 体力，
今日剩余 25 次；道具页空状态和有药状态均已采集。实测购买一次后体力增加、魔晶石和剩余次数正确扣减，但弹窗不会自动关闭，
而是刷新为下一次购买确认；点击“取消”后返回关卡详情，还需再次点击“开始”才会继续战斗。完整任务已清空第三页 `NEW`，再次空跑没有消耗体力并返回主界面。
复刻活动和大型活动本体仍待分别采集验证。

2026-07-16 使用已通关 `擦边-02` 消耗体力后采集有药分支。药品按过期时间排序，同日期同档位合并库存；实测默认选中 3 天后到期的初级药，确认 1 瓶回复 60，弹窗刷新后默认选中 10 天后到期的上级药并显示回复 100。流程据此采用逐瓶确认和关卡重试，不自行打乱游戏的临期顺序。

第三页上下视口展示不同关卡，确认常规活动单页需要纵向滑动才能覆盖全部关卡。自动通关扫描已按手动指定关卡搜索的坐标和方向补充为有限的向下、向上节点链；截图 20/21 用于对照同一页的下方和上方内容。

## 单任务采集表

开始一个任务时复制下表，按实际页面顺序填写。建议将筛选后的说明截图保存到 `docs/zh_cn/task_flows/images/<task>/`；用于 TemplateMatch 的无损裁剪仍放在 `assets/resource/image/`。

| 序号 | 页面状态   | 触发操作 | 截图路径 | 识别目标与方式 | 分支类型         | 状态   |
| ---- | ---------- | -------- | -------- | -------------- | ---------------- | ------ |
| 1    | 任务起始页 | 无       |          |                | 主流程           | 未采集 |
| 2    |            |          |          |                | 主流程/异常/结束 | 未采集 |

同时记录本次环境：

| 日期 | 客户端版本 | 模拟器/设备 | 分辨率        | 服务器 | 操作者 |
| ---- | ---------- | ----------- | ------------- | ------ | ------ |
|      |            |             | 720x1280 基准 |        |        |

## 完成检查

- [ ] 主流程每个不同页面状态至少有一张有效截图。
- [ ] OCR、TemplateMatch、ColorMatch 或 Custom 的关键识别依据已记录。
- [ ] 高风险确认页已暂停并由用户决定是否继续。
- [ ] 已出现的加载、空状态、资源不足和错误弹窗均有记录。
- [ ] 成功状态和安全退出位置已确认。
- [ ] 截图不包含账号隐私，文档图与识别素材用途没有混淆。
- [ ] 对应任务文档的页面识别、异常分支和验证记录已同步更新。
