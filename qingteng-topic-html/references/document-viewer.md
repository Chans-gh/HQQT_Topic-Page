# 目录与原始文档浏览

V2.3 将多页目录/资料的呈现分为三种策略：

- `content-redesign`：把已读信息重组为原生 HTML，适合快速理解和行动。
- `source-viewer`：原页版式、页序或图表样貌本身需要核对，以已取得的页图为主体。
- `hybrid`：先给编辑后摘要，再给原页供完整核对。

策略在内容清单中说明理由，但不产生清单批准。已选页面模式为`catalog`时，组合前必须明确选一种；其他页面也可在附录使用`hybrid/source-viewer`。没有原稿材料时记`not-applicable`及真实理由。

## 记录

`task.document_viewer_contract=1`，`task.document_strategy` 使用 `qt-document-strategy/1`；已选时保存 mode/rationale/documents。`source_documents[]` 使用 `qt-source-document/1`，每项保存原输入、承载模块、已读页图和未读范围：

```json
{
  "id": "DOC-01",
  "schema": "qt-source-document/1",
  "revision": 1,
  "title": "课程手册",
  "module": "M06",
  "input_ids": ["A01"],
  "unread_scope": ["13–15页扫描模糊，未做页图"],
  "pages": [
    {"id":"DOC-01-P01","number":1,"label":"封面","status":"available","media":"IMG-06","source_locator":"A01第1页"},
    {"id":"DOC-01-P13","number":13,"label":"未读扫描页","status":"unavailable","source_locator":"A01第13页"}
  ]
}
```

页图仍是普通`media[]`，必须归属查看器模块，使用原文件的页码/工作表/帧时间作 `source_locator`。原 PDF/DOCX 由输入快照保留；单文件专题不嵌入外部 PDF 运行库，不把下载失败的原件冒充已可视页。

## HTML 组件

从 `patterns.html#source-document-viewer` 复制 template 内容，按真实页数增删页码锚点和`data-media-id`。所有页均留在 DOM 中：

- 默认是带页码索引的局部纵向浏览区，按钮与 PageUp/PageDown/Home/End 只改变定位。
- “完整展开”移除局部裁切，让页图回到普通纵向阅读流。
- 禁用脚本后，页码索引仍是真实锚点，页图不隐藏；上/下页和展开按钮不冒充可用。
- 分享清洗即使去掉脚本，也不应丢页图。页图体积仍受分享预检的内联位图像素/总体积警告约束。
