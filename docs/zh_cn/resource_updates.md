# 资源包与完整包构建

活动配置、图片、识别流程和兼容现有环境的 Agent 逻辑可以通过资源包更新。前端、MaaFramework、Python 或运行依赖变化时，需要完整包。

目前新增的资源流程只生成下载附件，不创建标签、不发布 Release，也未切换正式客户端更新地址。正式资源仓库和首次切换版本仍须单独审核确定。

## 两条构建流程

| 流程        | 触发方式                                          | 产物                                 | 发布行为                          |
| ----------- | ------------------------------------------------- | ------------------------------------ | --------------------------------- |
| `resources` | 资源/Agent 等路径的分支推送、PR，或手工运行       | 六种桌面目标的资源 ZIP、SHA256、清单 | 仅 Artifact，保留 7 天            |
| `install`   | 完整包工具/运行环境配置变更、手工运行或 `v*` 标签 | 带前端与运行环境的完整包             | 只有版本标签进入现有 Release 步骤 |

纯活动更新不再触发完整包构建。需要验证前端、Agent 和运行环境的完整组合时，可手工运行 `install`。两个流程使用相同的资源收集与 Agent 路径转换代码，避免两套资源布局不一致。

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

测试更新源可通过 `--update-repository owner/repository` 覆盖；该参数只改生成包中的 `github`，不修改源码或访问远端。不传时保留源码地址。

## 查看与审核产物

手工运行 `resources` 时填写资源版本。普通分支/PR 自动使用 `v0.0.0-resource-ci.<运行编号>`，只是验收版本。

清单记录源码基准提交、工作区是否有未提交改动、包内逐文件 SHA256，以及要求的 Python/MaaFramework 版本。工作区有改动时，仅凭提交 SHA 无法重现产物，应结合文件清单审核。

下载后先核对 SHA256 与清单，再在独立客户端验证选项、Agent 和受影响的游戏任务。Schema、资源加载与 Agent 导入通过不能代替实机验证。新增 Python 依赖或框架版本变化时，即使资源包能构建，也必须安排完整包升级。

下一阶段在审核后接入正式资源仓库，并通过一次完整包发布切换资源更新源；当前两个流程不会替用户执行这一步。
