# 商城购买（DailyShop）验证记录

本文件记录商城购买（DailyShop）的实机验证、调试与覆盖状态，入口节点 `DailyShopStart`；流程、识别依据和限制见 [商城购买（DailyShop）](../tasks/daily_shop.md)。

## 覆盖状态

- 主流程：已实现，详细流程以当前 Pipeline 为准。
- 高风险路径：真实购买、货币不足和购买结果弹窗仍待验证。
- 返回主界面后的全屏稳定等待已移除，修复后的返回耗时待设备复测。

## 验证记录

- 2026-09-13 实机验证：目标商品设置为不存在名称，完成交易所与协会商店顶部/底部扫描并返回主界面，未发生购买或货币变化；验证无可处理内容和安全退出。

### 2026-09-13 商城返回等待排查

- 证据：本机 `E:/TKFM/debug/maafw.log`，资源版本 `v1.0.4-beta.1`，MaaFramework 5.13.0，设备为 MuMuPlayer v5+；本次日志未确认游戏客户端版本。
- `DailyShopReturnMain` 在 20:36:27.223 开始点击后的全屏稳定等待，要求全屏连续稳定 700ms；20:36:47.561 记录 `Node.WaitFreezes.Failed`，实际等待 20337ms。
- 随后 `CommonStopOnMain` 同时识别到“出征”和“调教”，20:36:49.212 记录 `Tasker.Task.Succeeded`。因此长停顿发生在全屏稳定等待，任务最终仍以成功结束。
- 修复移除该节点的 `post_wait_freezes`，保留 `pre_wait_freezes: 300` 和已有的主界面结束确认。maa-tools、Pipeline/Interface Schema、Prettier、体力配置同步和交互稳定性检查通过。
- 本轮设备检查时征才页面仍在变化，为避免并发操作已暂停设备验证；尚未复测修复后的商城返回耗时，也未重新执行购买或货币不足分支。
