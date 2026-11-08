# 运行环境与版本

本文区分用户运行环境、开发环境和构建版本锁定。以下版本根据当前仓库配置核对；升级时同步检查本页与来源文件，不直接以本文替代配置。

## 用户是否需要安装 Python

桌面完整包包含便携 Python、Agent 依赖、MaaFramework native runtime 和 MFAAvalonia 前端。安装脚本将 Agent 启动路径改为包内 Python；Windows 为 `./python/python.exe`，macOS/Linux 为 `./python/bin/python3`。正常使用桌面完整包不要求另装系统 Python。

前端仍要求系统提供 .NET 10 运行环境，不是完全自包含的 .NET 分发。Windows 按包内依赖安装说明处理。完整包需保持目录完整并可写，不能只复制前端可执行文件。

独立资源包只包含资源和 Agent 等文件，不含 Python、前端和 native runtime，只能用于兼容的已有客户端，不能作为首次安装包。Android 构建不走桌面 Python/前端捆绑步骤，不适用上述桌面结论。

以上是构建和启动配置事实，不代表本次已在未安装 Python 的干净系统中执行验收。

## 自动打包固定到什么程度

| 对象                             | 当前约束               | 固定程度与来源                                                                                     |
| -------------------------------- | ---------------------- | -------------------------------------------------------------------------------------------------- |
| Python                           | 3.12，ABI cp312        | 仅固定系列；完整包从 python-build-standalone 的最新 Release 匹配 3.12.\*，补丁版本与构建批次未固定 |
| MaaFramework native runtime      | 5.14.3                 | install 工作流按 v5.14.3 标签下载                                                                  |
| Python maafw                     | 5.14.3                 | requirements 精确固定；包内绑定下载到的 native 版本                                                |
| MFAAvalonia 前端                 | 2.16.2 加本项目补丁    | 固定上游提交、源码 ZIP、补丁及文件摘要，编译后校验来源                                             |
| 前端构建 .NET SDK                | 10.0.403               | 工作流与前端清单固定 SDK 版本                                                                      |
| 用户系统 .NET                    | 10.0 系列              | 系统运行条件，不作为包内运行时捆绑                                                                 |
| numpy / maaagentbinary / strenum | 2.5.4 / 1.0.1 / 0.4.15 | 桌面依赖按 release_baseline 精确安装                                                               |

来源：[完整包工作流](../../../.github/workflows/install.yml)、[Python 依赖](../../../tools/requirements.txt)、[桌面资源基线](../../../tools/release_baseline.json)、[前端构建配置](../../../tools/frontend_release.json)、[前端源码与补丁清单](../../../tools/frontend_candidate/manifest.json)。

因此，当前不能称为“所有依赖完全锁定”或“同一提交必然产生字节一致的完整包”。除 Python 最新构建选择外，构建机镜像、部分构建工具依赖等仍有可变因素。包内来源和文件哈希用于追踪与校验实际产物，不等于下载输入全部固定。

如需提高可复现性，下一步应单独固定便携 Python 的补丁版本、上游发布批次、六目标下载文件及摘要，并核对环境检查和打包工具。此次文档整理不修改工作流、依赖或兼容基线。

## 本地开发

首次安装、创建 `.venv312` 和验证依赖的完整步骤见[本地开发环境](setup.md)。源码工作区缺少该环境与已发布完整包是否内置 Python 是两件事。

开发与正式验证使用 Python 3.12；Windows 使用 `.venv312/`，终端设置 `PYTHONUTF8=1`。`.python-version` 与 CI 均以此为基线；使用 VS Code 时需手动选择项目解释器。其他 Python 版本不作为首选验收环境。
安装依赖后运行 `python tools/check_environment.py --load-resource` 核对解释器、maafw、native runtime 与构建声明，Agent 注册在独立进程检查。

OCR 来源由 `tools/ocr_model.json` 固定。当前只有 `.gitmodules` 声明而缺少 gitlink；使用 `python tools/configure.py --download` 恢复，使用 `--check` 只读核对。虚拟环境、下载模型、截图、日志和个人配置只保留本地。

Python、框架、前端或新增运行依赖的变更需要完整更新与迁移审核；不能只提高资源通道最旧客户端兼容基线后继续发小包。构建声明、资源加载与客户端实机验收分别记录，细则见[构建与发布操作约束](build_release.md)。
