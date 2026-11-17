# 多格式输入与读取范围

V2.2 将文本、飞书、DOCX、PDF、表格、网页、图片、视频和混合材料统一为 `qt-input-source/1`。Skill 记录宿主实际使用的连接器、解析、OCR、转写或视觉阅读结果，不自称拥有未配置的解析器，也不从文件名猜内容。

## 记录结构

```json
{
  "id": "A01",
  "schema": "qt-input-source/1",
  "revision": 1,
  "kind": "pdf",
  "locator": "用户附件定位",
  "original_name": "资料.pdf",
  "local_path": "inputs/资料.pdf",
  "sha256": "实际文件指纹",
  "extraction": {
    "status": "partial",
    "method": "parser",
    "read_scope": ["1–12页文本层", "表格2的可见表头"],
    "unread_scope": ["13–15页为模糊扫描"],
    "structure_loss": ["双栏页的阅读顺序需目视复核"],
    "media_status": "indexed",
    "attachments": [{"id":"A01-ATT-01","status":"referenced","locator":"第6页图1"}],
    "errors": []
  }
}
```

`complete` 表示本次声明的整个输入范围已读且没有未读范围；它不证明文件中的主张真实。`partial` 必须同时写已读和未读范围。`blocked` 写权限、密码、清晰度或工具限制。`not-run` 只能留在材料接收阶段，组合 HTML 前会被拒绝。

## 适配边界

- `assets/input-sources.json` 只给出宿主能力路由与核对项；不联网、不解析、不读密钥。
- 飞书折叠块、子节点和附件，表格筛选/隐藏行列，PDF 双栏/扫描，DOCX 修订/批注，视频音轨/画面要分别写入范围。
- 原始文件有 `local_path` 时绑定 SHA256；任务 snapshot 将它复制到 `inputs/`并重写为自包含相对路径。
- 读取范围只证明执行者获取了哪些材料；来源核验、内容采用、页面模式选择和用户确认仍分开记录。
