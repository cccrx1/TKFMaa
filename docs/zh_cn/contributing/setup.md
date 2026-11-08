# 本地开发环境

本页用于从源码开发和校验。使用桌面完整包的用户无需执行这些步骤：完整包已经带有 Python、Agent 依赖和 MaaFramework。两种环境的区别见[运行环境与版本](runtime.md)。

## Windows 首次配置

安装 64 位 Python 3.12，可与其他版本共存。Windows 的 Python Install Manager 支持直接安装指定版本，推荐在仓库根目录执行：

```powershell
py install 3.12
py -3.12 --version
```

也可以从 [Python 官方下载](https://www.python.org/downloads/windows/)取得 3.12 安装程序。安装后重新打开终端，用 `py -3.12 --version` 确认。
如果该命令找不到解释器，先解决 Python 3.12 安装或启动器识别问题，不要退回普通 `python` 命令创建项目环境。

从仓库根目录执行以下 PowerShell 命令，逐条确认成功后继续。已有 `.venv312` 时先检查其中解释器版本，不覆盖或删除已有环境。

```powershell
py -3.12 -m venv .venv312
$env:PYTHONUTF8 = "1"
.\.venv312\Scripts\python.exe --version
.\.venv312\Scripts\python.exe -m pip install -r tools/requirements.txt
npm ci
```

`tools/requirements.txt` 已包含固定的 maafw 及配置、Schema 工具依赖，pip 会解析并安装其依赖。无需先向系统 Python 3.15 安装一份 maafw，也不要另行安装未固定的最新版覆盖项目版本。
安装成功不等于版本及 native 库均可用，下一步仍须检查。

这些命令直接指定环境内的解释器，无需激活环境，也无需修改 PowerShell 执行策略。Node.js/npm 是单独的开发工具；`npm ci` 使用仓库锁文件安装。
使用 VS Code 时，在环境创建后选择 `.venv312` 中的解释器；新终端中确认 `PYTHONUTF8=1` 和 Python 路径符合预期。

## 验证安装

先检查模型与环境：

```powershell
.\.venv312\Scripts\python.exe tools/configure.py --check
.\.venv312\Scripts\python.exe tools/check_environment.py
```

OCR 缺失时执行以下下载命令，随后重跑 `--check`。已有模型哈希不匹配时停止并排查，不直接覆盖。

```powershell
.\.venv312\Scripts\python.exe tools/configure.py --download
```

环境和模型就绪后再执行资源与源码检查：

```powershell
.\.venv312\Scripts\python.exe tools/check_environment.py --load-resource
.\.venv312\Scripts\python.exe tools/validate_schema.py --schema-dir deps/tools --resource-dirs assets/resource --exclude-dirs assets/resource/announcement --interface-files assets/interface.json
.\.venv312\Scripts\python.exe tools/build_stamina_activities.py --check
.\.venv312\Scripts\python.exe tools/add_interaction_stability.py --check
npx @nekosu/maa-tools check
```

在另一个独立进程检查 Agent 模块导入和装饰器注册，不启动设备任务或等待 Agent 连接：

```powershell
.\.venv312\Scripts\python.exe -c "import sys; sys.path.insert(0, 'agent'); import main; print('Agent imports completed')"
```

导入成功不能证明每个 Custom 名称与配置的对应关系正确，更不能代替设备验证。默认 GPU 资源加载异常时保留日志，并参考[CPU 检查说明](build_release.md)，分别记录默认模式与 CPU 模式结果。

## 环境缺失时怎样判断

| 现象                                  | 含义与处理                                                  |
| ------------------------------------- | ----------------------------------------------------------- |
| `.venv312` 不存在                     | 当前源码工作区尚未配置开发环境，不代表发布完整包缺少 Python |
| `No module named maa` 或 `jsonschema` | 检查实际调用的解释器，再在项目环境安装 requirements         |
| maafw/native 版本不一致               | 按环境检查输出核对版本与库路径，不直接升级到最新版          |
| 模型缺失                              | 按固定模型清单恢复；不靠重新安装 Python 解决                |
| 完整包缺少 `python/` 或 `runtimes/`   | 完整包不完整，应重新取得完整包，避免用系统安装掩盖缺文件    |

虚拟环境、下载模型、调试输出和个人配置保留在被忽略的本地路径。开发与发布依赖升级需要单独审核，不通过修改本机环境自动改变打包配置。
