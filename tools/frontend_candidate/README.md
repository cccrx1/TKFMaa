# MFAAvalonia 固定补丁源码

此目录保存基于 MFAAvalonia 2.16.2 固定提交的补丁与来源清单。正式完整包和诊断候选共用该源码；前端改动必须通过完整更新交付。

候选包含资源安装前检查、压缩库与解压调用适配、更新失败后的界面复位、重启锁处理，以及 Windows TKFMaa 的进程临时目录隔离和 Agent TCP 兼容处理。TKFMaa 在线更新要求有效 SHA256，更新日志延后到安装成功后写入。其他项目保留原更新日志策略。

`manifest.json` 固定上游提交、源码 ZIP 与补丁的 SHA256、SDK，以及七个变更文件的应用前后内容摘要。文件摘要统一按 UTF-8、LF 计算；补丁不含本机更新服务地址。

## 本地复现

先取得清单指定提交的 [上游源码 ZIP](https://github.com/MaaXYZ/MFAAvalonia/archive/1080d3e1500f3439ac896ab2eca9aeb8e885f1f4.zip)，然后从本仓库根目录运行：

```powershell
python tools/prepare_frontend_candidate.py --source-zip <源码ZIP路径> --output build/frontend-source
dotnet publish build/frontend-source/MFAAvalonia.Desktop/MFAAvalonia.Desktop.csproj -c Release -r win-x64 -o build/frontend-candidate-bin -p:UsedAvaloniaProducts=
python tools/stage_frontend_release.py --source build/frontend-source --published build/frontend-candidate-bin --platform win-x64 --output build/frontend-staged
```

使用清单指定的 .NET SDK 10.0.403。准备工具不联网、不安装依赖，只在新建的 `build/` 子目录内解压和应用补丁；源码或补丁摘要不符时拒绝继续。编译需要已配置的 NuGet 依赖来源，首次恢复可能联网。

Windows TKFMaa 会在加载 native 库之前把进程 TEMP/TMP 指向安装目录内 `logs/runtime-temp`，并采用 Agent TCP。目录必须可写；不会修改系统环境变量。此目录与日志、配置一样属于运行数据，不应加入资源包或候选源码。

## 构建与验收边界

`frontend-candidate` 手工工作流仅构建 Windows x64，输出来源清单和文件哈希；没有标签或 Release 写权限。Artifact 仍需与同一源码资源、Python 及 native runtime 组装验证。候选的日志/摘要修复、资源更新重启、完整包回滚及本地升级链路已有 Windows x64 验收；在线真实仓库发布闭环、其他平台及游戏任务仍须单独验收。

`install` 默认编译六种桌面平台的固定补丁前端，按 `tools/frontend_release.json` 核对源码、基线和文件摘要，包内保存 `frontend-build-provenance.json`。所有非标签构建强制记录 rehearsal，不绕过云端干净源码检查。手工输入 `preview_version: v1.0.8` 可按发布计划生成准确版本的预演完整包；即使选择版本标签也不会发布。

正式标签流程使用相同的补丁前端，发布前检查版本计划、发布说明及六个桌面完整包的来源和哈希。v1.0.8 保持主仓库更新源，不迁移正式资源通道；资源通道最旧客户端兼容指纹不随前端构建配置修改。独立候选仍用 `stage_frontend_candidate.py` 生成不可发布的来源记录，不能替代正式构建记录。预演和本地假版本不得发布。

前端保持与上游 2.16.2 相同的系统 .NET 10 要求，不在本次改成独立运行时分发。打包仅清理缓存、字节码、符号和日志，不删除 DLL 或按文件名裁剪动态依赖。

组装目录的 `licenses/` 保存上游 GPL-3.0 许可证及绑定 TKFMaa 源码提交的补丁/构建说明链接，文件哈希进入来源清单。TKFMaa 根目录原有许可证保持不变。
