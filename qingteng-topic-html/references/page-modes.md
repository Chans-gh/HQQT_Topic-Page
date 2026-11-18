# 页面模式推荐与方向预览

本文件用于材料读取后的页面组织路由。它不增加视觉皮肤，也不替代内容清单确认。模式的唯一机器可读目录是 [page-modes.json](../assets/page-modes.json)。

## 1. 推荐解决什么问题

页面模式回答“读者主要怎样使用这页”，而不是“页面看起来像哪套模板”。固定候选为报告阅读、课程教程、产品目录、运营说明、活动转化；五类都不适配时使用自定义组合。品牌色、公共页头、字号、组件规则和五层验收对全部模式相同。

先读取实际材料，再形成结构化状态：

- `purpose`：页面要帮助读者完成什么判断或行动。
- `audience`：主要读者是谁。
- `next_action`：读完后最合理的下一步；没有行动要求也写“理解/查阅”。
- `material_types[]`：实际读取的材料类型，不把不可读附件算作已取得。
- `evidence_shapes[]`：结论、步骤、指标、原件、案例、价格/权益等实际信息形态。
- `content_scale`：内容规模和章节/对象数量的概括。
- `constraints[]`：未读范围、关键缺项、来源限制、必须保留的页序或业务边界。

## 2. 语义判断与确定性边界

推荐是一个闭集选择。执行者可直接按材料判断；环境已配置 TypeSafe 时，可以把上述结构化状态作为 `state`，用 Choice 在五种主模式与 `custom` 中选择，并保留 `probabilities` 和 `confidence`。候选描述使用 page-modes.json 的 `criteria`；如果可能无一适配，再加一个独立的“是否有任一模式适配”判断。TypeSafe 当前官方模式说明见 [Choice](https://docs.typesafe.ai/primitives/choice.md)、[State](https://docs.typesafe.ai/concepts/state.md) 与 [Confidence routing](https://docs.typesafe.ai/patterns/confidence-routing.md)。

TypeSafe 是可选判断来源，不是运行依赖：

- 不自动安装 SDK，不读取或输出密钥。
- 无服务或低置信时由执行者提出主/备选并说明冲突；不自动进入 HTML。
- 概率表示候选分布，不证明材料完整、模式正确或用户同意。
- 组件映射、阶段限制、审批和验收始终由本 Skill 的记录与确定性脚本执行。
- 阈值必须用代表性专题验证；本 Skill 不写一个未经验证的通用自动执行阈值。

## 3. 推荐记录

新任务 `task.page_mode_contract=1`，`task.page_mode` 包含：

- `schema=qt-page-mode/1`、`status`、`method`。
- 上述 `state`。
- `recommendation.primary/alternative/reasons/risks/confidence/probabilities`。
- `selection.status/mode/evidence`。

`method`可为`executor`、`typesafe`或`user`；pending阶段为`pending`。推荐与选择分开：执行者或模型可以推荐，只有真实用户消息才能写入selection evidence。用户在请求中明确指定“做成课程教程页”等，可直接以该消息作为选择依据；不要求再问同一件事。

推荐至少说明：为什么主模式更适合、备选改变了什么阅读关系、材料缺项会影响哪个模块。页面模式与`task.density`不同：模式决定整页主任务，density决定展示/讲解/资料的局部密度。选择模式后再按实际内容选C01–C12，不按映射表机械堆组件。

运行只读校验与查看映射：

```sh
python3 "$SKILL/scripts/page_modes.py" validate --record "$TASK/record.json"
python3 "$SKILL/scripts/page_modes.py" brief --record "$TASK/record.json"
```

`validate`不修改记录；旧任务没有contract时返回legacy。组合新任务前必须有已选择模式。

## 4. 两个方向预览

内容清单确认后，如方向差异会影响整页组织，可以制作最多两个轻量预览。两份预览使用同一份已确认内容，只比较：

1. 开场如何建立主题、对象和下一步。
2. 一个最能体现差异的代表模块如何组织信息。

预览不生成新事实、图片、价格、权益或入口；不自动分享。方向可以是推荐模式与备选模式，也可以是同一模式下两种组件关系。每份预览记入`direction_previews[]`：`PV-01`起的编号、mode、modules、status，以及渲染后相对任务目录的artifact和SHA。选中/拒绝都记录真实用户证据。

预览选择只锁定页面组织方向，不等于用户已经审阅完整初稿。选择后按同一内容清单制作完整HTML；完整初稿仍需独立确认。用户已明确指定方向或直接委托完成时，可以不制作双预览，并在记录中说明原因。

## 5. 模式适用边界

- 报告阅读不是“米白长文皮肤”；没有结论或证据时先处理内容缺项。
- 课程教程不因出现“课程”二字就成立；必须有实际学习顺序、动作或章节关系。
- 产品目录不等于商品销售页；作品集和资料目录可以没有价格与CTA。选中catalog后再按 [原稿浏览策略](document-viewer.md) 明确是内容重构、原稿浏览还是摘要+原稿；这不是第二次页面模式选择。
- 运营说明中的指标必须有主体、时间、范围和解释，不用大数字补视觉。
- 活动转化只有在真实目的需要时才加入权益、排期与CTA；缺少入口不能伪造按钮。
- 自定义组合必须说明主线和组件关系，不能借此跳过模式判断或品牌规则。
