# 资源包与完整包构建

固定前端补丁及来源清单保存在 [`tools/frontend_candidate/`](../../tools/frontend_candidate/README.md)。完整包默认按 `tools/frontend_release.json` 从固定源码编译六种桌面目标，不再下载上游原前端成品。在线更新要求有效 SHA256，更新日志在安装成功后保存；Windows 启动使用独立进程临时目录和 Agent TCP。独立 `frontend-candidate` 工作流仍仅生成不可发布的诊断 Artifact。

活动配置、图片、识别流程和兼容现有环境的 Agent 逻辑可以通过资源包更新。前端、MaaFramework、Python 或运行依赖变化时，需要完整包。

目前新增的资源流程只生成下载附件，不创建标签、不发布 Release，也未切换正式客户端更新地址。正式资源仓库和首次切换版本仍须单独审核确定。

## 两条构建流程

| 流程        | 触发方式                                          | 产物                                 | 发布行为                          |
| ----------- | ------------------------------------------------- | ------------------------------------ | --------------------------------- |
| `resources` | 资源/Agent 等路径的分支推送、PR，或手工运行       | 六种桌面目标的资源 ZIP、SHA256、清单 | 仅 Artifact，保留 7 天            |
| `install`   | 完整包工具/运行环境配置变更、手工运行或 `v*` 标签 | 带前端与运行环境的完整包             | 只有版本标签进入现有 Release 步骤 |

纯活动更新不再触发完整包构建。需要验证前端、Agent 和运行环境的完整组合时，可手工运行 `install`。两个流程使用相同的资源收集与 Agent 路径转换代码，避免两套资源布局不一致。

版本标签本身不自动识别改动类型：主仓库 `v*` 标签走完整包流程，资源发布使用单独的准备/发布流程。v1.0.8 的[发布说明](releases/v1.0.8.md)及 `tools/releases/v1.0.8.json` 明确指定完整更新，保留主仓库更新源；正式资源通道后续迁移。

手工 `install` 的 `preview_version` 可指定已有发布计划中的版本，例如 `v1.0.8`。预演只生成 Artifact，包内来源标记 rehearsal，汇总 job 检查六个桌面包；手工运行即使选择版本标签也不发布。实际标签推送在 Release 上传前检查发布计划、说明、来源 SHA、前端构建配置和文件哈希。每次新版本须准备对应计划与公开说明，不允许将预演包当正式镜像来源。

打包阶段只清理可再生的字节码、缓存、调试符号和日志，不裁剪运行依赖。出现用户配置、运行日志目录或 Git 数据时拒绝继续。仓库 `build/` 和本地验证资料不进入完整包，历史活动归档也不进入运行资源 ZIP。

## 本机构建资源包

使用项目 Python 3.12 环境，先安装 `tools/requirements.txt` 与锁定的 Node 依赖。缺少 OCR 时明确执行 `python tools/configure.py --download`；打包工具本身不会下载模型或运行环境。

```powershell
python tools/build_stamina_activities.py --check
python tools/configure.py --check
python tools/package_resources.py --version v1.2.3 --os win --arch x86_64
python tools/check_resource_package.py --manifest build/resources/TKFMaa-resource-win-x64-v1.2.3.zip.manifest.json
```

`--os` 支持 `win`、`macos`、`linux`，`--arch` 支持 `x86_64`、`aarch64`。这些参数确定附件名称与随包 Python 的入口路径，不表示目标系统已完成实机验收。

资源包仅收集 `interface.json`、`resource/` 和 `agent/`，不会包含前端、Python、native runtime、用户配置、日志或 Python 缓存。OCR 必须与 `tools/ocr_model.json` 锁定内容一致。产物默认写入 `build/resources/`，同名文件存在时拒绝覆盖。

共用资源收集和验包流程会检查 Agent 入口，以及 Pipeline 和 Interface Override 中显式引用的模板图片或非空模板目录。缺文件时在生成或核验阶段报错，错误包含引用来源。该检查随资源包、完整包资源收集及发布准备执行。

测试更新源可通过 `--update-repository owner/repository` 覆盖；该参数只改生成包中的 `github`，不修改源码或访问远端。不传时保留源码地址。

## 查看与审核产物

手工运行 `resources` 时填写资源版本。普通分支/PR 自动使用 `v0.0.0-resource-ci.<运行编号>`，只是验收版本。

清单记录源码基准提交、工作区是否有未提交改动、包内逐文件 SHA256，以及要求的 Python/MaaFramework 版本。工作区有改动时，仅凭提交 SHA 无法重现产物，应结合文件清单审核。

下载后先核对 SHA256 与清单，再在独立客户端验证选项、Agent 和受影响的游戏任务。Schema、资源加载与 Agent 导入通过不能代替实机验证。新增 Python 依赖或框架版本变化时，即使资源包能构建，也必须安排完整包升级。

## 本地发布准备与演练

`tools/release_baseline.json` 固定桌面资源基线和更新仓库允许名单。当前仅允许既有测试仓库，正式资源仓库尚未确定。完整包的 numpy、maaagentbinary、strenum 安装版本从此文件读取；基线来源为已验收 Windows x64 测试客户端，不代表其他平台已完成运行验收。

发布准备、演练与真实发布分别执行：

- `prepare_resource_release.py` 接收六个桌面资源包及清单，重新核对当前源码、版本、基线和更新源，逐包执行 Schema、资源加载与 Agent 注册/导入检查。
- 输出仅包含六个 ZIP、`checksums.txt` 和 `release-manifest.json`。按固定前端附件选择规则检查每个平台唯一命中正确 ZIP，不把逐 ZIP 的校验附件直接发布。
- `publish_resource_release.py --dry-run` 只读取本地远端状态快照，输出拟创建或恢复草稿的计划。`--publish` 则在指定的串行 Actions 发布 job 内上传草稿，核验远端大小和摘要，再公开；拒绝覆盖已公开版本、倒序版本、不一致草稿、缺失或错误摘要。
- 工作区有未提交内容时默认拒绝准备；显式 `--allow-dirty` 只用于本机演练，输出标记 `publishable: false`。即使工作区干净，来源检查通过也不代替客户端验收和发布审核。

准备命令示例（输入目录须先包含同一版本、源码和更新源的六个包）：

```powershell
$sourceCommit = git rev-parse HEAD
python tools/prepare_resource_release.py --input build/resources --output build/release-ready --version v0.0.0-resource-test --repository cccrx1/TKFMaa-update-test --source-sha $sourceCommit
python tools/publish_resource_release.py --prepared build/release-ready --remote-snapshot build/remote-snapshot.json --dry-run
```

离线快照格式为 `{"repository":"cccrx1/TKFMaa-update-test","complete":true,"releases":[]}`；每条 Release 使用 GitHub 的 `tag_name`、`draft`、`prerelease`、`body`、`assets` 字段。空列表只适用于模拟空仓库，不代表现有测试仓库的真实状态。恢复草稿要求正文包含演练输出的清单摘要标记，已有附件的大小和 `digest` 必须一致。快照检查不能代替发布前实时分页查询。

Agent 静态 import 检查会拒绝未列入基线的新依赖，但不证明动态 import、运行时 API 或游戏行为兼容。Python、框架、前端或依赖基线改变时，需要整体更新和新的迁移审核，不能只修改基线文件就继续发布小包。

## 完整包的来源记录

`tools/install.py` 新增可选 `--update-repository owner/repository`，只影响生成包。手工 `install` 工作流提供相同输入；标签构建可通过维护者显式设置的仓库变量 `TKFM_UPDATE_REPOSITORY` 选择源，未设置时保持默认。变更该变量须单独审核，不会迁移已安装客户端。

桌面完整包在依赖安装完成后执行 `record_full_package.py`，生成包内 `package-provenance.json`，记录源码、更新源、声明基线、实际依赖 METADATA 和文件哈希。记录前要求资源与源码完全一致，依赖符合基线，并检查前端、Python 和 native runtime 文件存在。框架与前端版本来自固定构建声明，不能把文件存在检查写成目标平台执行验证。Android 保持原有构建，不进入此桌面资源基线。

`mirror_full_release.py` 从主仓库已公开的同版本 Release 下载六个桌面完整包，解析标签到指定源码提交，核对 GitHub 摘要、包内来源/依赖和逐文件哈希，保持原 ZIP 不变。包内更新源必须已指向目标更新仓库，不接受镜像时修改 ZIP，也不接受缺少来源记录的历史包。镜像产物与资源包使用相同的准备附件布局和发布工具。

## 部署发布工作流

`tools/resource_repository/publish.yml` 是待部署到已批准资源仓库 `.github/workflows/publish.yml` 的模板，不是主仓库中已启用的发布流程。

1. 指定主仓库 40 位源码提交、版本和 `resource` / `full-mirror` 类型，保持 `publish: false`，取得候选 Artifact。
2. 核验候选并完成 Windows x64 客户端验收，记录 `release-manifest.json` 的 SHA256。
3. 使用相同源码、版本、包类型重新运行，显式启用发布，并提供发布说明与验收 JSON。该 JSON 必须包含 `source_commit`、`version`、`manifest_sha256`、`windows_x64_passed: true` 和非空 `evidence`；摘要不符时禁止上传。声明必须有实际验收证据支持。
4. 发布 job 只获得资源仓库自己的写权限；按仓库串行执行，实时分页读取 Release 与附件，上传草稿后验证全部摘要，公开前再次检查版本序列。不会删除或替换不一致附件，失败保留草稿供检查；一致草稿可恢复，公开版本不可覆盖。

资源发布前须配置 `TKFM_CHANNEL_BASELINE_SHA256` 为 `python tools/release_support.py` 输出的兼容指纹。这是该通道最旧受支持环境的固定约束，不能在发布新环境完整包后立即改成新指纹继续发小包。跨环境升级应暂停旧通道小包，完成兼容拦截或新通道迁移；完整包仍可作为明确审核的升级交付。

工作流并发组只能串行使用该组的任务，不能防止维护者手工或其他发布程序并行修改 Release。应将该工作流设为此通道唯一写入入口。草稿上传异常不会自动删除附件；缺摘要或内容不符的草稿需维护者检查，工具不会自动覆盖修复。

这些工具已实现本机模拟测试，Windows x64 候选已完成本地完整包→资源包→完整包、故障回滚和摘要校验。新工作流尚未部署，真实 GitHub 上传、完整包在线镜像、通道迁移及在线跳版本闭环仍待验收；本地结果不代表其他平台通过。

正式接入建议使用独立资源仓库作为新客户端统一入口：兼容改动发资源包，需要整体更新时镜像主仓库完整包，同一版本只放一种包。首次接入须下载完整包到新目录并确认更新源；现有 MFAAvalonia 2.16.2 应用内更新会保留旧源，不能承诺自动迁址。将来跨运行环境基线升级时，恢复小包发布前须有兼容拦截或新的迁移方案，防止旧用户跳过整包后误装小包。
