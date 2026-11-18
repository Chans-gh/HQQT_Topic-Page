#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const css=fs.readFileSync(path.join(root,'assets/components/topic.css'),'utf8');
const runtime=fs.readFileSync(path.join(root,'assets/components/topic.js'),'utf8');
const body=`<main class="qt-t-topic">
 <header id="M01" data-module-id="M01"><h1>长页导航回归</h1></header>
 <nav class="qt-t-page-nav qt-t-stage-nav" data-qt-page-nav aria-label="学习阶段"><div class="qt-t-page-nav-head"><strong>学习阶段</strong><a class="qt-t-back-top" href="#M01">返回开头</a></div><ol class="qt-t-page-nav-list"><li><a href="#M02"><span>Day 01</span><strong>阅读材料</strong></a></li><li><a href="#M03"><span>Day 02</span><strong>完成练习</strong></a></li></ol></nav>
 <section id="M02" data-module-id="M02" style="min-height:900px"><h2>阅读材料</h2><p>内容一直保留在页面中。</p></section>
 <section id="M03" data-module-id="M03" style="min-height:900px"><h2>完成练习</h2><p>后续内容同样保留。</p></section>
 </main>`;
const documentFor=withScript=>`<!doctype html><meta charset="utf-8"><style>${css}</style>${body}${withScript?`<script>${runtime}<\/script>`:''}`;

const launchOptions={headless:true};
if(process.env.QT_CHROMIUM_EXECUTABLE)launchOptions.executablePath=process.env.QT_CHROMIUM_EXECUTABLE;
const browser=await chromium.launch(launchOptions);
try{
 const page=await browser.newPage({viewport:{width:390,height:720}});
 await page.setContent(documentFor(true),{waitUntil:'load'});
 const visibility=await page.locator('#M01,#M02,#M03').evaluateAll(nodes=>nodes.map(node=>getComputedStyle(node).display!=='none'&&!node.hidden));
 if(!visibility.every(Boolean))throw new Error('navigation hid authored sections');
 if(await page.locator('[data-qt-page-nav]').evaluate(node=>getComputedStyle(node).position)!=='static')throw new Error('mobile navigation became sticky/fixed');
 if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw new Error('mobile navigation caused page-level horizontal overflow');
 await page.locator('a[href="#M03"]').click();
 await page.waitForFunction(()=>location.hash==='#M03');
 await page.waitForFunction(()=>document.querySelector('a[href="#M03"]').getAttribute('aria-current')==='location');

 const fallback=await browser.newPage({javaScriptEnabled:false,viewport:{width:390,height:720}});
 await fallback.setContent(documentFor(false),{waitUntil:'load'});
 await fallback.locator('a[href="#M03"]').click();
 if(!fallback.url().endsWith('#M03'))throw new Error('no-script fragment navigation failed');
 const fallbackVisibility=await fallback.locator('#M01,#M02,#M03').evaluateAll(nodes=>nodes.map(node=>getComputedStyle(node).display!=='none'&&!node.hidden));
 if(!fallbackVisibility.every(Boolean))throw new Error('no-script document hid sections');
 await fallback.close();
 console.log('✅ Chromium long-page navigation checks passed');
} finally {
 await browser.close();
}
