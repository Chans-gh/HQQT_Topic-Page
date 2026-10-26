# HQQT Topic Page

环球青藤专题页 Skill `qingteng-topic-html` V1.0.0。将文字、链接、文件、视频或图片材料整理为可确认的内容清单，再制作统一品牌的 Web/H5 独立专题 HTML。

## Skill 入口

- [SKILL.md](qingteng-topic-html/SKILL.md)
- [业务流程](qingteng-topic-html/references/workflow.md)
- [视觉与组件规则](qingteng-topic-html/references/visual-spec.md)
- [工具使用](qingteng-topic-html/references/tools.md)
- [交付检查](qingteng-topic-html/references/quality-checks.md)
- [资产及规则溯源](qingteng-topic-html/assets/provenance.json)

## 工作流程

材料读取与整理 → 拟呈现内容清单 → 用户确认清单版本与范围 → HTML 初稿 → 用户确认初稿及相关素材方案 → 精修 → 验收交付。

支持部分确认、稳定编号、单项修订与恢复。默认可联网补充公开资料，先查证、后确认采用；不编造内部价格、权益、排期、人物资历或效果。清单与初稿阶段不生成新图；精修只处理明确获准方案。

## 实现与验证

原生 HTML/CSS/JavaScript，默认独立单文件；1200px 上限，1000/700px 断点，固定品牌与字号。随包公共模板、C01–C12 语义片段、内容容量适配、审阅展示、媒体查看和局部浏览工具。公共入口保留15个原型目标，不接入真实搜索、客服、交易或账号服务。

Python 3.9+ 工具负责确定性组合与静态检查；可用的 Node.js/Playwright/Chromium 负责浏览器验证。脚本核对执行者记录的版本与范围，不能证明用户授权真实性，也不代替内容取舍或事实核验。

2026-10-26 本地验收覆盖 F01–F12、来源/图像修订与省略扩展，数量与十视口、长短混合容量、横纵局部浏览，以及展示/讲解/资料三类不同完整页。Chromium离线检查与桌面/H5截图目视通过。Safari、iOS、Android实机与真实图片生成服务未测试；本轮真实生图调用为0。

## 仓库范围

`qingteng-topic-html/` 是完整独立 Skill，共34个文件；无需旧Skill、来源仓库或原始项目目录即可使用。输入材料、任务记录、生成专题、临时截图/报告和密钥不应写入Skill源目录。

本仓库仅保存该Skill的分发快照。源码来自本地项目库已提交的独立产品包，内容从锁定视觉/流程基线有意识移植，版本关系为 VARIANT；不替代视觉基础包。规则与资源出处见 provenance.json。此仓库不包含本地治理库的其他项目、分支历史或内部交接记录。

创建远程仓库仅用于用户授权的代码备份与协作；未自动安装Skill或发布到市场。
