# 启动游戏（GameLogin）

入口节点：`GameLoginStart`；实现文件：`assets/resource/pipeline/game_login.json`。

## 背景说明

官服与 erolab 服务器提供相同的游戏内容、页面布局和登录流程，因此共用同一套登录 Pipeline。两者的
发行渠道和 Android 包名不同：官服使用 `com.pinkcore.tkfm`，erolab 使用
`com.pinkcore.tkfm.erolabs`；任务选项“选择服务器”仅通过 Interface Override 切换启停应用使用的包名。

## 前置状态

- 模拟器已安装所选服务器对应的游戏包，并允许从主界面启动应用。
- 在任务选项“选择服务器”中确认包名：工口服务器为 `com.pinkcore.tkfm`，erolab 服务器为 `com.pinkcore.tkfm.erolabs`。

## 主流程

1. 关闭已运行的游戏应用，再启动所选服务器的游戏包。
2. 启动后进入统一状态分发器，按当前画面处理加载、资源检查、公告、标题页、首登弹窗、礼包和主界面。
3. 通过 `TAP TO START` 或版本号确认标题页后点击进入游戏，再返回同一状态分发器识别点击后的新页面；
   点击未生效时由同一节点限频、有限次重试。
4. 当日首次登录时，依次点击活动登录奖励和常规签到页底部的 `TOUCH SCREEN`，再关闭标题页后的
   王城公布栏。同日再次登录时这些页面均可能不出现。
5. 进入每次登录都会出现的 STEP 礼包页，通过左上角返回按钮回到状态分发器；识别主界面后结束任务。

## 页面识别

| 页面状态   | 识别目标                             | 识别方式  | 动作                         |
| ---------- | ------------------------------------ | --------- | ---------------------------- |
| 资源检查   | `资源检查中`或`档案读取中`           | OCR       | 等待并返回所属状态分发器     |
| 启动加载   | `LOADING`/`LOAD ING`                 | OCR       | 等待并返回所属状态分发器     |
| 王城公布栏 | `王城公布栏`、`活动公告`或`最新公告` | OCR       | 点击底部关闭区域             |
| 标题页     | `TAP TO START` 或版本号              | OCR       | 点击底部进入区域             |
| 活动签到   | `挑战奖励`、`LOGIN REWARDS`或`UTC+8` | OCR       | 点击底部 `TOUCH SCREEN` 区域 |
| 常规签到   | `奖励已送至仓库`、每日获得或签到文本 | OCR       | 点击底部 `TOUCH SCREEN` 区域 |
| STEP 礼包  | `STEP`、限时、精选或月卡页签         | OCR       | 点击左上角返回区域           |
| 主界面     | 出征与调教同时存在                   | And + OCR | `GameMainReady` 停止任务     |

## 异常与分支

- 2026-07-15 双轮实测中，标题页前王城公布栏、活动登录奖励、常规签到和标题页后王城公布栏只在
  当日首次登录出现；同日再次登录从标题页后的资源检查直接进入 STEP 礼包页。
- STEP 礼包页在两轮登录中都出现，属于每次登录主流程；活动签到、常规签到或公告未出现时不应等待
  固定顺序，而应继续判断礼包页和主界面。
- `GameLoginDispatch` 是唯一状态分发器，显式使用 `DirectHit + DoNothing`，在 360 秒总预算内根据当前
  画面选择处理节点，不用节点调用链表达页面阶段。
- 加载、资源检查、首登弹窗、公告、礼包和标题点击全部通过 `[JumpBack]` 返回状态分发器。会改变页面的
  动作节点不再配置自己的 `next`，避免点击后框架继续以旧页面节点为当前 PipelineNode。
- 标题页不使用通用的 `TOUCH SCREEN` 识别，避免签到页被当成标题页。活动签到、常规签到和礼包先用
  页面特征 OCR 确认，再点击该页面固定且稳定的底部或左上角区域，不依赖组合识别返回框。
- 标题页点击后不要求再次识别 `TAP TO START`；状态分发器会直接识别加载、资源检查、首登弹窗、公告、
  礼包或主界面。仍停留标题页时才会再次命中标题节点。
- 标题点击共允许命中 5 次，并设置 2 秒 `rate_limit`；主界面识别排在其他页面处理之后。
- 网络错误、服务器维护或资源更新页面目前没有专用恢复节点，出现时应安全停止并补充流程记录。

## 完成状态

- 成功条件：`GameMainReady` 命中并停止任务。
- 安全退出位置：游戏主界面；无法识别已知页面时不得盲点继续。

## 验证记录

- 2026-07-14：根据导入的历史说明和当前 Pipeline 整理，未重新运行模拟器。
- 2026-07-14，客户端 `Ver.2.2.1`，MuMuPlayer v5+，工口服务器：人工完成桌面启动、资源检查、
  标题页、王城公布栏、STEP 礼包页和主界面路径，最终同时识别到“出征”和“调教”。本轮不是当日首次
  登录，标题页前的每日公告、活动签到和常规签到未自动出现；标题页后的登录公告正常出现。未出现的
  页面按条件分支待后续覆盖，不计为流程失败。
- 2026-07-14 Pipeline 测试：`GameTapTitleScreen` 成功识别 `TAPTO START` 并点击 `(360, 1135)`，但旧实现
  随后通过 `[JumpBack]GameTapTitleScreen` 递归调用同名节点，直至人工停止。
- 2026-07-15，客户端 `Ver.2.2.1`，MuMuPlayer v5+，官服：完成当日首次登录和同日再次登录两轮人工
  采集。首轮实际顺序为标题页前王城公布栏、标题页、资源检查、活动登录奖励、常规签到、标题页后
  王城公布栏、STEP 礼包页、主界面；第二轮为资源检查、标题页、资源检查、STEP 礼包页、主界面。
- 2026-07-15 旧 Pipeline 复测：`run_pipeline` 运行 300 秒仍未返回 TaskDetail，`stop_pipeline` 也因任务
  占用而超时。根据现场和节点关系确认标题页、礼包页的自递归及首登页面动作错误会导致流程挂起，
  随后改为独立标题重试和统一的标题页后状态循环。
- 2026-07-15 修复后 Pipeline 复测：从模拟器桌面运行 `GameLoginStart`，自动完成同日再次登录并到达
  主界面，重新连接后同时识别到“出征”和“调教”；`stop_pipeline` 在 4.8 秒内完成清理，MaaMCP 未再次
  死锁。`run_pipeline` 结束时因 MCP 返回层缺少结构化输出而报校验错误，因此本轮以最终画面确认行为
  通过，未取得可用的 TaskDetail 状态。
- 2026-07-15 VS Code Maa Support 插件日志：插件使用 MaaFramework `v5.9.0-alpha.4`，`GameLoginLaunch`
  执行 `StartApp` 后画面由 `1280x720` 切换为 `720x1280`，冻结检测比较不同尺寸的前后帧并报
  `lhs_image_.size() != rhs_image_.size()`。已移除启停应用节点上的 `post_wait_freezes`，改由后续页面
  状态识别等待游戏就绪。
- 2026-07-15 插件标题页复测：`GameTapTitleScreen` 成功识别和点击，但插件在扫描其唯一下一节点时未
  触发任何子节点识别，直至人工停止。已为标题后状态循环补充显式 `DirectHit + DoNothing`，并移除
  标题点击、标题重试和资源检查节点上不承担页面确认职责的冻结等待。
- 2026-07-15 中间版本复测：将标题页前后候选拆入独立状态分发器，并为启停应用节点补充显式
  `DirectHit`。现场基准确认 `Or`/`And` 组合识别会返回空结果框，未包含在当前识别图中的命名点击目标
  也不会在动作阶段重新识别；因此标题、首登弹窗和礼包均改为单次页面 OCR 后点击稳定坐标。礼包完成
  后单向进入 `GameLoginAwaitMain`，避免返回父状态和重复扫描全部候选。
- 2026-07-15，客户端 `Ver.2.2.1`，MuMuPlayer v5+，erolab 服务器：使用
  `com.pinkcore.tkfm.erolabs` 临时 Override 完成当日首次登录验证。实际覆盖活动登录奖励、常规签到、
  标题页后公告、STEP 礼包和主界面；`GameCloseEventSignIn`、`GameCloseSignIn`、
  `GameCloseAnnouncement` 和 `GameCloseGift` 单节点均返回 `status: succeeded`。同日再次从应用启动入口
  运行完整链路，最终同时识别到“出征”和“调教”。MaaMCP 返回层仍因缺少结构化输出报校验错误，已在
  画面确认后调用 `stop_pipeline` 清理任务。首次登录各页面与下方已有截图一致。
- 2026-07-15 MaaFramework 日志复核：`GameTapTitleScreen` 于 `16:57:20.719` 点击成功，但框架随后继续以
  `GameTapTitleScreen` 启动后续 PipelineNode，直到 `17:03:56.813` 才失败。根因是会改变页面的标题节点
  仍通过自身 `next` 尝试跨阶段；点击后旧页面识别条件已经消失。现改为单一 `GameLoginDispatch`，标题、
  弹窗和礼包均以 `[JumpBack]` 处理，动作完成后直接按新画面重新分发。
- 2026-07-15 单一状态分发器复测：从 STEP 礼包页运行 `GameLoginDispatch`，自动关闭礼包并到达主界面；
  随后从应用启动入口运行 `GameLoginStart`，完成标题点击、登录后页面处理和礼包返回，最终同时识别到
  “出征”和“调教”。MaaMCP 返回层仍因缺少结构化输出报校验错误，已在画面确认后清理任务。
- 2026-07-15 中断复测时实际出现“网路连线不稳定，请稍后重试”、`GetCDN_SomeError` 和“重新连线”
  按钮；当前 Pipeline 未处理该页面，本次重构不在未经复现验证的情况下增加自动点击，保留为待验证分支。
- 待验证：礼包的其他出现顺序，以及网络错误、服务器维护和资源更新异常页面。

## 实测截图

官服与 erolab 的页面内容和布局一致，以下首次登录与同日再次登录截图适用于两个服务器。

### 2026-07-15 当日首次登录

| 顺序 | 页面状态     | 截图                                                                                                      | 实测识别依据                            |
| ---- | ------------ | --------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| 1    | 模拟器桌面   | [01-emulator-desktop.png](images/game_login/2026-07-15-first-login/01-emulator-desktop.png)               | 右侧非 EROLABS 的“天下布魔”图标         |
| 2    | 启动画面     | [02-launch-splash.png](images/game_login/2026-07-15-first-login/02-launch-splash.png)                     | `PINK CORE`/`SCArts`                    |
| 3    | 标题页前公告 | [03-pre-title-announcement.png](images/game_login/2026-07-15-first-login/03-pre-title-announcement.png)   | `王城公布栏`、`魔王城情报联播网`        |
| 4    | 标题页       | [04-title-screen.png](images/game_login/2026-07-15-first-login/04-title-screen.png)                       | `TAP TO START`、`Ver.2.2.1`             |
| 5    | 资源检查     | [05-resource-check.png](images/game_login/2026-07-15-first-login/05-resource-check.png)                   | `资源检查中`                            |
| 6    | 活动登录奖励 | [06-event-login-reward.png](images/game_login/2026-07-15-first-login/06-event-login-reward.png)           | `挑战奖励`、`UTC+8`、`TOUCH SCREEN`     |
| 7    | 常规签到     | [07-daily-sign-in.png](images/game_login/2026-07-15-first-login/07-daily-sign-in.png)                     | `7月`、`奖励已送至仓库`、`TOUCH SCREEN` |
| 8    | 标题页后公告 | [08-post-title-announcement.png](images/game_login/2026-07-15-first-login/08-post-title-announcement.png) | `王城公布栏`、活动公告/最新公告         |
| 9    | STEP 礼包页  | [09-gift-screen.png](images/game_login/2026-07-15-first-login/09-gift-screen.png)                         | 返回按钮、STEP/限时/精选/月卡           |
| 10   | 主界面       | [10-main-screen.png](images/game_login/2026-07-15-first-login/10-main-screen.png)                         | “出征”和“调教”同时存在                  |

### 2026-07-15 同日再次登录

| 顺序 | 页面状态     | 截图                                                                                                           | 与首轮对照                        |
| ---- | ------------ | -------------------------------------------------------------------------------------------------------------- | --------------------------------- |
| 1    | 模拟器桌面   | [01-emulator-desktop.png](images/game_login/2026-07-15-repeat-login/01-emulator-desktop.png)                   | 相同官服入口                      |
| 2    | 启动资源检查 | [02-resource-check.png](images/game_login/2026-07-15-repeat-login/02-resource-check.png)                       | 启动阶段出现 `资源检查中`         |
| 3    | 标题页       | [03-title-screen.png](images/game_login/2026-07-15-repeat-login/03-title-screen.png)                           | 标题页前公告未出现                |
| 4    | 标题页后检查 | [04-post-title-resource-check.png](images/game_login/2026-07-15-repeat-login/04-post-title-resource-check.png) | 点击标题页后再次出现 `资源检查中` |
| 5    | STEP 礼包页  | [05-gift-screen.png](images/game_login/2026-07-15-repeat-login/05-gift-screen.png)                             | 首登奖励、签到和公告均未出现      |
| 6    | 主界面       | [06-main-screen.png](images/game_login/2026-07-15-repeat-login/06-main-screen.png)                             | 与首轮相同的结束状态              |

### 2026-07-15 修复后 Pipeline

| 页面状态 | 截图                                                                                                                          | 验证结果                     |
| -------- | ----------------------------------------------------------------------------------------------------------------------------- | ---------------------------- |
| 主界面   | [01-main-screen-after-fixed-pipeline.png](images/game_login/2026-07-15-pipeline-test/01-main-screen-after-fixed-pipeline.png) | 自动登录后命中“出征”和“调教” |
