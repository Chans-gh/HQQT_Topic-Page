# 确定性工具

Python 3.9+标准库，无API/密钥。浏览器脚本需要Node.js20+、随包锁定的Playwright及已安装Chromium；缺少时报告未执行，不自动安装/下载。所有命令在任务目录运行，`SKILL` 表示当前Skill目录，`TASK`表示用户允许的任务目录；请按宿主路径替换，不照抄为绝对路径。

首次环境准备与doctor/smoke见 [setup.md](setup.md)；缺浏览器依赖时准确记录未执行，不自动下载。

## 制作主体

执行者阅读与编排，手工写 `body.html`；从 `assets/components/patterns.html`复制实际需要的template内部片段并替换示意文案。每个顶层section/article/header必须有`data-module-id`，所有正文均归属模块。一个H1放在开场模块中；其他模块H2、内部H3。不要把原材料HTML/脚本拼进可执行片段；文案用HTML转义或安全文本节点，URL限明确用途的http(s)/锚点。片段不允许script/style/iframe/内联事件/内联style；样式和交互由Skill自有topic.css/js提供，特殊业务布局可在既定规则内调整代码并重新检查。

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

mode=refine 输出仍可审阅的精修中页面；mode=final 要求DELIVERY阶段、准确初稿确认、全部相关事实/素材到位。最终不附加策划/索引/确认状态；作者片段有审阅UI或未解决关键项则拒绝。默认正文与固定代码内嵌单文件，不生成外部资源包；锁定官方页头允许联网。用户明确要求视频/素材包时由执行者按真实资源制作相对路径交付，重新核对依赖及大小；检查器仅在逐字一致的公共块内豁免官方依赖，正文仍拒绝非内嵌运行资源，不能把这类报告当作素材包通过证据。

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

如Playwright不在默认模块路径，设置`QT_PLAYWRIGHT_MODULE`为宿主可用的Playwright入口文件；如需使用现成Chromium，可设置`QT_CHROMIUM_EXECUTABLE`。只采用实际存在的运行时，不依赖特定本机路径。报告区分pass/fail/not-run和五层结果，绑定HTML/截图SHA；输出十视口往返几何、桌面/H5全页和逐模块截图。组边界/同排底线/媒体槽及图注按2px检查。content/visual默认not-run，需执行者目视另记，不能由自动结果赋pass。检查覆盖全部标题字号及普通纯色背景文字对比度，渐变/背景图等无法可靠计算的情况列为需人工检查；不认证伪元素、图片内文字、叠层及复杂合成背景。截屏前等待正文图片解码，长模块扩大捕获视口，仍需逐图目视完整性。浏览器脚本默认联网，按官方域名范围核对页头/页脚互动与正文布局；--offline仅验收降级，不声称真实搜索或登录通过，关系/事实/密度/人物安全区仍须目视。仅Chromium通过不能说Safari/iOS/Android实机通过。


## 绑定人工内容与视觉审查

需要汇总实际审查时，使用`check_html.py PAGE --mode final --record RECORD --review REVIEW --report REPORT`。REVIEW放任务目录，其`html_sha256`必须对应当前PAGE；`layers.content`和`layers.visual`各写status、scope、evidence。evidence为`{模块ID: 实际判断与发现/处理}`，pass必须覆盖本页全部模块；不要套用“已检查，没问题”。visual.pass另有screenshots数组，各项为`{"path":"相对REVIEW目录的截图路径","sha256":"实际文件SHA"}`，覆盖桌面/H5全页及逐模块审查；工具核对文件指纹，执行者核对审查覆盖。

人工fail会使汇总检查失败；未执行仍not-run；过期HTML、截图被改或pass缺少模块依据会被拒绝。该接口只采用执行者判断并核对关联，无法判断一句结论是否真实可信，也不自动批准交付。正式交付仍需五层实际通过，浏览器报告的scope/未执行项继续保留。

## 页头组件维护

仅在明确修改Skill源时，编辑assets/header/中的HTML/CSS/JS；随后运行`python3 scripts/build_shell.py`与`python3 scripts/build_shell.py --check`。模板保留页脚与五公共块，生成区不手改。build_shell自动更新相关资产与公共块指纹；新增资产仍需登记provenance。页头采用官方源码适配版，1200px上限/60px高度；联网状态与真实登录限制见visual-spec第13节。
