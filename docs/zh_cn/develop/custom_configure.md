# 开发环境配置

## Issue 模板

`.github/ISSUE_TEMPLATE/` 已按 TKFMaa 配置。Bug 模板会要求版本、`maafw.log`、相关 `debug` 文件、脱敏后的配置以及模拟器信息。修改日志目录或调试产物后，应同步更新中英文 Bug 模板。

## VS Code 插件

- [Maa Pipeline Support](https://marketplace.visualstudio.com/items?itemName=nekosu.maa-support)：Pipeline 调试、截图、ROI 和取色。
- [markdownlint](https://marketplace.visualstudio.com/items?itemName=DavidAnson.vscode-markdownlint)：Markdown 检查。

仓库的推荐插件位于 `.vscode/extensions.json`。

## 格式化

JSON、YAML 和 Markdown 使用 Prettier，配置位于 `.prettierrc`。检查整个仓库：

```bash
npx prettier --check .
```

只格式化本次修改的文件，避免给无关文件制造格式差异：

```bash
npx prettier --write <文件路径>
```

Python 使用 4 空格缩进，并保持导入位于文件顶部。本项目当前没有配置 pre-commit hooks，不要依赖提交时自动修复格式。

## 调试输出

`config/maa_option.json` 控制 MaaFramework 日志和识别截图：

- `logging`：启用日志。
- `save_on_error`：任务失败时保存调试图。
- `save_draw`：保存绘制识别结果的图片，会显著增加本地文件数量。

`config/`、`debug/` 和 `maafw.log` 都是本地运行产物，不提交到仓库。提交 Issue 前应关闭 TKFMaa，并检查配置和日志中是否包含敏感信息。
