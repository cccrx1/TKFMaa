# 构建与验包

本页供协作者核对构建产物。面向使用者的安装和更新使用主仓库发布的完整包，安装步骤见[项目说明](../../README.md)。

## GitHub Actions 构建

| 工作流      | 用途                                                                                                |
| ----------- | --------------------------------------------------------------------------------------------------- |
| `resources` | 资源、Agent 等相关路径的推送或 PR 可触发构建，也可手工运行。六种桌面目标的测试 Artifact 保留 7 天。 |
| `install`   | 构建包含前端和运行环境的完整包。手工运行生成测试 Artifact，推送 `v*` 版本标签触发完整包发布流程。   |

资源测试 Artifact 包含 `interface.json`、`resource/` 和 `agent/`，用于核对资源布局、引用和加载结果。常规 CI 运行使用 `v0.0.0-resource-ci.<运行编号>` 作为验收版本。涉及前端或运行环境的改动，用同一源码构建的完整包验收。完整包发布与续发步骤见[构建与发布操作约束](contributing/build_release.md)。

## 本地验包

按[本地开发环境](contributing/setup.md)准备 Python 3.12 和 OCR，然后从仓库根目录执行：

```powershell
python tools/build_stamina_activities.py --check
python tools/configure.py --check
python tools/package_resources.py --version v0.0.0-resource-test --os win --arch x86_64
python tools/check_resource_package.py --manifest build/resources/TKFMaa-resource-win-x64-v0.0.0-resource-test.zip.manifest.json
```

产物默认写入 `build/resources/`，再次构建时使用新的测试版本或输出目录。清单记录源码提交、工作区状态和文件 SHA256。验包覆盖文件清单、图片与 Agent 入口引用、Schema、资源加载和 Agent 导入。游戏行为需在客户端验证，覆盖范围和结果写入[本地验证记录](templates/verification.md)。
