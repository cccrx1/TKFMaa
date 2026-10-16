# 本地开发环境与依赖验收

本项目当前版本基线为 Python 3.12、MaaFramework 5.14.3 和 MFAAvalonia 2.16.2。MaaFramework 5.14.3 的[官方发布说明](https://github.com/MaaXYZ/MaaFramework/releases/tag/v5.14.3)包含 Agent 响应匹配、Android 13+ ADB 方向检测和截图尺寸变化后的稳定等待修复；本仓库仍需通过本地检查与实机回归确认这些修复对项目的实际收益。Python 3.14 不作为本项目首选验证环境。

## 配置位置

| 配置                            | 用途                                                                                                                       |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `.python-version`               | 声明项目 Python 3.12，供支持该文件的工具读取，不会自动切换所有终端                                                         |
| `.vscode/settings.json`         | Windows 默认解释器和新终端指向 `.venv312`，启用 UTF-8                                                                      |
| `tools/requirements.txt`        | 固定 `maafw==5.14.3` 和校验依赖；并非完整的传递依赖锁文件                                                                  |
| `tools/ocr_model.json`          | 固定 OCR 来源修订、三个文件的大小与 SHA256                                                                                 |
| `tools/check_environment.py`    | 检查解释器、Python 包、native runtime 与构建配置一致性，可只读加载资源包                                                   |
| `maatools.config.mts`           | maa-tools 固定加载 5.14.3，避免随 latest 漂移                                                                              |
| `.github/workflows/check.yml`   | 资源校验明确使用 Python 3.12 和 Node.js 22                                                                                 |
| `.github/workflows/install.yml` | 发布 Python 3.12，原生 MaaFramework 固定 v5.14.3，发布前端 MFAAvalonia 固定 v2.16.2，Agent Python 包跟随 MaaFramework 版本 |

MaaMCP 由 Codex 全局配置提供，工具包固定为 `maa-mcp==1.2.3`；一次性、可复现的设备与资源检查使用 `maafw-cli==0.1.6`。两者的独立环境也须固定 `maafw==5.14.3`，仅锁工具包版本不能锁住其传递依赖。MaaMCP 适合截图/OCR/长流程探索，CLI 适合 JSON 输出的检查和短操作，不能让两个后端同时控制同一设备会话。

Maa Support 插件独立维护所选框架版本，修改 maa-tools 配置不会替它切换版本。VS Code 命令面板中的“**Maa: 选择 MaaFramework 版本**”应选择 `5.14.3`。发布前端 MFAAvalonia 由 workflow 的 `MFAA_VERSION` 固定为 `v2.16.2`（[官方发布说明](https://github.com/MaaXYZ/MFAAvalonia/releases/tag/v2.16.2)）；升级前端时须同时确认它与当前的 MaaFramework 版本兼容，不要把前端单独升到 `latest`。

## 使用已安装的环境

已有 `.venv312` 时不必重新创建。在仓库根目录打开新的 PowerShell 终端：

```powershell
$env:PYTHONUTF8 = "1"
.\.venv312\Scripts\python.exe --version
.\.venv312\Scripts\python.exe -m pip check
.\.venv312\Scripts\python.exe -m pip show maafw
```

修改 VS Code 配置后关闭旧终端再新建终端；已有的 Python 解释器选择可能需要通过“Python: Select Interpreter”手动切换到 `.venv312/Scripts/python.exe`。终端中执行 `python -c "import sys; print(sys.executable)"`，应指向该项目虚拟环境。插件启动 Agent 的终端也需要确认使用该环境；仅在另一个终端激活环境不代表正在运行的插件已切换。

首次搭建时才创建环境并安装：

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\python.exe -m pip install -r tools/requirements.txt
npm ci
```

如果机器没有 Python 3.12，可使用已安装的 uv 获取 CPython 3.12，再创建项目环境：

```powershell
uv python install 3.12
uv venv --python 3.12 .venv312
uv pip install --python .venv312\Scripts\python.exe -r tools/requirements.txt
```

若 `py` 不可用，使用已安装的 Python 3.12 可执行文件完整路径执行 `-m venv .venv312`。不要覆盖已有虚拟环境来排查错误，先核对其中的 `pyvenv.cfg` 和解释器版本。

## 检查命令

```powershell
$env:PYTHONUTF8 = "1"
.\.venv312\Scripts\python.exe tools/configure.py --check
.\.venv312\Scripts\python.exe tools/check_environment.py --load-resource
npx @nekosu/maa-tools check
.\.venv312\Scripts\python.exe tools/validate_schema.py --schema-dir deps/tools --resource-dirs assets/resource --exclude-dirs assets/resource/announcement --interface-files assets/interface.json
.\.venv312\Scripts\python.exe tools/build_stamina_activities.py --check
.\.venv312\Scripts\python.exe tools/add_interaction_stability.py --check
npx prettier --check .
```

若 Schema 脚本输出 `UnicodeEncodeError` 并指出 GBK 不能编码勾号，先设置 `PYTHONUTF8=1` 后重跑；这不等同于资源校验失败。

确认 Python 所加载的原生库：

```powershell
.\.venv312\Scripts\python.exe -c "from maa.library import Library; print(Library.version()); print(Library.framework_libpath)"
```

确认命令行后端版本（不连接设备）：

```powershell
uvx --python 3.12 --with maafw==5.14.3 --from maafw-cli==0.1.6 maafw-cli --version
```

MaaMCP 是 stdio 服务，`--help` 不会退出并输出版本帮助。用 Codex 的 `codex mcp get maa-mcp --json` 核对启动配置，再由 MCP 客户端完成 `initialize` / `tools/list` 握手；不要把服务等待输入误判为挂起。

在另一个独立进程确认 Agent 模块可注册：

```powershell
.\.venv312\Scripts\python.exe -c "import sys; sys.path.insert(0, 'agent'); import main; print('Agent imports OK')"
```

这两个探测不要合并到同一 Python 进程：先加载普通框架上下文再注册 Agent 会产生上下文错误。导入通过只证明模块和动态库可加载，不代表 Agent 已连接插件或游戏任务已完成。

## OCR 与本地数据

运行资源应包含 `assets/resource/model/ocr/det.onnx`、`rec.onnx` 和 `keys.txt`。来源由 `tools/ocr_model.json` 固定为 MaaCommonAssets 修订 `dabcd4681ac990dc4361de26416d986abd80e4aa` 的 `OCR/ppocr_v6/small`，逐文件验证大小和 SHA256。本仓库没有记录 `assets/MaaCommonAssets` 的 gitlink，仅执行子模块初始化无法恢复模型。

首次恢复或补齐缺失文件：

```powershell
.\.venv312\Scripts\python.exe tools/configure.py --download
.\.venv312\Scripts\python.exe tools/configure.py --check
```

`--download` 明确允许联网，只补缺失文件；已有文件校验不符时停止，保留原文件供检查。先备份并移走不匹配文件，再重新下载。无参数运行不联网：已有完整模型直接通过，否则尝试从本地 `assets/MaaCommonAssets/OCR/ppocr_v6/small` 导入固定版本。`--check` 只读，不创建目录。可用 `--model-dir tmp/environment-clean/ocr` 验证空目录恢复，不影响游戏使用的模型。

构建和资源检查 workflow 均显式执行 `--download`，不依赖开发机手动复制过的模型。下载中途失败或摘要不符时，不发布本轮已下载的文件。模型仍在 Git 忽略目录中；模型校验只证明来源与完整性，识别效果须由设备测试确认。

Schema 同步使用 `python tools/sync_schemas.py`，按 `tools/requirements.txt` 固定版本下载六份 Schema，不跟随上游 `main`。手动同步 workflow 在校验成功后才提交文件，正常开发不需要运行该 workflow。

`.venv312/`、`.venv/`、`debug/`、`assets/debug/`、`config/`、`assets/config/` 和普通 `*.log` 均由 Git 忽略。工具下载依赖需要联网，不会因此自动上传本地调试证据。

uv 创建的环境默认没有 pip，可使用 `uv pip check --python .venv312/Scripts/python.exe` 和 `uv pip show --python .venv312/Scripts/python.exe maafw`；若需要本文的 `python -m pip` 命令，先用 `uv pip install --python .venv312/Scripts/python.exe pip` 安装。

技能路由、MCP 可用性分级和开发验收步骤见 [Maa 技能与工具流程](maa_workflow.md)。

本文只说明如何搭建和检查环境，历次验收结论见 [开发环境验收记录](../records/environment.md)。

## 使用自动构建包验证前端

前端读取同一个构建包内的 `interface.json`；无需单独安装另一份 MFAAvalonia，也无需先打版本标签。普通分支推送命中 `install.yml` 的路径规则后会生成测试包，只有 `v*` 标签进入 Release 发布步骤。纯文档推送可能不触发构建。

1. 在 GitHub Actions 的 `install` 运行中确认提交 SHA，下载对应的 `TKFMaa-win-x86_64` Artifact。若所需更改仍未提交或未推送，旧 Artifact 不包含它们。
2. 解压到独立目录，完整保留前端、`interface.json`、`resource/`、`agent/`、`python/` 和 `runtimes/`。首次验收使用新配置，避免旧配置掩盖默认值或已移除任务的问题；也避免启动后自动更新切换到另一提交。
3. 启动包内前端，核对任务、选项和活动名称。确认自动通关任务未注册，选择的商城商品与活动难度正确；保存后重启，检查选项是否保持。
4. 连接模拟器，用启动游戏或好友体力任务检查前端是否能启动随包 Agent，并按任务文档完成后回到主界面。核对日志实际使用的 runtime 为 5.14.3，任务结果与画面一致。
5. 再按商城、体力等对应记录的待测分支验证选项效果、任务连续运行和停止行为。保留包的提交 SHA、前端版本、设备与覆盖路径，将结论写入 `docs/zh_cn/records/`；日志和截图保存在本地忽略目录。

源码 Schema、资源加载和 Agent 导入通过后，仍需执行上述包内前端验收，才能确认 MFAAvalonia 2.16.2 与本项目 Interface、Agent、native runtime 的完整组合可用。
