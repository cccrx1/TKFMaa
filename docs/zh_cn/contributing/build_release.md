# 构建与发布操作约束

修改打包工具、工作流或执行发布操作前阅读。任何远端操作仍须遵守根目录 AGENTS.md 的授权边界。资源通道说明见[资源包与完整包构建](../resource_updates.md)，版本固定程度见[运行环境与版本](runtime.md)。版本号示例不构成发布授权。

## 命令索引

命令从仓库根目录执行。下文 `python` 应指向项目 Python 3.12；首次配置见[本地开发环境](setup.md)。示例中的版本和目录须按实际任务替换。

### 环境与日常校验

- `git submodule update --init --recursive`：存在 gitlink 时初始化 Maa 通用资源；当前缺少 gitlink，须按[环境配置](setup.md)恢复本地 OCR。
- `python tools/configure.py --download`：下载固定修订的 OCR 缺失文件，逐文件校验大小和 SHA256，不覆盖不匹配的已有文件。
- `python tools/configure.py --check`：只读检查 OCR 模型完整性与来源一致性。
- `python tools/check_environment.py --load-resource`：核对 Python、maafw、native runtime、构建和 maa-tools 版本，并在不连接设备的情况下加载完整资源包。Agent 导入注册须在另一个独立进程检查。
- `python tools/sync_schemas.py`：按 requirements 固定的 MaaFramework 版本同步六份 Schema，不跟随上游 main。
- `npm ci`：安装 CI 使用的锁定版本 Node.js 工具。
- `npx @nekosu/maa-tools check`：校验 Maa Pipeline 与 Interface 资源。
- 本地默认 GPU 资源加载崩溃时，先保留日志，再运行 `node --require ./tools/maa_check_cpu.cjs node_modules/@nekosu/maa-tools/bin/maa-tools check`；它使用同一固定版本缓存和原版校验器，仅把资源加载改为 CPU，不跳过结构诊断或资源加载。须记录默认命令失败与 CPU 模式结果，不据此宣称 GPU 验收通过。
- `python -m pip install -r tools/requirements.txt`：安装 Maa Agent、配置生成和 Schema 校验所需的 Python 依赖。
- `python tools/validate_schema.py --schema-dir deps/tools --resource-dirs assets/resource --exclude-dirs assets/resource/announcement --interface-files assets/interface.json`：执行与 CI 相同的 JSON Schema 校验。
- `python tools/add_interaction_stability.py --check`：检查带识别结果的交互动作是否配置点击前稳定等待。

### 活动配置生成

- `python tools/build_stamina_activities.py`：修改 `assets/stamina/active.yaml` 后重新生成体力活动配置。
- `python tools/build_stamina_activities.py --check`：只检查体力活动配置与 `assets/interface.json` 是否同步，不写文件。

### 前端编译与组装

- `python tools/prepare_frontend_candidate.py --source-zip <固定源码ZIP> --output build/<新目录>`：离线核验并应用 `tools/frontend_candidate/` 的固定补丁源码，拒绝覆盖已有目录。正式完整包和独立候选工作流共用该源码；后者仍只手工生成不可发布的 Windows x64 Artifact。
- `python tools/stage_frontend_release.py --source <已核验源码目录> --published <编译输出> --platform win-x64 --output <新目录>`：按 `tools/frontend_release.json` 校验固定前端并记录平台、源码及文件哈希，支持六种桌面目标。完整包默认使用此补丁前端，不再下载上游原前端成品。
- `python tools/stage_frontend_candidate.py --source <已核验源码目录> --published <编译输出> --output <新目录>`：保留 Windows x64 诊断候选组装，强制标记不可发布，不能作为正式完整包来源。
- `python tools/clean_package_stage.py --stage install`：仅清理新打包目录中的字节码、缓存、调试符号和日志；拒绝带用户配置、运行日志目录或越界路径的目录。`--check` 只读核对，不能用该工具清理正在运行的客户端或本地验收证据。

### 资源包构建与核验

- `python tools/package_resources.py --version v1.2.3 --os win --arch x86_64`：从当前源码与已核验 OCR 生成独立资源 ZIP、SHA256 和清单，默认输出到被忽略的 `build/resources/`；不下载前端或运行环境，不发布。
- `python tools/check_resource_package.py --manifest build/resources/TKFMaa-resource-win-x64-v1.2.3.zip.manifest.json`：核验资源包路径、文件清单、哈希、Schema、资源加载及 Agent 注册/导入，不连接设备。

### 发布准备与镜像

- `python tools/release_preflight.py --version v1.0.8`：只读核对 `tools/releases/` 中的发布计划、固定前端与公开发布说明；加 `--artifacts <下载目录> --source-sha <明确SHA> --expect-rehearsal` 验证六目标预演完整包。不会打标签或发布。
- `python tools/release_support.py`：核对桌面发布基线与 Python、MaaFramework、完整包构建声明的一致性。
- `python tools/prepare_resource_release.py --help`：查看六目标资源发布附件准备参数；默认要求干净且匹配明确 SHA 的源码，`--allow-dirty` 仅生成不可发布的本机演练产物。
- `python tools/publish_resource_release.py --help`：查看离线演练与显式发布参数；`--dry-run` 只读本地快照，`--publish` 仅允许在目标仓库串行 Actions 中执行，要求明确版本、源码、发布说明及绑定附件清单摘要的验收记录。
- `python tools/mirror_full_release.py --help`：查看完整包镜像准备参数；只读下载主仓库已公开 Release，核对标签提交、远端摘要、包内来源和文件哈希，不重新打包、不发布。

## 兼容基线与升级边界

桌面资源发布基线位于 `tools/release_baseline.json`，完整包中的 numpy、maaagentbinary、strenum 按此固定版本安装。新增依赖或变更 Python、框架、前端基线时须安排整体更新与迁移审核，不得仅修改基线继续向旧客户端投放小包。桌面完整包在依赖安装后通过 `tools/record_full_package.py` 生成来源和逐文件哈希记录；实际运行验收与构建声明分别记录。基线允许名单当前仅含测试仓库，正式源变更仍需明确授权。

## 完整包构建与版本计划

完整包前端构建配置位于 `tools/frontend_release.json`，与资源通道最旧客户端基线分开记录。[v1.0.8 发布计划](../../../tools/releases/v1.0.8.json)采用完整更新，保持主仓库更新源，不部署正式资源通道或提高其兼容指纹；其他版本以各自计划为准。`install` 手工输入 `preview_version: v1.0.8` 可生成准确版本的预演包，源码仍须干净且匹配 SHA，所有非标签构建均记录 rehearsal；即使手工选择版本标签也不发布。正式标签需要对应的 `tools/releases/<版本>.json` 和 `docs/zh_cn/releases/<版本>.md`，发布 job 在上传前核对六个桌面完整包的版本、更新源、来源、前端及全部文件摘要。完整包保留 `licenses/MFAAvalonia-LICENSE.txt` 和绑定源码提交的来源说明，禁止在清理中删除。编译与依赖恢复仍可能联网；前端继续要求系统 .NET 10，与原上游成品一致。

## 发布产物与失败续发

完整发布下载目录固定为 `build/full-release-assets/`，输出ZIP到 `build/full-release-zips/`，不能使用仓库已有的 `assets/`。若标签 install 在上传前失败，但八目标构建和原发布验包已成功，可在用户已明确授权该版本发布的前提下手工运行 `finalize_full_release.yml`，提供既有版本与源运行编号；它核对标签提交、原运行与验收，重复验包后仅发布同批Artifact，不移动标签、不重新编译，已有Release时拒绝执行。两个发布入口共用 `tkfmaa-full-release-publish` 并发组。

## 源码与产物隔离

完整构建下载目录 `/MFA/`、`/python-runtime/` 以及 Python 字节码由 `.gitignore` 排除，不能纳入源码提交；完整包 CI 禁止生成字节码。来源检查仍拒绝真实源码改动，并输出有限的脏路径供定位，不使用 `--allow-dirty` 绕过云端发布来源检查。

## 分支版本命名

分支完整包使用 `git describe --long` 生成 CI 版本：预发布基准追加 `.ci.<距离>.g<提交>`，稳定基准追加 `-ci.<距离>.g<提交>`；版本标签构建保留标签原文。不得把 `beta.1` 改成 `beta.1-ci`，否则数字预发布序号变为文本，可能阻挡后续 beta 资源更新。CI 产物只用于开发验收，不作为已发布完整包镜像来源。

## 资源通道部署与授权

资源仓库工作流模板位于 `tools/resource_repository/publish.yml`，部署后默认只生成 Artifact，发布 job 使用仓库级 `tkfmaa-release-publish` 并发组和本仓库 Token。资源发布还要求仓库变量 `TKFM_CHANNEL_BASELINE_SHA256` 与固定兼容基线一致；它代表该通道最旧受支持客户端的环境，不可随一次完整包升级而直接提高。模板部署、变量变更、远端运行和正式源切换均不由本地实现或提交自动授权。完整包标签构建可通过显式仓库变量 `TKFM_UPDATE_REPOSITORY` 选择更新源，未设置时保持默认源。

## 工作流触发范围

`.github/workflows/resources.yml` 在资源/Agent 等路径的分支推送、PR 或手工运行时生成独立资源 Artifact，只有读取权限，无标签或 Release 发布步骤。完整包继续由 `.github/workflows/install.yml` 在 `v1.2.3` 等版本标签时构建发布；其普通分支/PR 构建仅匹配完整包工具、运行环境与依赖配置等路径，纯活动或 Agent 逻辑改动不触发完整包构建，需要前端组合验收时手工运行完整包流程。两个流程共用 `tools/package_resources.py` 中的资源收集和布局逻辑；完整包仍包含前端、Python 与 native runtime。前端验收须使用对应提交的完整包，按[验证模板](../templates/verification.md)记录来源、环境和覆盖范围。本地完整打包需要预先下载 MaaFramework 运行时，不属于常规开发验证流程。
