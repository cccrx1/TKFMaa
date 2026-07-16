# 如何开发 TKFMaa

开始前请阅读 [MaaFramework 快速开始](https://maafw.com/docs/1.1-QuickStarted) 和本仓库的 [`AGENTS.md`](../../../AGENTS.md)。任务采集、变更分级和验收要求见 [`task_workflow.md`](./task_workflow.md)。

## 准备环境

需要安装 Git、Python、Node.js 和可运行《天下布魔》的 Android 模拟器。克隆仓库并初始化 MaaCommonAssets：

```bash
git clone --recurse-submodules https://github.com/cccrx1/TKFMaa.git
cd TKFMaa
git submodule update --init --recursive
```

安装项目工具依赖并配置 OCR 模型：

```bash
npm ci
python -m pip install -r tools/requirements.txt
python tools/configure.py
```

`tools/configure.py` 会从 `assets/MaaCommonAssets/OCR` 复制默认模型到 `assets/resource/model/ocr/`。OCR 模型是本地生成资源，不提交到仓库。

## 修改任务

- Pipeline 位于 `assets/resource/pipeline/`。
- 识别图片位于 `assets/resource/image/`。
- 用户任务和选项位于 `assets/interface.json`。
- Python 自定义识别和动作位于 `agent/`。
- 页面流程记录位于 `docs/zh_cn/task_flows/`。

新增任务或重构跨页面流程前，先在模拟器中观察并记录实际页面。编写 Pipeline 时遵循“识别、动作、再识别”，不要假设点击后必然进入下一页。

体力活动 Case 由 `assets/stamina_activities.yaml` 生成。活动换期方法见 [`stamina_activity_config.md`](./stamina_activity_config.md)，不要直接修改 `assets/interface.json` 中生成的 Case。

## 本地验证

修改 Pipeline、Interface 或生成配置后至少执行：

```bash
python tools/build_stamina_activities.py --check
npx prettier --check .
npx @nekosu/maa-tools check
python tools/validate_schema.py --schema-dir deps/tools --resource-dirs assets/resource --exclude-dirs assets/resource/announcement --interface-files assets/interface.json
```

修改识别、坐标、手势或资源消耗逻辑后，还要在 MFAAvalonia 中运行受影响任务，并把版本、设备和覆盖路径写入对应任务文档。

## 提交 Pull Request

分支、提交格式、验证记录和截图要求见 [`pull_request_guidelines.md`](./pull_request_guidelines.md)。不要提交 `maafw.log`、`debug/`、`config/`、本地截图、OCR 模型或构建产物。

## 发布

`.github/workflows/install.yml` 会在推送 `v1.2.3` 形式的标签时构建各平台发布包，并将 MFAAvalonia、MaaFramework 运行时、项目资源和 Agent 一起打包。

发布属于维护操作。执行前应确认目标提交、工作区状态、完整验证结果和版本说明，再创建并推送标签：

```bash
git tag v1.2.3
git push origin v1.2.3
```

非维护者无需执行发布步骤。

## 常见问题

参见 [`faq.md`](./faq.md)。
