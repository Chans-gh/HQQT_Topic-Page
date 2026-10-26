# HQQT Topic Page · 环球青藤专题页 Skill

`qingteng-topic-html` V1.1.0：先整理并确认内容清单，再制作、审阅和精修环球青藤 Web/H5 专题 HTML。独立使用，不依赖作者的本机目录、旧项目或其他Skill；正文单文件，官方青藤页头的搜索/账户等服务允许联网。

## 1. 获取源码

本仓库为**私有仓库**。先取得仓库访问权限，并使用有权限的 GitHub 账号登录；无权限时网页/API可能返回404。私有访问限制不会因为安装Skill而自动解除。

```sh
git clone https://github.com/Chans-gh/HQQT_Topic-Page.git
cd HQQT_Topic-Page
```

也可以在 GitHub 的 Code 菜单下载 ZIP 后解压。安装的目录是仓库里的 **`qingteng-topic-html/`**，不是整个仓库根目录。`maintenance/` 是维护者同步工具，不需要装入Codex。

## 2. 安装到 Codex

任选一种方式；不需要两种都做。

**方式A：让 Codex 安装。** 在具有该私有仓库访问权限的 Codex 中输入：

```text
使用 $skill-installer 安装
https://github.com/Chans-gh/HQQT_Topic-Page/tree/main/qingteng-topic-html
```

安装器需要自己的Git/GitHub访问凭据。浏览器能打开仓库，不代表终端或安装器已获得访问权限；出现404/认证失败时先核对登录账号与仓库权限，不把token发到对话里。

**方式B：从已获取的源码手动安装。** 在仓库根目录运行：

macOS / Linux：

```sh
python3 -c "from pathlib import Path; import shutil; shutil.copytree('qingteng-topic-html', Path.home()/'.agents'/'skills'/'qingteng-topic-html')"
```

Windows PowerShell（已安装Python启动器）：

```powershell
py -3 -c "from pathlib import Path; import shutil; shutil.copytree('qingteng-topic-html', Path.home()/'.agents'/'skills'/'qingteng-topic-html')"
```

目标目录已存在时，命令会停止，不覆盖已有Skill。先核对并备份旧目录，再处理更新。Codex通常会发现新增Skill；若未出现，重新启动Codex。[官方Skill说明](https://learn.chatgpt.com/docs/build-skills)

## 3. 运行环境与依赖

| 使用范围 | 需要什么 |
|---|---|
| 读取规则、整理清单 | 支持本地Skill的Codex及当前任务需要的材料读取能力 |
| HTML组合、静态检查、安装自检 | Python 3.9+；仅标准库，不用pip安装包 |
| 自动浏览器验收 | Node.js 20+、npm、随包锁定的Playwright及Chromium |
| 联网补充 / 图片生成 | 宿主提供相应工具；没有内置供应商、API Key或生成服务。图片仍按业务确认范围执行 |

先进入**安装后的Skill目录**检查基础环境：

```sh
# macOS / Linux
cd "$HOME/.agents/skills/qingteng-topic-html"
python3 scripts/doctor.py
python3 scripts/smoke_test.py
```

```powershell
# Windows PowerShell
Set-Location "$HOME/.agents/skills/qingteng-topic-html"
py -3 scripts/doctor.py
py -3 scripts/smoke_test.py
```

`status: pass`表示基础文件、资产指纹和最小运行通过。没有Node时会准确报告可选浏览器能力缺失，Python工具仍可用。

如需完整浏览器验收，在同一个Skill目录执行：

```sh
npm ci --ignore-scripts --no-audit --no-fund
npx --no-install playwright install chromium
```

然后运行（Windows将`python3`替换为`py -3`）：

```sh
python3 scripts/doctor.py --browser
python3 scripts/smoke_test.py --browser
```

这里的npm依赖和浏览器下载只在你明确执行命令时发生。`doctor.py`和`smoke_test.py`不会自动安装依赖或调用生图。smoke --browser默认联网验收官方页头；普通smoke和doctor不访问业务服务。Playwright版本与锁文件随包提供；可复用现成运行时，配置方法见[环境说明](qingteng-topic-html/references/setup.md)。[Playwright安装文档](https://playwright.dev/docs/library)

Linux如提示缺系统库，按[Playwright浏览器依赖说明](https://playwright.dev/docs/browsers#install-system-dependencies)由有权限的人安装系统依赖；本Skill不自动执行sudo或改系统设置。

## 4. 第一次使用

在Codex输入：

```text
使用 $qingteng-topic-html，把我接下来提供的材料整理成环球青藤专题页。
先提交拟呈现内容清单，等我确认版本和范围后再制作HTML初稿。
```

固定业务流程：材料读取 → 内容清单 → 确认清单 → HTML初稿 → 确认初稿及相关素材方案 → 精修 → 验收交付。清单/初稿不生成新图；部分确认、编号与修订范围持续保留。开发测试的合成确认不代表真实业务授权。

- [Skill入口](qingteng-topic-html/SKILL.md)
- [业务流程](qingteng-topic-html/references/workflow.md)
- [视觉规范](qingteng-topic-html/references/visual-spec.md)
- [工具使用与参数](qingteng-topic-html/references/tools.md)
- [质检要求](qingteng-topic-html/references/quality-checks.md)
- [资源溯源](qingteng-topic-html/assets/provenance.json)

## 5. 作者以后如何从本地 Codex 同步

作者的唯一编辑源仍是本地项目库对应分支的`package/`。已安装Skill是运行副本；若改在安装目录，先比较并人工移植回源目录。GitHub保存该产品的分发快照，不自动双向同步。

最省事：在原开发对话或本地源项目中直接要求Codex：

```text
请验证并提交本次 qingteng-topic-html 修改，然后同步到
Chans-gh/HQQT_Topic-Page 的 main。
只导出当前已提交的 package 产品内容，保留远端提交历史。
核对 PROJECT_OFF 记录的上次远端提交；远端有新修改时先审计。
同步后记录远端SHA，并说明已安装副本是否需要另行更新。
```

维护者工具让这一步可重复执行。在**本地项目库根目录、正确package分支、工作区已提交且干净**时：

```sh
# 把下方SHA替换为PROJECT_OFF中上次已核对的远端提交，不要填本地源提交。
python3 package/maintenance/github_sync.py prepare \
  --expected-head LAST_AUDITED_REMOTE_SHA \
  --out /tmp/qingteng-export.json
```

prepare仅读Git已提交对象，输出源提交、树指纹和文件清单，**零网络写入**。Codex可用GitHub连接器按同一清单上传blob、核对tree、创建以该远端提交为父的新提交，再以非强制更新推进main。

若终端已有对该仓库的写入凭据，也可以显式执行：

```sh
python3 package/maintenance/github_sync.py push --expected-head LAST_AUDITED_REMOTE_SHA
```

push只使用已有`GH_TOKEN`/`GITHUB_TOKEN`、已登录`gh`或Git凭据助手，不新建或扩大权限。不要把凭据写入仓库。凭据不覆盖此私有仓库时，改用已授权的Codex GitHub连接器。远端基线改变、源工作区未提交或分支不符时停止；不会force push，也不会将治理库其他分支历史推上去。

同步完成后更新本地`PROJECT_OFF.md`中的远端提交SHA。已安装的Skill不会因GitHub提交自动更新；使用者需要重新获取，并在备份/核对旧安装副本后更新安装目录。仅安装文档与维护工具变更、无运行文件变化时，可按实际差异判断是否需要更新。

## 6. 验收范围

首版已完成F01–F12流程与修订/省略扩展、十视口数量与容量矩阵、局部浏览以及三种不同完整页的Chromium离线验收。V1.0.1补齐安装/依赖/自检与同步；V1.1.0采用官方青藤页头固定适配版：1200px容器上限、Web/H5统一60px、官方导航/搜索/账户，与页脚原型入口分开。原始来源及适配说明见[qingteng-topic-html/assets/header/sources.json](qingteng-topic-html/assets/header/sources.json)；当前实现与验证记录在源项目PROJECT_OFF。

自检的合成页面与确认记录只验证安装和工具，不替代业务事实/授权核对，也不调用真实生图。Safari、iOS、Android实机和Windows实机未验收；浏览器模拟不能冒充实机结论。未安装或发布到任何Skill市场；此仓库仍为私有分发。
