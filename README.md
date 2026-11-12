# HQQT Topic Page · 环球青藤专题页 Skill

`qingteng-topic-html` V1.9.0：按环球青藤视觉规范制作独立Web/H5专题。保留用户跨轮素材要求，分别核对AI生成素材履约与网页排版；合并远端1.2.4可选分享能力。正文单文件，官方页头服务允许联网。

## 1. 获取源码

本仓库当前公开，可从GitHub获取运行源。作者的内部复盘规格、验收报告和业务材料保留在本地维护库，不随公开分发。

```sh
git clone https://github.com/Chans-gh/HQQT_Topic-Page.git
cd HQQT_Topic-Page
```

也可以在 GitHub 的 Code 菜单下载 ZIP 后解压。安装的目录是仓库里的 **`qingteng-topic-html/`**，不是整个仓库根目录。`maintenance/` 是维护者同步工具，不需要装入Codex。

## 2. 安装到 Codex

任选一种方式；不需要两种都做。

**方式A：让 Codex 安装。** 在 Codex 中输入：

```text
使用 $skill-installer 安装
https://github.com/Chans-gh/HQQT_Topic-Page/tree/main/qingteng-topic-html
```

安装器按GitHub实际访问状态下载；出现404或认证失败时核对地址和访问状态，不把token发到对话里。

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
| 分享（可选） | Node.js 18+ 与青水平台 API Key（`QINGSHUI_API_KEY`）；仅用户明确要求时执行，命令与限制见 tools.md 分享节 |

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

默认业务流程：材料读取 → 内容清单 → 确认清单 → HTML初稿 → 确认初稿及相关素材方案 → 精修 → 验收交付。清单/初稿不生成新图；部分确认、编号与修订范围持续保留。开发测试的合成确认不代表真实业务授权。用户明确直接委托完成时，使用独立执行授权继续制作，不伪造实际清单或初稿审阅。

- [Skill入口](qingteng-topic-html/SKILL.md)
- [业务流程](qingteng-topic-html/references/workflow.md)
- [视觉规范](qingteng-topic-html/references/visual-spec.md)
- [工具使用与参数](qingteng-topic-html/references/tools.md)
- [质检要求](qingteng-topic-html/references/quality-checks.md)
- [资源溯源](qingteng-topic-html/assets/provenance.json)

## 5. 作者以后如何从本地 Codex 同步

作者的唯一编辑源仍是本地项目库对应分支的`package/`。公开导出明确排除distribution.json中local_only_paths列出的内部复盘与验收报告；业务材料、旧页面和截图始终不进入该产品源。已安装Skill是运行副本；若改在安装目录，先比较并人工移植回源目录。GitHub保存该产品的分发快照，不自动双向同步。

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

push只使用已有`GH_TOKEN`/`GITHUB_TOKEN`、已登录`gh`或Git凭据助手，不新建或扩大权限。不要把凭据写入仓库。凭据不覆盖此仓库时，改用已授权的Codex GitHub连接器。远端基线改变、源工作区未提交或分支不符时停止；不会force push，也不会将治理库其他分支历史推上去。

同步完成后更新本地`PROJECT_OFF.md`中的远端提交SHA。已安装的Skill不会因GitHub提交自动更新；使用者需要重新获取，并在备份/核对旧安装副本后更新安装目录。仅安装文档与维护工具变更、无运行文件变化时，可按实际差异判断是否需要更新。

## 6. 验收范围

首版已完成F01–F12流程与修订/省略扩展、十视口数量与容量矩阵、局部浏览以及三种不同完整页的Chromium离线验收。V1.0.1补齐安装/依赖/自检与同步；V1.1.0采用官方青藤页头固定适配版：1200px容器上限、Web/H5统一60px、官方导航/搜索/账户，与页脚原型入口分开。V1.2.0–V1.2.1完善对外表达与通用编辑验收；V1.2.2增加可选分享步骤：仅在用户明确要求时先用prepare_share.py生成分享适配副本（内联远程图片、移除搜索iframe），再上传并返回链接；已实测全链路（分享、URL可访问、取消分享后URL失效）。V1.2.3把上传改为内置青水分享源码（`scripts/share/share.js`，仅迁移share/assets/unshare与打包清洗逻辑、无第三方依赖、不经npx），并修复页头CSS中一条无效url()声明。V1.2.4在公共外壳脚本中为分享平台会清洗的form/input/button补空值防护（缺失时退化为惰性占位，避免脚本中断导致页脚入口失效），并在分享文档中明确禁止成品页使用`--no-scripts`——卡片列宽与媒体槽位由topic.js运行期计算，禁用脚本会使卡片退化为单列、图文区塌陷成窄条。分享页运行在平台CSP沙箱，官方页头搜索/账户与表单交互被服务端清洗或降级。原始来源及适配说明见[qingteng-topic-html/assets/header/sources.json](qingteng-topic-html/assets/header/sources.json)；当前实现与验证记录在源项目PROJECT_OFF。

自检的合成页面与确认记录只验证安装和工具，不替代业务事实/授权核对，也不调用真实生图。Safari、iOS、Android实机和Windows实机未验收；浏览器模拟不能冒充实机结论。未安装或发布到任何Skill市场；该源码仓库当前公开。

## 7. 真实测试复盘与升级规格

2026-10-26真实专题测试暴露了内容提炼、视觉层级、整页编排、容量算法及验收闭环的问题。用户已决定停止沿用D01–D03作为交付候选，要求全面升级后以同项目从零重测。

本地维护库的《真实测试复盘与全面升级 SPEC V1.0》记录用户反馈、已核对原因、待验证假设、升级要求、回归与重测契约。V1.2.0已按它完成开发与合成验收，实际范围见本地升级验收报告；同项目真实从零重测另行启动。它是维护规格，不属于安装Skill的运行文件，也不进入Skill分发ZIP。业务失败页面、真实截图及报告继续保存在原任务目录，不纳入Skill源。


## 8. V1.2.0开发验收与更新

本轮将文案提炼与视觉编排落入清单/记录/初稿：生产链、成长成果、前后变化和证据、指标主次、场景图文及媒体组。组级默认保持模块边界，显式compact只用于局部；容量按可换行文字、媒体固有比例和父容器计算，取消渲染高度反馈。共享页头修正320px容量与过渡，保留60px、1200px和原公共入口。

1.2.0当时采用节内短引用与页尾去重（现行1.2.1输出边界见下节）；输入读取、主张核验和采用分开；混合模块范围与公共壳快照有核对；自定义资源占位不能冒充final。工具报告绑定HTML/截图SHA，并将内容/视觉默认not-run，需执行者逐模块实际审查。

维护者可在本地源项目复验（不会调用生图）：

```sh
python3 package/maintenance/upgrade_regression.py --out /tmp/qingteng-upgrade-check
# 配好Playwright，或按setup显式配置QT_PLAYWRIGHT_MODULE后：
node package/maintenance/upgrade_browser.mjs /tmp/qingteng-upgrade-check package/qingteng-topic-html
```

41项范围/收口回归、数量与交互压力矩阵、三份整页Chromium检查及桌面/H5逐模块目视的真实结果、I/R/T映射与剩余边界见验收报告。合成页和批准只用于开发，不替代真实项目材料与两次业务确认。真实图片服务调用0；真实登录、Safari/iOS/Android/Windows实机和真实视频解码未测试。官方搜索源环境一次未取得输入框；ZIP隔离在线复验已加载1个真实输入框。搜索提交结果和真实账号仍未测，离线/失败/超时回退另有实测。

运行源1.2.0与独立分发已验证；用户可按安装说明更新，旧安装先比对并备份。维护者内部报告与当前安装状态保留在本地维护库。ZIP仅含已提交Skill源，不含maintenance、业务失败样本、测试页、截图或报告。

1.2.0交付源提交`8f4b23c`，Skill tree `f0408ef4f7e5b7621d51a5b8beab687dc6956a5a`；49文件ZIP的CRC/字节核对及隔离npm ci、doctor/smoke、重新组合与浏览器验收已通过，详见验收报告。


## 9. V1.2.1 共性能力修订

对外成品的正文、图注、alt显式编写；内部来源、查证与采用留在记录和初稿/精修审阅区，final不自动输出来源编号或“引用与口径”，也不从supports/purpose生成公开说明。读者确有需要的出处与条件在正文自然组织。兼容旧来源public_note作为内部记录；素材alt需明确填写，图注可省略。页脚/服务弹窗的制作解释改为面向读者的文案和真实官网下一步，官方页头及既有路由行为保留。

workflow补充跨题材的材料→取舍→完整文案→构图示例；选材检查主张、受众、场景与适用条件；案例依据实际行动/产物/证据组织，无可比材料时不强制前后变化。首屏标题与信息权重按任务选择；精修逐项检查问题是否解决、删减后信息是否完整。使用既有字段，避免把具体项目的名称、岗位门槛或原句写成全局规则。

工程检查补齐真实图像编码、无内部字段回退、放大图注、全部标题字号、普通纯色背景正文对比度与长模块捕获。`check_html.py --review`可核对人工内容/视觉结论对应的HTML、逐模块依据与截图文件；人工fail使汇总失败，工具不自动理解文案或证明评审真实。基础自检只证明其覆盖的运行行为；完整开发验证、当前安装和发布状态以本地PROJECT_OFF为准。真实业务重测与实机验收另计。


## 10. V1.3.0 视觉体系与制作接口

本地源默认采用薄荷浅色开场、蓝/绿/橙/青协调分类色、原创内容图标、软阴影白卡、分类主卡与白色内嵌区。patterns提供可编辑完整片段，知识/资料按阅读关系编排，不强加人物或营销结构。独立分区48px/H5 34px与卡内8/14/16/26px分别维护。深蓝是有依据时显式选用的变体。

新增--subject-css、record.py init/snapshot/restore及check_html --browser-report；制作与恢复使用同一组合器，不依赖作者业务脚本。浏览器按可见边界/祖先裁切和正文Range检查溢出，报告同SHA五层并单列目标视觉；旧基本可读pass不代表达到参考。手机公共页脚原生折叠，13目标、官方60px/1200px页头和服务降级保留。内容删减与精修例子见workflow，范围与验证以本地PROJECT_OFF及SPEC验收记录为准。

本轮不含真实业务重测、实机、真实账号登录/搜索提交；源开发验证不等于业务页正式交付。安装、GitHub、提交、发布按各自授权处理；实际安装与提交状态以本地PROJECT_OFF为准，公开仓库仍为1.2.1。


本地1.3.0已完成两类视觉局部、三题材整页及全部模块的参考对照，以及十宽往返、动态内容/媒体、视觉与溢出反例、同版报告、隔离运行验证。当前执行者的合成开发验收已通过；未声明独立盲测或任意未来页面自动达标。实际业务/实机范围仍按上节边界与项目恢复记录执行。


## 11. V1.3.1 整页文字层级修订

按用户追加反馈，替换旧38/26/16/14/12的标签固定字号。catalog.typography统一维护页面、模块、主卡、普通卡、重点句、引言、正文与辅助角色；build_shell生成CSS，浏览器按同表检查实际文本。主卡与普通卡保留语义H3但权重不同，必要说明不再用辅助小字；手机通过自然换行和减列保留阅读层级。公共页头/页脚独立维护。实际前后对照、验证与安装状态见本地PROJECT_OFF。

本地开发验证覆盖三题材整页及16模块桌面/H5文字层级、角色字号/字重/行高、长文与动态重排，并拒绝旧16px主卡/14px正文反例。必要内容仍由HTML承载，图片缩略字不因字号检查通过而视为直接可读。真实业务页面与实机需按实际材料复验。


## 12. V1.3.2 制作与验收修复

组合区按内容容量与主次重量重排，支持少项、多项和正文增删；同职责字段可用data-qt-field对齐。检查器直接测可见框体，覆盖cluster、无分组属性的原生组和字段。保留1.3.1角色字号，不用固定高度或缩字消除错位。

新任务初始化包含素材评估；精修前明确复用/生成/混合/无图及理由，未决缺图阻止交付。直接完成指令以execution_authorizations记录，与实际初稿审阅分开；执行权限不自动扩大到图片生成或新增事实。用户未解决的否定反馈会使相应验收层失败，旧通过报告不能覆盖。规则、字段与命令见workflow/content-record/tools。

本地源修复与实际安装状态以PROJECT_OFF为准；业务失败页保留作证据，不随产品分发。本轮不自动安装、提交、推送或发布。


## 13. V1.4.0 制作与成品判断

新任务逐模块评估配图覆盖与缺口，证据截图关联具体主张；连续过程/前后变化核对同一主体、任务与作品。独立元素按需要生成透明背景PNG，核验真实Alpha，原图与网页展示裁切保留双指纹并可原图放大。正文绿色按钮白字、白色按钮ink黑字；操作深绿与品牌识别色分开，hover状态一并检查。新增透明插图和动作/产物字段组件，补充手机与断点目视。

推荐用[check_task](qingteng-topic-html/references/tools.md#保存一轮完整制作与验收)保存每轮完整输入、媒体、HTML与报告，失败轮保留；新版记录使用production_contract=2，旧记录兼容。组合器调用数和任务已到位生成素材数分别报告；内容需独立反向复核，程序不能认证关系声明、审查真实性或用户接受。源开发结果及未测项见本地PROJECT_OFF，合成PNG测试不代表真实生图或业务页已经重做。


## 14. V1.5.0 文字编排与视觉表达

基于真实八模块反馈，先确定具体任务/成果/价值，再选择角色字号、本机展示字体、语义强调色和表面层级。增加图标短词产物、有序动作与成果单元、彩色证据标题/托底和价值贴片，减少重复字段与非必要制作解释；新增image/audio/video原生内容图标。数量与表达按材料选择，长文与必要条件保留，不把固定业务词或三卡写入通用规则。技术检查与人工内容/目标视觉分别验收。

本地源开发与验证状态见PROJECT_OFF；安装仍1.4.0，当前业务HTML和用户否定反馈不因源修订而视作已修复或已接受。本轮不自动安装、提交、推送或发布。


## 15. 七项制作与阅读收口改进（源1.6.0）

320px代表模块预览与标题实际行框；配图解释作用及可见主体/实际图幅；证据相关区域/完整图/原尺寸；角色化图幅与natural异职责回退；作者id提前拒绝冲突；full逐图逐按钮及实际断点/超长模块覆盖；可选SHA字节缓存、媒体导出与耗时/体积报告。preview不作为完整通过，缓存不复用人工判断。源规则与工具见[使用说明](qingteng-topic-html/references/tools.md#快速预览与完整收口)。2026-10-30已按用户明确指令完成本地1.6.0安装；源仍未提交，未推送或发布。


## 1.7 信息保留、对齐与交付结论

源1.7.0保留此前1.6.0能力：案例保留材料支持的具体任务/动作/作品/反馈；解释图按实际尺寸与具体关系判断；证据展示/原图及阅读位置连续。新增标签值与紧凑步骤配方、显式对应起点/跨模块基线/图幅对齐检查；1.7当时允许natural解除异职责等高，1.8已收紧为只保留媒体比例，外框继续对齐。整页构图、卡片重复及2+1仍由实际画面判断，不以填满或固定数量评判。

报告分开production_status、按页面用途的business_information、当前HTML的user_acceptance；completion仅在三者满足时通过。旧记录可恢复但未知用户接受不追认为pass。开发合成回归与独立前向试用不代表真实业务接受。维护测试outcome_regression.py/outcome_browser.mjs留本地，不进入运行Skill；实测结果与边界见当前PROJECT_OFF。

## 1.8 可见边界与公开文案取舍

源1.8.0将natural限定为媒体固有比例，保留并排框体/字段边界检查；自定义内容双栏不能脱离检查，严重图文失衡自动纵排，框内大块撑白与同列照片实际边缘错位会失败。原比例照片列使用qt-t-photo-column；自定义并列可声明data-qt-composition="parallel"。公开提示按是否影响当前理解/操作取舍，未展开的可选方向可省略，真实必要条件保留。后续使用暴露了持续素材要求被覆盖的缺陷，1.9增加独立要求与履约检查；技术通过不能证明素材充分。


## 1.9 素材要求继承与合并

已有AI生成解释图、透明背景和模块覆盖要求保存在独立requirements.json并绑定SHA；重测、调整对齐或删文案不能用none/reuse和空gaps抵消。组合、快照与复核校验AR→IMG覆盖、实际文件和HTML内嵌字节；素材人工判断单列，asset_fulfillment未核对时不称制作通过。无生成要求仍可零生成，旧任务复核前保留not-run。

合并产品远端main的1.2.4分享脚本与公共壳清洗防护，保留本地1.3–1.8的视觉、阅读与对齐改进；分享业务页面仍须单独明确授权，不随Skill发布自动上传业务材料。
