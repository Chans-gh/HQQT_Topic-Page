# 确定性工具

Python 3.9+标准库，无API/密钥。浏览器脚本需要Node.js20+、随包锁定的Playwright及已安装Chromium；缺少时报告未执行，不自动安装/下载。所有命令在任务目录运行，`SKILL` 表示当前Skill目录，`TASK`表示用户允许的任务目录；请按宿主路径替换，不照抄为绝对路径。

首次环境准备与doctor/smoke见 [setup.md](setup.md)；缺浏览器依赖时准确记录未执行，不自动下载。

## 页面模式记录与只读校验

新任务init创建`task.page_mode_contract=1`、pending的`task.page_mode`和空`direction_previews`。执行者读取材料后按[页面模式](page-modes.md)填写结构化state、主/备选、依据/风险和真实用户selection；脚本不调用AI、不替用户选择、不修改记录。

```sh
python3 "$SKILL/scripts/page_modes.py" validate --record "$TASK/record.json" --allow-pending
python3 "$SKILL/scripts/page_modes.py" validate --record "$TASK/record.json"
python3 "$SKILL/scripts/page_modes.py" brief --record "$TASK/record.json"
```

`--allow-pending`只用于材料/清单阶段检查字段形状；组合新任务HTML前必须selected。brief仅返回已选模式在`assets/page-modes.json`中的密度、组件优先级、导航和预览焦点，不生成页面。使用TypeSafe时由宿主按官方Choice/State接口取得推荐并保存概率/confidence；本工具不读取密钥或联网。组件映射是起点，仍按真实信息关系选择C01–C12。

方向预览在清单确认后由执行者用相同已确认内容制作，最多两份，artifact使用任务相对路径并记录SHA。snapshot会复制已渲染预览并相对化；预览选择不是draft审批，不进入final DOM，也不自动分享。

## 制作主体

执行者阅读与编排，手工写 `body.html`；从 `assets/components/patterns.html`复制实际需要的template内部片段并替换示意文案。每个顶层section/article/header必须有`data-module-id`，所有正文均归属模块。一个H1放在开场模块中；其他模块H2、内部H3。不要把原材料HTML/脚本拼进可执行片段；文案用HTML转义或安全文本节点，URL限明确用途的http(s)/锚点。片段不允许script/style/iframe/内联事件/内联style；样式和交互由Skill自有topic.css/js提供，特殊主体布局通过下述--subject-css接口输入并重新检查，不能改公共块。

长标题需要控制语义断行时，可将自然短语分别放入`<span class="qt-t-title-phrase">`，例如“扫描文件，”与“按日期和主题命名”。短语在足够宽时同排，窄屏按实际容量换行，超窄时允许短语内部换行；不全局nowrap、不为每个字插入br，也不假定均衡换行算法能理解中文词义。短标题无需分组，仍须目视实际标题。

每个非omitted素材只放一个空槽`<div data-media-id="IMG-01"></div>`；组合器按记录生成占位或内嵌授权文件。输入图要求reuse审批记录；新生成图在draft中拒绝，在refine/final必须有draft方案和generate范围。素材文件相对路径以记录文件所在目录解析，输出不泄露路径。截图自动具备放大/原尺寸/关闭焦点；人物使用独立矩形槽。不要用占位图冒充到位素材。

来源由`module.sources`核对，与详细supports/note一起只进入draft/refine的内部审阅区；final不生成编号/页尾来源组。不在body手写data-source-id或核验状态。确有必要的公开出处直接写成正常链接和正文，不能复制内部说明充当公开文案。素材必须显式写alt；caption可省略，不从purpose生成。图像编码按文件内容识别，不依赖扩展名。审阅数据由记录生成，不提供批准按钮。要调整清单或文案，先根据真实反馈维护受影响记录版本，再组合。

容量标记：`data-qt-fit=prose/pair/media/person`分别承载文字/观点依据/材料解读/人物组合，默认保持所属边界；确需局部收紧时显式`data-qt-align="compact"`。person最后一个子项为人物，正文在前。三组以上用组或嵌套语义结构。`data-qt-group`按可换行文本的当前字体预算、数量和父容器选择列，组宽保持100%，末行靠前。图片按固有比例参与容量，不读取当前渲染高度形成反馈。空集合使用`<p data-qt-empty>暂无内容</p>`，计数0；不造空卡。移除媒体后回收空列。

`qt-t-media-group qt-t-group`加`data-qt-group`协调双/三媒体；普通同级组的每项均为figure或包含单一figure的卡片时，也会自动启用这一契约。共同媒体槽完整contain，图注等高且可增长，截图自动原图查看。`qt-t-production/qt-t-journey/qt-t-change/qt-t-key/qt-t-outcome/qt-t-evidence/qt-t-scene/qt-t-hero`表达方法见patterns；表达需要实际文案配合，不是给任意长列表加class即可通过。

非图片资源只放空`data-resource-id`槽并在modules.resources/record.resources关联；单文件工具支持真实不可用通知/经明确批准省略或保留通知，不伪造播放器。真实视频包另行审计，不能以本工具pass声称视频通过。混合阶段与输入引用语义见content-record。

## 组合与静态检查

```sh
python3 "$SKILL/scripts/compose_html.py" --record "$TASK/record.json" --body "$TASK/body.html" --mode draft --out "$TASK/draft.html"
python3 "$SKILL/scripts/check_html.py" "$TASK/draft.html" --mode draft --record "$TASK/record.json" --report "$TASK/static-report.json"
```

mode=refine 输出仍可审阅的精修中页面；mode=final 要求DELIVERY阶段、准确的实际审阅或直接执行授权、全部相关事实/素材到位。最终不附加策划/索引/确认状态；作者片段有审阅UI或未解决关键项则拒绝。默认正文与固定代码内嵌单文件，不生成外部资源包；锁定官方页头允许联网。用户明确要求视频/素材包时由执行者按真实资源制作相对路径交付，重新核对依赖及大小；检查器仅在逐字一致的公共块内豁免官方依赖，正文仍拒绝非内嵌运行资源，不能把这类报告当作素材包通过证据。

脚本拒绝写入Skill目录或覆盖body/record；失败先返回错误，不输出半成品，不自动修改记录。原始输入只读。脚本不证明语义、商业数据真实性或授权真实性，不自动转阶段。

## 获准生成的范围计划（零副作用）

```sh
python3 "$SKILL/scripts/compose_html.py" --record "$TASK/record.json" --mode refine --generation-plan --modules M01 M03
```

输出eligible/blocked编号，永不执行生成。执行者逐个核对真实指令，用当时用户认可且可用的工具处理eligible方案；成功后记录实际来源、文件指纹和素材状态。失败留pending，不用无关图顶替。当前Skill开发验收使用内存替身记录调用，禁止真实生成。

## 浏览器实测

```sh
node "$SKILL/scripts/check_browser.mjs" "$TASK/draft.html" "$TASK/browser-report"
```

如Playwright不在默认模块路径，设置`QT_PLAYWRIGHT_MODULE`为宿主可用的Playwright入口文件；如需使用现成Chromium，可设置`QT_CHROMIUM_EXECUTABLE`。只采用实际存在的运行时，不依赖特定本机路径。报告区分pass/fail/not-run和五层结果，绑定HTML/截图SHA；full输出十视口及指定宽度往返几何、全页和全部模块截图，含700/1000两侧；preview仅输出指定范围，详见下节。组边界/同排底线/已声明媒体槽及图注按2px检查。natural只保留媒体固有比例，不豁免框体；自定义内容双栏未声明时报unregistered-composition，确需自定义并列时使用data-qt-composition="parallel"，作者CSS仍负责重排。大块框内空尾报peer-content-balance，严重图文高差报composition-balance，同列photo实际边缘错位报photo-column-edges。qt-t-evidence按内容高差回退纵排，qt-t-photo-column提供等宽、原比例的照片连续列；这些几何门槛不证明构图美观。content/visual默认not-run，需执行者目视另记，不能由自动结果赋pass。检查覆盖全部标题字号及普通纯色背景文字对比度，渐变/背景图等无法可靠计算的情况列为需人工检查；不认证伪元素、图片内文字、叠层及复杂合成背景。截屏前等待正文图片解码，长模块扩大捕获视口，超过安全捕获高度时按连续区间分段保存，仍需逐图目视完整性。浏览器脚本默认联网，按官方域名范围核对页头/页脚互动与正文布局；--offline仅验收降级，不声称真实搜索或登录通过，关系/事实/密度/人物安全区仍须目视。仅Chromium通过不能说Safari/iOS/Android实机通过。


## 绑定人工内容与视觉审查

需要汇总实际审查时，使用`check_html.py PAGE --mode final --record RECORD --review REVIEW --report REPORT`。REVIEW放任务目录，其`html_sha256`必须对应当前PAGE；`layers.content`和`layers.visual`各写status、scope、evidence。evidence为`{模块ID: 实际判断与发现/处理}`，pass必须覆盖本页全部模块；不要套用“已检查，没问题”。visual.pass另有screenshots数组，各项为`{"path":"相对REVIEW目录的截图路径","sha256":"实际文件SHA"}`，覆盖桌面/H5全页及逐模块审查；工具核对文件指纹，执行者核对审查覆盖。

人工fail会使汇总检查失败；未执行仍not-run；过期HTML、截图被改或pass缺少模块依据会被拒绝。该接口只采用执行者判断并核对关联，无法判断一句结论是否真实可信，也不自动批准交付。正式交付仍需五层实际通过，浏览器报告的scope/未执行项继续保留。

## 页头组件维护

仅在明确修改Skill源时，编辑assets/header/中的HTML/CSS/JS；随后运行`python3 scripts/build_shell.py`与`python3 scripts/build_shell.py --check`。模板保留页脚与五公共块，生成区不手改。build_shell自动更新相关资产与公共块指纹；新增资产仍需登记provenance。页头采用官方源码适配版，1200px上限/60px高度；联网状态与真实登录限制见visual-spec第13节。


## 主体CSS、任务初始化与版本快照

`compose_html.py --subject-css "$TASK/subject.css"`在通用组件后内嵌自定义CSS。每条选择器必须以`.qt-t-topic .qt-u-名称`开始，只支持平面规则和普通类/标签/关系/简单伪类；自定义变量仅--qt-u-*。不支持@规则、转义、url资源、!important、公共类、全局选择器、fixed/sticky和隐藏横向错误。它是有意限制的制作接口，不是任意CSS净化器；响应式优先用已有组件，复杂能力在Skill源开发中验证。例：

```css
.qt-t-topic .qt-u-note { border:1px solid #CDEEE1; padding:16px; }
```

新任务与快照均写入新目录，拒绝覆盖；init只创建INTAKE记录与空片段，不造批准。确认后的记录仍由执行者按真实反馈填写。

```sh
python3 "$SKILL/scripts/record.py" init --out "$TASK" --id TOPIC-01 --title "专题名称"
python3 "$SKILL/scripts/record.py" snapshot "$TASK" --out "$VERSIONS/D01" --files record.json body.html subject.css draft.html
python3 "$SKILL/scripts/record.py" restore "$VERSIONS/D01" --out "$RESTORED"
```

--files明确列出该版本完整输入（没有CSS就不列）；快照自动复制record引用的媒体，改为相对media路径，逐文件SHA写snapshot.json。restore先验证所有指纹与路径，复制到新目录，可继续用同一compose接口制作。批准记录保留而不新增；独立HTML也应列入快照，以保留当时公共壳。快照不冻结Skill运行时，恢复后重组可能因Skill升级改变公共块，须按shell_migration规则记录；旧HTML保持可打开，不生成作者机器专用构建脚本。

## 同版五层汇总

```sh
python3 "$SKILL/scripts/check_html.py" "$TASK/draft.html" --record "$TASK/record.json" --review "$TASK/manual.json" --browser-report "$TASK/browser-report/report.json" --report "$TASK/summary.json"
```

content/visual继续按逐模块evidence与screenshots绑定。visual中新增target：status、reference和dimensions（atmosphere/palette/icons/surfaces/rhythm/focus六项实际观察）；没有目标评审时target not-run，旧基本可读pass不等于目标达标。delivery可由执行者填写status、scope和evidence，说明实际参与条件/资源是否齐全；不能从draft或技术pass推定。summary.status是已提供检查结果；production_status要求五层和目标视觉都pass，completion_status另须用途信息完备和当前用户接受；缺报告保留not-run，HTML/截图过期或任何fail均阻断。工具只核对报告关联，不证明人工判断真实。

公共页脚的唯一源也在public-shell.html；修改后同样运行build_shell和--check，更新指纹。官方页头来源文件保持独立生成，不能用业务CSS覆盖。手机端原生details折叠，桌面全部展开；目标集合不变。


## 文字角色与生成

语义H3不再只能16px。主卡标题自动用feature 24/22px，普通卡card 20/18px，重点句使用`class="qt-t-emphasis"`或`data-qt-type="emphasis"`；必要说明仍16px正文。显式视觉角色不改变H1/H2/H3层级，也不能将关键文案降成meta来缩短卡片。

修改catalog.json中的typography后运行`python3 scripts/build_shell.py`，从唯一表生成topic.css角色区并更新指纹；`--check`及doctor同时核对生成一致性。不要手改QT_TYPOGRAPHY标记内CSS。浏览器按角色及继承关系检查实际文本字号，而非仅按H标签匹配旧值；整页层级仍需人工实际审查。


## 组合对齐与制作收口

qt-t-cluster按内容重排；group/production组件类名无需依赖data-qt-group才能被运行时及检查器识别。对同职责字段，按相同顺序使用data-qt-field="title|summary|detail"等稳定名称，涵盖前置的可变高元素；不要为不同含义的文本强行共用字段。高度来自当前行实际内容，纵排时回收。scripts/browser_layout.mjs是可序列化的可见框体/字段检查，check_browser自动调用。

新任务init已含production_contract和asset_review待评估状态。先完成真实素材决定，再进入refine；直接制作权限按content-record的execution_authorizations填写。生成计划仍是零副作用：工具只返回eligible，执行者必须使用当前可用图片工具落实并保存结果，不能把计划输出当已生成。

用户指出失败时登记feedback再调用check_html；即便旧人工/浏览器报告pass，未解决反馈仍使汇总fail。compose_html允许输出结构有效的修订候选用于检查，输出包含completion_status和unresolved_feedback；文件生成不等于交付通过。修订后根据实际字节与复验填写resolution，重新汇总。


## 保存一轮完整制作与验收

推荐入口（SKILL/TASK/ROUNDS替换为当前实际目录，ROUNDS是TASK外的兄弟目录）：

```sh
python3 "$SKILL/scripts/check_task.py" --record "$TASK/record.json" --body "$TASK/body.html" --subject-css "$TASK/subject.css" --mode final --out-dir "$ROUNDS/R01" --browser
```

无自定义CSS时省略--subject-css。输出目录必须是全新目录，位于任务源与Skill之外，不重用R01；修改后用R02。每轮保存page.html、inputs/自包含快照（正文、CSS、record及原图/展示图）、record-original.json、assets.json、report.json和round.json逐文件SHA；浏览器附browser/artifact.html、报告和截图。结构失败保留可取得的输入，用户否定但结构有效的失败轮仍保留HTML。工具不写回源记录，不生成图片，不安装依赖。

--review可合并已完成的同SHA人工报告，工具将其截图复制到轮次目录；--browser调用现有Chromium检查，--offline仅与--browser合用且只代表降级。只有提供实际制作人工报告与全部验证证据，production_status才可能pass；completion_status另需用途信息与当前用户接受；静态pass不代表内容完成。检查器仅对真实application/json脚本节点提示私有数据检查，公共脚本里的类型字符串不再误报。

素材生成由执行者使用已获准工具完成。组合器输出composer_generation_calls=0与task_generated_assets（记录中已到位生成素材数），后者不认证供应方实际调用次数。PNG透明、生成记录、衍生图和原图SHA由production.py在组合与check_task中统一核验；原图与展示图分别以实际MIME内嵌，放大显示原图，原尺寸与焦点恢复不变。

主体CSS支持安全的子代/相邻关系选择器，如`.qt-t-topic .qt-u-note > p`；仍限制自有作用域、禁止活动CSS与公共结构覆盖。新增`qt-t-illustrated`（正文+透明插图）和`qt-t-tasks`/`qt-t-result`（动作与产物字段）完整片段见patterns；手机优先使用已有响应式组件，避免逐页重写补丁。


## 文字编排组件

patterns的editorial-opening、artifact-symbols、visual-stages、tonal-evidence、value-tiles给出通用结构。`.qt-t-display`只切换本机展示字体栈，`.qt-t-accent/.qt-t-highlight`用于语义短语；`.qt-t-task-heading`按feature角色生成字号。`.qt-t-artifacts`与`.qt-t-group`组合承载短词图标组，普通长文项自动回到容量单列；`.qt-t-production.qt-t-stages`保留顺序并给每步独立表面，成果以artifact单元就近呈现。`.qt-t-panel/.qt-t-panel-head/.qt-t-value-card`复用分类色与静态阴影，不能通过类名自动获得“设计通过”。image/audio/video为新增原生内容图标，非图片生成、品牌Logo或业务证据。


## 快速预览与完整收口

统一入口保持check_task，--profile默认full。快速preview仍保存独立完整输入快照与页面，浏览器只做早期检查，默认320px首屏/实际任务/媒体代表模块；--modules M01 M03可选代表模块，--widths 320 390可指定宽度。没有该类模块不会造空模块。full禁止缩小模块范围，默认十宽往返，并保存1440/1001/1000/768/701/700/390/320全部模块；--widths增加实际变化宽度并保存对应全部模块。浏览器命令的列表使用逗号，check_task使用空格。

```sh
python3 "$SKILL/scripts/check_task.py" --record "$TASK/record.json" --body "$TASK/body.html" --mode refine --out-dir "$RUNS/P01" --browser --profile preview --widths 320 --asset-cache "$CACHE"
python3 "$SKILL/scripts/check_task.py" --record "$TASK/record.json" --body "$TASK/body.html" --mode final --out-dir "$RUNS/R01" --browser --profile full --widths 833 --asset-cache "$CACHE" --export-media
node "$SKILL/scripts/check_browser.mjs" "$TASK/page.html" "$TASK/preview" --profile preview --widths 320,390 --modules M01,M03
python3 "$SKILL/scripts/export_media.py" "$TASK/page.html" --out-dir "$TASK/media-export"
```

$RUNS与$CACHE放本任务的独立目录，不能在Skill内；新轮目录不得存在。preview技术pass的completion仍not-run，合并器也不接受它作为完整layout/function通过。full只代表完整技术范围，人工content/visual/delivery以及用户接受继续按真实证据分别处理。--offline含义不变。

browser报告coverage列实际模块/全部正文button和按钮链接的default/hover、全部证据图的相关区域/完整图/原尺寸与焦点；reading列标题实际行框和媒体几何待目视；captures列各模块每宽度的完整高度及分段区间。窄宽超长模块分段保存，检查连续覆盖；未测试内容不补pass。timings报告测量/截图/交互/总耗时，check_task另报告快照/组合/复核/浏览器耗时、snapshot_bytes/html_bytes与缓存命中。

--asset-cache可选。仅缓存当前素材SHA+production检查器SHA的PNG字节检查，条目有内容校验；同进程也复用相同编码，不重复扫描Alpha。仅用可信本地缓存，损坏重算；原始文件仍逐次读取SHA。换图、改检查器或破坏条目均不复用；任何缓存均不认证图意、批准或人工审查。省略该参数时不产生持久缓存。快照中相同SHA素材仍按既有机制去重；导出工具对已有内嵌媒体按SHA去重，manifest分别标展示版/原图及字节，不裁切、不生成、不压缩、不覆盖输入。工具不自动删除失败轮或历史快照。


## 交付结论与用途范围

check_html/check_task汇总三项。`production_status`为五层制作检查及target视觉的pass/fail/not-run；`business_information`为按真实用途的信息完备度；`user_acceptance`为当前HTML实际用户决定。顶层status表示已提供检查/审阅是否失败，不表示整页已完成；业务缺项可保留候选的制作pass。`completion_status`仅当production pass、business complete或not-applicable、user accepted时pass；任一制作失败或用户rejected为fail，其余not-run。CLI只因status fail返回非零，不能用退出码0推定交付完成。

review仍绑定html_sha256，在原layers之外加入：

```json
{
  "outcome": {
    "business_information": {
      "status": "complete",
      "scope": "知识介绍：说明识别步骤和适用范围，不提供办理服务",
      "evidence": "本用途所需步骤、条件和材料均在正文；无报名目的",
      "missing": []
    },
    "user_acceptance": {"status": "not-reviewed", "scope": "当前HTML待实际审阅"}
  }
}
```

business状态为complete/incomplete/not-applicable/unknown。非unknown须有scope、evidence及missing数组；incomplete须列具体缺项，complete/not-applicable不得仍有缺项。not-applicable说明为何本次用途不涉及该类业务信息，不得用于隐藏实际办理需要的信息。介绍页只按介绍所需信息判断；办理/报名页按其真实目标核对条件、费用、排期和入口，不凭模板补造。缺评审时unknown；制作检查不要求自动编出这些信息。

user状态为accepted/rejected/not-reviewed/unknown。accepted或rejected须有scope与evidence对象，含`actor:"user"`、实际对话/记录定位`locator`、用户原话`text`、被审阅成品的`html_sha256`。不能将执行者自评、测试替身、直接制作授权或旧版接受填为当前用户决定；无实际定位就保留not-reviewed/unknown。工具核验字段及SHA，不能验证发言真实性或判断正确性。

旧record/review继续可读；没有outcome的历史报告按unknown汇总，不继承旧的总completion通过。无效/过期review清除所附outcome，拒绝留下accepted。修改页面后重新取证；旧失败轮保留。阅读几何报告新增reading.composition的章节坐标与分组行框，提供构图目视线索；显式baseline/anchor/facts/media-align错位为layout失败，未声明的关系不被自动视为正确。

## 分享（仅限用户明确要求）

分享是对外发布动作：不随交付自动执行，只在用户明确要求对指定文件分享时运行；用户在任务内预先明确授权“交付后自动分享”的，视为该次明确要求。前置条件：Node.js 18+；`QINGSHUI_API_KEY`从环境变量读取（也支持skill根目录或当前目录`.env`，真实环境变量优先），可选`QINGSHUI_BASE_URL`覆盖服务地址。本Skill不含任何密钥；未配置时报告未执行并停止，不代用户注册或猜密钥。分享脚本已内置：`scripts/share/`（share.js 与 bundle-html.js，源自青水skill v1.2.3 @8d187e9、MIT许可，仅迁移share/assets/unshare与打包清洗逻辑，图片/视频/语音生成能力未迁移），Node直接运行，无第三方依赖、不经npx/npm。

**第一步：生成分享适配副本**（只写副本，不改交付文件）：

```sh
python3 "$SKILL/scripts/prepare_share.py" --input "$TASK/final.html" --out "$TASK/final-share-ready.html" --report "$TASK/share-prep-report.json"
```

分享服务与CLI不接受组合页的部分内容，必须先清洗：CLI图片白名单仅收PNG/JPEG/GIF/WebP，拒绝下载远程SVG（官方页头品牌图标即远程SVG）；服务端拒绝iframe/object/embed/video/audio/math等标签（页头官方搜索层是iframe）以及含外部引用的CSS。服务端还会移除button；专题页放大图原本位于`button[data-qt-zoom]`内，直接清洗可能把后代图片一并移除。prepare_share.py只在副本中把该单图按钮解包为静态`img`，同时把远程图片内联为data URI（SVG保留为data:image/svg+xml，交服务端白名单清洗）、移除script块之外的真实iframe，脚本内容不动；原交付页仍保留放大能力。JSON报告增加`zoom_buttons_unwrapped`，并继续报告内联数、iframe数、下载失败与遗留引用；存在遗留时如实说明再继续。服务端接受内联SVG数据（含模板Logo）与位图data URI，无需替换品牌资产。

**第二步：本地预检适配副本**（不上传、不需要API Key）：

```sh
node "$SKILL/scripts/share/share.js" preflight "$TASK/final-share-ready.html"
```

`preflight`执行与正式分享相同的打包，检查10MB硬上限、遗留的`data-qt-zoom`按钮、内联位图数量和像素规模。位图累计超过约800万像素时给出风险警告：青水可能把WebP/JPEG重编码为PNG，导致本地文件小于10MB但“清洗后的HTML”超过上限。该判断是保守提示，不是服务端结果的替代；有风险时用接近页面展示尺寸的派生图，原图另行保留。阻断项修复后再上传。

**第三步：上传适配副本**：

```sh
node "$SKILL/scripts/share/share.js" share "$TASK/final-share-ready.html" --name "页面名称"
node "$SKILL/scripts/share/share.js" assets
node "$SKILL/scripts/share/share.js" unshare <hash>
```

`share`默认打包内联、对放大图按钮做同样的静态降级、剥离@font-face并注入沙箱存储垫片；即使漏跑prepare_share.py，也不会把单图放大按钮原样交给服务端。`--keep-svg`把自包含内联SVG保留原样交服务端清洗；`--no-bundle`用于已是单文件且无外部引用的页面；`--no-scripts`禁脚本（**成品专题页禁止使用，见下条**）；`--no-fetch`不下载远程资源（有远程引用时报错）。服务地址默认 `https://qingshui.hqwx.com`，白名单 qingshui.hqwx.com / qingshui.hqqt.com（含子域名），非白名单域名直接拒绝。成功输出分享URL、32位hash与MIME类型，URL形如`https://<平台域名>/{project}/{user}/{hash}.html`——这是沙箱包装页，原始内容在同URL加`?raw=1`（仅iframe请求头返回）。输出中的⚠️清洗警告（如移除button/input/form标签）逐条如实转述用户；把URL与hash回传，并按[记录约定](content-record.md)可记入`task.share`，该记录不替代用户授权证据。

**硬约束：成品专题页禁止 `--no-scripts`。** 卡片列宽（`--qt-cols`）与媒体槽位（`--qt-media-slot`）由 `assets/components/topic.js` 在运行时按视口计算并写入自定义属性；禁用脚本后这两个变量停在默认值 1，`.qt-t-group` 退化为单列、图文组宽度塌陷成窄条，文字逐字竖排贴至右侧——页面看起来像样式全坏了，但本地交付文件完全正常，极易误判为模板缺陷。若分享页出现脚本报错，应修正报错来源（页头 `form`/`input`/`button` 被服务端清洗时的空值防护已在公共外壳脚本中处理），不得改用 `--no-scripts` 规避。分享后必须实测：JS 报错数、每模块网格列数、section 实际宽度。

分享页运行在平台CSP沙箱iframe中：脚本不能发起网络请求、读本站Cookie/存储或顶层跳转，官方页头的搜索、账户与表单交互在分享链接中被服务端移除或降级，与本地浏览器验收不同；如实说明，不以分享链接替代本地验收或官方服务检查。用户要求撤回时执行`unshare <hash>`并复测URL失效（取消后短期内有缓存延迟，报告实际状态）。命令失败（网络、鉴权、大小或格式限制）如实返回错误，不重试到成功、不伪造URL，不把失败当交付。


## 素材履约与要求继承（1.9）

init创建独立requirements.json（pending）；执行者先核对真实当前与历史要求，填checked、持续要求和实际AR→IMG绑定，再将文件SHA-256写入record.task.requirements_sha256。格式见content-record“持续素材要求”。compose/check_task从任务目录读取；check_html从--record的同目录读取；generation-plan也使用同目录。不得在record中另填“无要求”覆盖此文件。

每轮check_task与snapshot自动携带requirements.json及SHA，修改后仍写新轮。check_html核对要求覆盖、生成记录、实际素材/内嵌字节，人工review的layers.visual.asset_review补每个有效AR的具体素材判断。报告asset_fulfillment独立于浏览器layout/function；未核对为not-run、缺图/错误字节为fail，均不能制作pass。旧记录可读、旧HTML不变，但不能自动追认素材履约。

本工具不调用生成服务、不默认要求固定图数，也无法认证用户证据或AI服务调用真实性。正式业务必须按真实授权使用宿主生成工具，实际PNG、提示词、SHA与图片作用随后进入任务记录，不用合成测试图片冒充业务素材。
