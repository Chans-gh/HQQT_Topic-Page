# 确定性工具

Python 3.9+标准库，无API/密钥。浏览器脚本需要Node.js20+、随包锁定的Playwright及已安装Chromium；缺少时报告未执行，不自动安装/下载。所有命令在任务目录运行，`SKILL` 表示当前Skill目录，`TASK`表示用户允许的任务目录；请按宿主路径替换，不照抄为绝对路径。

首次环境准备与doctor/smoke见 [setup.md](setup.md)；缺浏览器依赖时准确记录未执行，不自动下载。

## 制作主体

执行者阅读与编排，手工写 `body.html`；从 `assets/components/patterns.html`复制实际需要的template内部片段并替换示意文案。每个顶层section/article/header必须有`data-module-id`，所有正文均归属模块。一个H1放在开场模块中；其他模块H2、内部H3。不要把原材料HTML/脚本拼进可执行片段；文案用HTML转义或安全文本节点，URL限明确用途的http(s)/锚点。片段不允许script/style/iframe/内联事件/内联style；样式和交互由Skill自有topic.css/js提供，特殊业务布局可在既定规则内调整代码并重新检查。

每个非omitted素材只放一个空槽`<div data-media-id="IMG-01"></div>`；组合器按记录生成占位或内嵌授权文件。输入图要求reuse审批记录；新生成图在draft中拒绝，在refine/final必须有draft方案和generate范围。素材文件相对路径以记录文件所在目录解析，输出不泄露路径。截图自动具备放大/原尺寸/关闭焦点；人物使用独立矩形槽。不要用占位图冒充到位素材。

来源由`module.sources`生成支持引用与独立查证/采用状态；不要在body手写data-source-id或重复审批状态。审阅数据由记录生成，不提供批准按钮。要调整清单或文案，先根据真实反馈维护受影响记录版本，再组合。

容量标记：`data-qt-fit=prose`用于可收紧的纯文字组合；`pair`用于观点/依据；`media`用于材料/解读；`person`的最后一个子元素是人物，正文在前。子元素应是与关系匹配的两个组合，三组以上用组或嵌套语义结构。同级组`data-qt-group`根据真实文字与父容器计算宽度和列数；不是固定文本框宽度。局部滚动集合为空时使用`<p data-qt-empty>暂无内容</p>`标记空状态，计数为0；不要用一张空卡充当真实项目。对齐比较/资料字段保留关系，不能为收紧破坏跨项对齐。无媒体时删除对应槽，容量层自动回收空间。

## 组合与静态检查

```sh
python3 "$SKILL/scripts/compose_html.py" --record "$TASK/record.json" --body "$TASK/body.html" --mode draft --out "$TASK/draft.html"
python3 "$SKILL/scripts/check_html.py" "$TASK/draft.html" --mode draft --record "$TASK/record.json" --report "$TASK/static-report.json"
```

mode=refine 输出仍可审阅的精修中页面；mode=final 要求DELIVERY阶段、准确初稿确认、全部相关事实/素材到位。最终不附加策划/索引/确认状态；作者片段有审阅UI或未解决关键项则拒绝。默认全部内嵌、独立单文件，不生成外部资源包。用户明确要求视频/素材包时由执行者按真实资源制作相对路径交付，重新核对依赖及大小；当前严格单文件检查器会拒绝非内嵌运行资源，不能把这类报告当作素材包通过证据。

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

如Playwright不在默认模块路径，设置`QT_PLAYWRIGHT_MODULE`为宿主可用的Playwright入口文件；如需使用现成Chromium，可设置`QT_CHROMIUM_EXECUTABLE`。只采用实际存在的运行时，不依赖特定本机路径。报告区分pass/fail/not-run，输出十视口几何与桌面/H5全页截图。浏览器脚本做确定性互动和离线检查，关系/事实/密度/人物安全区仍须目视。仅Chromium通过不能说Safari/iOS/Android实机通过。
