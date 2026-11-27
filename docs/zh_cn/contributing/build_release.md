# 构建与发布操作约束

修改打包工具、工作流或执行发布操作前阅读。远端操作遵守根目录 AGENTS.md 的授权边界。测试产物的用法见[构建与验包](../resource_updates.md)，版本固定程度见[运行环境与版本](runtime.md)。

## 命令索引

命令从仓库根目录执行。下文 `python` 应指向项目 Python 3.12；首次配置见[本地开发环境](setup.md)。示例中的版本和目录须按实际任务替换。

### 环境与日常校验

- `python tools/configure.py --download`：下载固定修订的 OCR 缺失文件，逐文件校验大小和 SHA256，不覆盖不匹配的已有文件。
- `python tools/configure.py --check`：只读检查 OCR 模型完整性与来源一致性。
- `python tools/check_environment.py --load-resource`：核对 Python、maafw、native runtime、构建和 maa-tools 版本，并在不连接设备的情况下加载项目资源。Agent 导入注册须在另一个独立进程检查。
- `python tools/sync_schemas.py`：按资源通道版本同步六份 Schema。完整包 CI 用 `--maafw-tag <标签> --output-dir build/maafw-schemas` 将所选框架的 Schema 下载到独立目录。
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

### 本地验包

- `python tools/package_resources.py --version v0.0.0-resource-test --os win --arch x86_64`：从当前源码与已核验 OCR 生成测试 ZIP、SHA256 和清单，默认写入被忽略的 `build/resources/`。
- `python tools/check_resource_package.py --manifest build/resources/TKFMaa-resource-win-x64-v0.0.0-resource-test.zip.manifest.json`：核验测试 ZIP 的路径、文件清单、哈希、Schema、资源加载及 Agent 注册和导入。

### 完整包发布准备

- `python tools/release_preflight.py --version v1.0.8`：只读核对 `tools/releases/` 中的发布计划、固定前端与公开发布说明；加 `--artifacts <下载目录> --source-sha <明确SHA> --expect-rehearsal` 验证六目标预演完整包。不会打标签或发布。
- `python tools/release_support.py`：核对完整包构建声明与完整包基线。

## 兼容基线与升级边界

`tools/full_package_baseline.json` 提供完整包的 Python、前端和其他桌面依赖约束，并保留历史完整包的框架基线供验包。新的 install 运行从 MaaFramework GitHub Latest Release 解析稳定标签，保存到 `maafw-build` Artifact。所有目标、Python wheel、Schema 和发布验包都使用这次选择。同一运行重试沿用已保存的选择。框架附件、wheel 或 Schema 缺失时构建失败。桌面包记录来源和逐文件哈希，实际运行验收单独记录。正式更新源使用主仓库，变更更新地址须明确授权并核对已有客户端的升级路径。

资源包 CI 使用 `tools/release_baseline.json` 的客户端兼容版本校验，不随完整包选到的新版本变化。涉及资源通道迁移时核对现存客户端的升级路径。

## 完整包构建与版本计划

完整包前端构建配置位于 `tools/frontend_release.json`。[v1.0.8 发布计划](../../../tools/releases/v1.0.8.json)使用主仓库更新源。手工运行 `install` 时，输入 `preview_version: v1.0.8` 可生成指定版本的预演包，源码须干净且匹配 SHA。手工构建只上传 Artifact，并记录为 rehearsal。正式标签需要对应的 `tools/releases/<版本>.json` 和 `docs/zh_cn/releases/<版本>.md`。发布 job 在上传前核对六个桌面完整包的版本、更新源、来源、前端及全部文件摘要。完整包保留 `licenses/MFAAvalonia-LICENSE.txt` 和绑定源码提交的来源说明。编译与依赖恢复可能联网，前端要求系统 .NET 10。

新版本先用 `preview_version` 打包并验收，将预演实际通过的 MaaFramework 版本写入发布计划的 `maafw` 字段，例如 `"maafw": "5.16.1"`，发布说明填写同一版本。正式构建仍会选取当时的最新稳定版。所选版本与计划不同时发布验包失败。按新框架重新预演和验收后，使用包含新发布计划的提交准备新标签。后续验包及失败续发读取原运行的 `maafw-build`，并核对两份 Android 包的标签。

## 发布产物与失败续发

发布流程将下载的附件放在 `build/full-release-assets/`，生成的 ZIP 放在 `build/full-release-zips/`。如果八个目标均已构建成功、原发布任务已执行验包步骤，但整次运行失败且 Release 尚未创建，可在该版本已获发布授权时手工运行 `finalize_full_release.yml`，提供原版本和运行编号。该流程核对标签提交和原运行，重新验包成功后发布同一批附件。预发布标签会创建预发布 Release。两个发布入口共用 `tkfmaa-full-release-publish` 并发组。

## 源码与产物隔离

完整构建下载目录 `/MFA/`、`/python-runtime/` 以及 Python 字节码由 `.gitignore` 排除，不能纳入源码提交；完整包 CI 禁止生成字节码。来源检查仍拒绝真实源码改动，并输出有限的脏路径供定位，不使用 `--allow-dirty` 绕过云端发布来源检查。

## 正式版本号

随游戏版本更新资源或新增功能并发版时，版本号末位加一，例如 `v1.0.8` → `v1.0.9`。前两位的递增时机留待具体版本决定。

## 分支版本命名

分支完整包使用 `git describe --long` 生成 CI 版本。预发布基准追加 `.ci.<距离>.g<提交>`，稳定基准追加 `-ci.<距离>.g<提交>`。保留 `beta.1` 中的数字序号，避免影响后续 beta 的版本比较。版本标签构建保留标签原文。分支构建产物仅用于开发验收。

## 工作流触发范围

`.github/workflows/resources.yml` 在资源和 Agent 等相关路径的分支推送、PR 或手工运行时生成测试 Artifact。`.github/workflows/install.yml` 的分支和 PR 构建匹配完整包工具、运行环境与依赖配置等路径。需要验证前端与运行环境的组合时，手工运行 `install`，使用对应提交的完整包，并按[验证模板](../templates/verification.md)记录来源、环境和覆盖范围。正式版本由 `install` 的版本标签流程发布。本地完整打包需预先下载 MaaFramework 运行时。
