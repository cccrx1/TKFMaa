# 公共主界面恢复

实现文件：`assets/resource/pipeline/common.json`、`assets/resource/pipeline/common_return.json`。
入口节点：`CommonEnsureMain`；任务结束确认：`CommonStopOnMainWithRetries`。

## 实机依据

登录后可能出现包含“限时 / 精选 / 月卡”页签的礼包，左上角返回可关闭，原公共恢复流程无法处理。

## 页面流程

恢复入口与任务结束确认用途不同，分别如下。

```mermaid
flowchart TD
    Start[CommonEnsureMain 恢复入口] --> Check{按优先级识别当前页面}
    Check -->|正在加载| Wait[等待 500 毫秒]
    Wait --> Check
    Check -->|礼包页签，未达 3 次上限| Gift[点击左上角关闭礼包]
    Gift --> Check
    Check -->|奖励确认按钮| Reward[关闭奖励弹窗]
    Reward --> Check
    Check -->|出征与调教同时存在| Return[返回父流程继续任务]
    Check -->|商店、任务页或玩家信息页| Back[识别对应返回按钮并点击]
    Back --> Verify{识别返回后的页面}
    Verify -->|加载或礼包| Handle[等待加载或关闭礼包后复查]
    Handle --> Verify
    Verify -->|主界面| Return
    Verify -->|候选识别超时| Fail[恢复失败，交由调用方处理]
    Check -->|其他已配置页面| Legacy[执行已有返回动作并交回父流程]
    Check -->|候选识别超时| Fail
```

商店、任务页、玩家信息页的返回节点显式连接主界面确认，候选列表超时为 10 秒。
`CommonEnsureMain` 本身的候选列表超时为 8 秒，失败时如何处理由调用方决定。

```mermaid
flowchart TD
    Start[CommonStopOnMainWithRetries 结束入口] --> Check{检查加载、礼包、主界面}
    Check -->|加载文字命中| Wait[等待 500 毫秒]
    Wait --> Check
    Check -->|礼包命中且未达上限| Gift[关闭礼包]
    Gift --> Check
    Check -->|主界面命中| Done[CommonStopOnMain 停止整个任务]
    Check -->|尚未命中，仍有复查阶段| Retry[进入下一阶段，间隔 300 毫秒]
    Retry --> Check
    Check -->|已用尽 3 个复查阶段| Final[在最后阶段继续识别加载、礼包或主界面]
    Final -->|加载或礼包| Handle[处理后留在最后阶段复查]
    Handle --> Final
    Final -->|主界面命中| Done
    Final -->|候选识别超时| Fail[结束确认失败，不认定任务完成]
```

三个复查阶段对应 `CommonStopOnMainWait1/2/3`；每阶段候选列表超时为 10 秒，
并非整个任务只等待 900 毫秒或固定 10 秒。结束入口没有任意页面返回动作，也没有普通奖励弹窗处理分支。

- `CommonEnsureMain` 优先处理加载、礼包和奖励确认，再识别主界面，避免已在主界面时多点一次“城堡”。
- 礼包用 `__CommonGiftTabs` 识别 `[100, 95, 530, 75]` 内的完整页签文字，
  `CommonCloseMainGift` 点击 `[40, 75]`，最多 3 次；点击后重新检查页面，不点击购买区。
- 商店底栏、玩家信息和任务页的返回动作取消全屏稳定等待，由目标主界面识别承接页面切换。
- `CommonWaitLoading` 的 ROI 为 `[180, 1158, 360, 92]`，完整覆盖底部加载提示；匹配 `LOADING`、
  `CONNECTING` 并兼容字母间空格。仅在文字命中时等待 500 毫秒再复查，不要求整屏静止。
- 结束重试节点使用短间隔复查，并允许处理加载和礼包。最后必须识别主界面，不能只因点击发出而结束。
- 点击前的 300 毫秒稳定等待保留。

## 完成状态

- `CommonEnsureMain` 返回父流程；`CommonStopOnMain` 则在主界面识别成功后停止整个任务。
