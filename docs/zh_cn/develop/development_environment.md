# 本地开发环境与依赖验收

本项目当前验证基线为 Python 3.12 和 MaaFramework 5.13.0。这是一套可复核的项目配置，并不表示已证明 Python 3.14 不兼容；保留已有的 3.14 环境即可。

## 配置位置

| 配置                            | 用途                                                                        |
| ------------------------------- | --------------------------------------------------------------------------- |
| `.python-version`               | 声明项目 Python 3.12，供支持该文件的工具读取，不会自动切换所有终端          |
| `.vscode/settings.json`         | Windows 默认解释器和新终端指向 `.venv312`，启用 UTF-8                       |
| `tools/requirements.txt`        | 固定 `maafw==5.13.0` 和校验依赖；并非完整的传递依赖锁文件                   |
| `maatools.config.mts`           | maa-tools 固定加载 5.13.0，避免随 latest 漂移                               |
| `.github/workflows/check.yml`   | 资源校验明确使用 Python 3.12 和 Node.js 22                                  |
| `.github/workflows/install.yml` | 发布 Python 3.12，原生 MaaFramework 固定 v5.13.0，Agent Python 包跟随该版本 |

Maa Support 插件独立维护所选框架版本，修改 maa-tools 配置不会替它切换版本。VS Code 命令面板中的“**Maa: 选择 MaaFramework 版本**”应选择 `5.13.0`。发布前端 MFAAvalonia 仍沿用原来的版本选择策略，此轮没有锁定整个发布工具链。

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

若 `py` 不可用，使用已安装的 Python 3.12 可执行文件完整路径执行 `-m venv .venv312`。不要覆盖已有虚拟环境来排查错误，先核对其中的 `pyvenv.cfg` 和解释器版本。

## 检查命令

```powershell
$env:PYTHONUTF8 = "1"
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

在另一个独立进程确认 Agent 模块可注册：

```powershell
.\.venv312\Scripts\python.exe -c "import sys; sys.path.insert(0, 'agent'); import main; print('Agent imports OK')"
```

这两个探测不要合并到同一 Python 进程：先加载普通框架上下文再注册 Agent 会产生上下文错误。导入通过只证明模块和动态库可加载，不代表 Agent 已连接插件或游戏任务已完成。

## OCR 与本地数据

运行资源应包含 `assets/resource/model/ocr/det.onnx`、`rec.onnx` 和 `keys.txt`。缺少时按仓库要求初始化子模块，再运行 `tools/configure.py`；目录存在时脚本会跳过复制，因此还应检查文件是否完整。模型文件存在并不能证明识别效果正常，也不能仅据此推断与子模块当前提交完全一致。

`.venv312/`、`.venv/`、`debug/`、`assets/debug/`、`config/`、`assets/config/` 和普通 `*.log` 均由 Git 忽略。工具下载依赖需要联网，不会因此自动上传本地调试证据。

本文只说明如何搭建和检查环境，历次验收结论见 [开发环境验收记录](../records/environment.md)。
