# MFAAvalonia 前端候选

此目录保存基于 MFAAvalonia 2.16.2 固定提交的候选补丁与来源清单。它尚未接入正式完整包流程，不是可以单独投放给旧客户端的资源更新。

候选包含资源安装前检查、压缩库与解压调用适配、更新失败后的界面复位、重启锁处理，以及 Windows TKFMaa 的进程临时目录隔离和 Agent TCP 兼容处理。TKFMaa 在线更新要求有效 SHA256，更新日志延后到安装成功后写入。其他项目保留原更新日志策略。

`manifest.json` 固定上游提交、源码 ZIP 与补丁的 SHA256、SDK，以及七个变更文件的应用前后内容摘要。文件摘要统一按 UTF-8、LF 计算；补丁不含本机更新服务地址。

## 本地复现

先取得清单指定提交的 [上游源码 ZIP](https://github.com/MaaXYZ/MFAAvalonia/archive/1080d3e1500f3439ac896ab2eca9aeb8e885f1f4.zip)，然后从本仓库根目录运行：

```powershell
python tools/prepare_frontend_candidate.py --source-zip <源码ZIP路径> --output build/frontend-source
dotnet publish build/frontend-source/MFAAvalonia.Desktop/MFAAvalonia.Desktop.csproj -c Release -r win-x64 -o build/frontend-candidate-bin -p:UsedAvaloniaProducts=
python tools/stage_frontend_candidate.py --source build/frontend-source --published build/frontend-candidate-bin --output build/frontend-staged
```

使用清单指定的 .NET SDK 10.0.403。准备工具不联网、不安装依赖，只在新建的 `build/` 子目录内解压和应用补丁；源码或补丁摘要不符时拒绝继续。编译需要已配置的 NuGet 依赖来源，首次恢复可能联网。

Windows TKFMaa 会在加载 native 库之前把进程 TEMP/TMP 指向安装目录内 `logs/runtime-temp`，并采用 Agent TCP。目录必须可写；不会修改系统环境变量。此目录与日志、配置一样属于运行数据，不应加入资源包或候选源码。

## 构建与验收边界

`frontend-candidate` 手工工作流仅构建 Windows x64，输出来源清单和文件哈希；没有标签或 Release 写权限。Artifact 仍需与同一源码资源、Python 及 native runtime 组装验证。候选的日志/摘要修复、资源更新重启、完整包回滚及本地升级链路已有 Windows x64 验收；在线真实仓库发布闭环、其他平台及游戏任务仍须单独验收。

`install` 手工工作流可勾选 `frontend_candidate`，Windows x64 会从固定源码应用补丁、编译并组装完整包，其余目标保持原前端。候选 Artifact 名称包含 `frontend-candidate-DO-NOT-PUBLISH`；包内记录候选源码、前端文件摘要，并强制标记为演练，完整包镜像工具会拒绝其作为正式来源。来源记录仍要求干净且匹配提交的源码，不绕过云端检查。手工运行即使选择版本标签也不进入发布步骤。

标签推送的正式完整包仍下载原上游前端。采用候选前须审核前端来源、依赖和兼容基线；候选尚未成为正式发布基线，不能只修改基线继续向旧客户端投放小包。测试夹具和本地假版本不得发布。实际云端构建、发布与通道迁移须另行授权并验收。
