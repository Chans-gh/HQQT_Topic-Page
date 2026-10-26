# 首次环境检查与安装后更新

获取/安装步骤见[仓库README](https://github.com/Chans-gh/HQQT_Topic-Page#readme)；安装对象为完整`qingteng-topic-html`目录。新机器需要自己的仓库访问权限和Codex，不能依赖作者会话的GitHub连接。已安装目录存在时先保留、比较和备份，不直接覆盖本地修改。

在安装目录运行：

```sh
python3 scripts/doctor.py
python3 scripts/smoke_test.py
```

Python3.9+只用标准库；Windows可用`py -3`替代`python3`。基础doctor为只读；smoke仅在临时目录生成合成记录/页面并自动清理，或用`--out`保存到Skill外的新/空目录。两者不会安装依赖、联网查证、生成图片或伪造真实授权。

浏览器验收使用Node20+。首次由用户明确选择配置后执行：

```sh
npm ci --ignore-scripts --no-audit --no-fund
npx --no-install playwright install chromium
python3 scripts/doctor.py --browser
python3 scripts/smoke_test.py --browser
```

npm ci使用随包锁定的Playwright；Chromium是单独下载的浏览器。没有配置时仍可完成内容与Python静态工作，但不得声称浏览器验收通过。Linux系统库不足时由环境维护者按Playwright官方文档处理，不自动sudo。宿主生图/联网能力与这些本地依赖独立，无内置API密钥。

已有宿主运行时可用环境变量`QT_PLAYWRIGHT_MODULE`指向实际存在的Playwright入口，`QT_CHROMIUM_EXECUTABLE`指向现成Chromium可执行文件；Windows PowerShell用`$env:变量名`配置，POSIX shell用`export 变量名`。不在Skill中硬编码作者路径。doctor的browser模式实际启动并退出浏览器，报告所用来源。

GitHub更新不会自动刷新已安装目录。作者在源项目提交并定向同步，使用者重新获取/备份后更新自己的Skill。首次使用显式调用`$qingteng-topic-html`；如未发现新增Skill，按[官方说明](https://learn.chatgpt.com/docs/build-skills)重新启动Codex。不要将临时业务生成物或依赖缓存提交为Skill源文件。
