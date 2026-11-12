#!/usr/bin/env node
/**
 * 青水静态资源分享（share / assets / unshare）
 *
 * 打包逻辑见同目录 bundle-html.js（保留来源打包逻辑）。
 * 相对源码的两处适配：
 * 1. 默认 QINGSHUI_BASE_URL 为 https://qingshui.hqwx.com；
 * 2. 域名白名单为 qingshui.hqwx.com 与 qingshui.hqqt.com（含各自子域名）。
 */

const https = require('https');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { bundleHTML } = require('./bundle-html');

function loadDotEnv() {
  // 自动读取 .env：skill 根目录（scripts/share/..）优先，其次当前工作目录；真实环境变量优先于 .env
  const candidates = [path.join(__dirname, '..', '..', '.env'), path.join(process.cwd(), '.env')];
  const seen = new Set();
  for (const file of candidates) {
    if (seen.has(file)) continue;
    seen.add(file);
    let text = '';
    try { text = fs.readFileSync(file, 'utf8'); } catch (e) { continue; }
    for (const line of text.split(/\r?\n/)) {
      const t = line.trim();
      if (!t || t.startsWith('#')) continue;
      const m = t.match(/^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/);
      if (!m) continue;
      let val = m[2].trim();
      if ((val.startsWith('"') && val.endsWith('"') && val.length >= 2) ||
          (val.startsWith("'") && val.endsWith("'") && val.length >= 2)) {
        val = val.slice(1, -1);
      }
      if (!(m[1] in process.env)) process.env[m[1]] = val;
    }
  }
}

function getConfig() {
  const apiKey = process.env.QINGSHUI_API_KEY || '';
  const rawBaseUrl = (process.env.QINGSHUI_BASE_URL || 'https://qingshui.hqwx.com').replace(/\/+$/, '');

  if (!apiKey) {
    console.error('❌ 错误：未设置 QINGSHUI_API_KEY 环境变量');
    console.error('请执行: export QINGSHUI_API_KEY=qs-your-key');
    process.exit(1);
  }

  // 强制 HTTPS
  const url = new URL(rawBaseUrl);
  if (url.protocol !== 'https:') {
    console.error('❌ 安全错误：QINGSHUI_BASE_URL 必须使用 HTTPS 协议');
    console.error('当前: ' + rawBaseUrl);
    process.exit(1);
  }

  // 域名白名单：仅允许 qingshui.hqwx.com / qingshui.hqqt.com 及其子域名
  const allowedHosts = ['qingshui.hqwx.com', 'qingshui.hqqt.com'];
  if (!allowedHosts.some(h => url.hostname === h || url.hostname.endsWith('.' + h))) {
    console.error('❌ 安全错误：QINGSHUI_BASE_URL 域名不在白名单中');
    console.error('域名: ' + url.hostname);
    console.error('允许: ' + allowedHosts.join(', '));
    process.exit(1);
  }

  return { apiKey, baseUrl: rawBaseUrl };
}

const API_TIMEOUT_MS = 30 * 1000;       // JSON API 请求空闲超时
const UPLOAD_TIMEOUT_MS = 120 * 1000;   // 文件上传空闲超时

function apiRequest(method, apiPath, data = null) {
  const { apiKey, baseUrl } = getConfig();
  const url = new URL(apiPath, baseUrl);
  const options = {
    hostname: url.hostname,
    port: url.port ? Number(url.port) : 443,
    path: url.pathname + url.search,
    method,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
      'X-API-Key': apiKey,
    },
  };
  return new Promise((resolve, reject) => {
    const body = data ? JSON.stringify(data) : null;
    const req = https.request(options, (res) => {
      let chunks = '';
      res.on('data', (chunk) => (chunks += chunk));
      res.on('end', () => {
        try { resolve({ status: res.statusCode, data: JSON.parse(chunks) }); }
        catch (e) { resolve({ status: res.statusCode, data: { error: chunks } }); }
      });
    });
    req.on('error', (err) => reject(err));
    // 空闲超时：长时间无响应时主动中断，而不是永远挂起
    req.setTimeout(API_TIMEOUT_MS, () => req.destroy(new Error(`请求超时（${API_TIMEOUT_MS / 1000}s 无响应）`)));
    if (body) req.write(body);
    req.end();
  });
}

// 依据扩展名推断 Content-Type（上传文件时使用）
function inferMimeType(filePath) {
  const mimeMap = {
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.webp': 'image/webp',
    '.gif': 'image/gif',
    '.html': 'text/html',
    '.htm': 'text/html',
    '.pdf': 'application/pdf',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.txt': 'text/plain',
    '.md': 'text/markdown',
    '.csv': 'text/csv',
  };
  return mimeMap[path.extname(filePath).toLowerCase()] || 'application/octet-stream';
}

// 构造 multipart/form-data 请求体（Node 原生实现，无第三方依赖）
function buildMultipartBody(fields, files) {
  // 时间戳 + 随机数，避免同一毫秒内并发上传时 boundary 撞车
  const boundary = `----qingshui${Date.now().toString(16)}${Math.random().toString(16).slice(2, 10)}`;
  const chunks = [];
  for (const [key, value] of Object.entries(fields)) {
    if (value === undefined || value === null || value === '') continue;
    chunks.push(Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="${key}"\r\n\r\n${value}\r\n`));
  }
  for (const file of files) {
    chunks.push(Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="${file.field}"; filename="${path.basename(file.path)}"\r\nContent-Type: ${file.mime}\r\n\r\n`));
    chunks.push(fs.readFileSync(file.path));
    chunks.push(Buffer.from('\r\n'));
  }
  chunks.push(Buffer.from(`--${boundary}--\r\n`));
  return { body: Buffer.concat(chunks), boundary };
}

// 上传文件（multipart/form-data）
function apiUpload(pathname, fields, files) {
  const { apiKey, baseUrl } = getConfig();
  const url = new URL(pathname, baseUrl);
  const { body, boundary } = buildMultipartBody(fields, files);
  const options = {
    hostname: url.hostname,
    port: url.port ? Number(url.port) : 443,
    path: url.pathname + url.search,
    method: 'POST',
    headers: {
      'Content-Type': `multipart/form-data; boundary=${boundary}`,
      'Content-Length': body.length,
      'Authorization': `Bearer ${apiKey}`,
      'X-API-Key': apiKey,
    },
  };
  return new Promise((resolve, reject) => {
    const req = https.request(options, (res) => {
      let chunks = '';
      res.on('data', (chunk) => (chunks += chunk));
      res.on('end', () => {
        try { resolve({ status: res.statusCode, data: JSON.parse(chunks) }); }
        catch (e) { resolve({ status: res.statusCode, data: { error: chunks } }); }
      });
    });
    req.on('error', (err) => reject(err));
    req.setTimeout(UPLOAD_TIMEOUT_MS, () => req.destroy(new Error(`上传超时（${UPLOAD_TIMEOUT_MS / 1000}s 无响应）`)));
    req.write(body);
    req.end();
  });
}

async function shareAsset(filePath, options = {}) {
  if (!filePath) throw new Error('请指定要分享的文件路径');
  const abs = path.resolve(filePath);
  if (!fs.existsSync(abs) || !fs.statSync(abs).isFile()) {
    throw new Error(`文件不存在: ${filePath}`);
  }
  const originalName = path.basename(abs);
  const ext = path.extname(originalName).toLowerCase().replace(/^\./, '');
  if (!ext) throw new Error('文件必须有扩展名');

  const isHTML = ext === 'html' || ext === 'htm';
  const noBundle = options.noBundle === true || options.noBundle === 'true' || options.bundle === false || options.bundle === 'false';
  let uploadPath = abs;
  let tempDir = '';

  try {
    if (isHTML && !noBundle) {
      const fetchRemote = !(options.noFetch === true || options.noFetch === 'true');
      console.log(`🧩 正在打包 CSS/JS/图片（本地内联${fetchRemote ? ' + 远程下载' : '，远程引用不下载'}）: ${originalName}`);
      const html = await bundleHTML(abs, {
        allowScripts: options.noScripts !== true && options.noScripts !== 'true',
        fetchRemote,
        keepSvg: options.keepSvg === true || options.keepSvg === 'true',
      });
      tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'qingshui-share-'));
      uploadPath = path.join(tempDir, 'share.html');
      fs.writeFileSync(uploadPath, html, 'utf8');
      if (Buffer.byteLength(html, 'utf8') > 10 * 1024 * 1024) {
        console.log('⚠️  打包后的 HTML 超过 10MB，服务端可能拒绝上传（HTML 上限 10MB）');
      }
    }

    const fields = {
      name: options.name || originalName,
      extension: ext === 'htm' ? 'html' : ext,
      allow_scripts: (options.noScripts === true || options.noScripts === 'true') ? '0' : '1',
    };
    const files = [{ field: 'file', path: uploadPath, mime: inferMimeType(uploadPath) }];
    console.log(`📤 上传分享: ${originalName}`);
    const result = await apiUpload('/api/v1/assets', fields, files);
    if (result.status !== 201 || !result.data.success) {
      throw new Error(`分享失败: ${result.data.error || 'HTTP ' + result.status}`);
    }
    console.log(`✅ 分享成功: ${result.data.url}`);
    console.log(`   hash: ${result.data.asset.hash}`);
    console.log(`   类型: ${result.data.asset.kind} / ${result.data.asset.mime_type}`);
    if (result.data.asset.kind === 'html') {
      console.log('   提示：HTML 在沙箱 iframe 中打开；页面内脚本无法读取本站 Cookie/存储。');
    }
    (result.data.warnings || []).forEach((w) => console.log(`   ⚠️  ${w}`));
    return result.data;
  } finally {
    if (tempDir) {
      try { fs.rmSync(tempDir, { recursive: true, force: true }); } catch (e) { /* ignore */ }
    }
  }
}

async function listAssets(options = {}) {
  const params = new URLSearchParams();
  if (options.page) params.set('page', String(options.page));
  if (options.pageSize) params.set('page_size', String(options.pageSize));
  const query = params.toString();
  const result = await apiRequest('GET', `/api/v1/assets${query ? '?' + query : ''}`);
  if (result.status !== 200 || !result.data.success) {
    throw new Error(`查询失败: ${result.data.error || 'HTTP ' + result.status}`);
  }
  const { assets = [], usage, total, page, page_size: pageSize } = result.data;
  console.log(`\n📦 已分享资源（${total} 个，第 ${page} 页，每页 ${pageSize} 条）:`);
  if (assets.length === 0) {
    console.log('  （暂无）');
  }
  assets.forEach((a, i) => {
    console.log(`  ${i + 1}. [${a.kind}] ${a.file_name}  ${a.url}`);
    console.log(`     hash: ${a.hash}`);
  });
  if (usage) {
    console.log(`\n💾 配额: ${usage.used_bytes}/${usage.max_total_bytes} 字节；今日 ${usage.uploads_today}/${usage.max_uploads_per_day} 次；本小时 ${usage.uploads_this_hour}/${usage.max_uploads_per_hour} 次`);
  }
  return result.data;
}

async function deleteAsset(hash) {
  if (!hash) throw new Error('请指定要删除的 hash');
  if (!/^[a-f0-9]{32}$/.test(hash)) throw new Error('hash 必须是 32 位小写十六进制');
  const result = await apiRequest('DELETE', `/api/v1/assets/${encodeURIComponent(hash)}`);
  if (result.status !== 200 || !result.data.success) {
    throw new Error(`取消分享失败: ${result.data.error || 'HTTP ' + result.status}`);
  }
  console.log(`✅ 已取消分享: ${hash}`);
  return result.data;
}

function parseOptions(args) {
  const result = {};
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg.startsWith('--')) {
      const key = arg.slice(2).replace(/-([a-z])/g, (_, c) => c.toUpperCase());
      const val = args[i + 1] && !args[i + 1].startsWith('--') ? args[++i] : 'true';
      const parsed = isNaN(val) ? val : Number(val);
      if (result[key] === undefined) {
        result[key] = parsed;
      } else if (Array.isArray(result[key])) {
        result[key].push(parsed);
      } else {
        result[key] = [result[key], parsed];
      }
    }
  }
  // 重复的非列表参数取最后一个值
  for (const key of Object.keys(result)) {
    if (Array.isArray(result[key])) {
      result[key] = result[key][result[key].length - 1];
    }
  }
  return result;
}

async function main() {
  loadDotEnv();
  const args = process.argv.slice(2);
  const command = args[0];

  switch (command) {
    case 'share': {
      const file = args[1];
      if (!file) { console.error('用法: node share.js share <文件> [--name 名称] [--no-bundle] [--no-scripts] [--no-fetch] [--keep-svg]'); process.exit(1); }
      const options = parseOptions(args.slice(2));
      try {
        await shareAsset(file, options);
      } catch (e) { console.error(`\n❌ ${e.message}`); process.exit(1); }
      break;
    }
    case 'assets': {
      const options = parseOptions(args.slice(1));
      try {
        await listAssets(options);
      } catch (e) { console.error(`\n❌ ${e.message}`); process.exit(1); }
      break;
    }
    case 'unshare': {
      const hash = args[1];
      if (!hash) { console.error('用法: node share.js unshare <hash>'); process.exit(1); }
      try {
        await deleteAsset(hash);
      } catch (e) { console.error(`\n❌ ${e.message}`); process.exit(1); }
      break;
    }
    default:
      console.log(`青水静态资源分享脚本

用法:
  node share.js share <文件> [--name 名称] [--no-bundle] [--no-scripts] [--no-fetch] [--keep-svg]
                                                       上传分享 HTML/图片/文档
  node share.js assets [--page 1] [--page-size 20]     查看已分享资源
  node share.js unshare <hash>                         取消分享

分享示例:
  node share.js share ./report.html                    自动内联本地 CSS/JS/图片，远程图片/脚本/样式自动下载后内联
  node share.js share ./poster.png --name 活动海报
  node share.js share ./page.html --no-bundle --no-scripts
  node share.js share ./page.html --no-fetch           不下载远程资源（遇到远程引用时报错）
  node share.js assets
  node share.js unshare 0123456789abcdef0123456789abcdef

环境变量: QINGSHUI_API_KEY (必需), QINGSHUI_BASE_URL (可选，默认 https://qingshui.hqwx.com，
白名单 qingshui.hqwx.com / qingshui.hqqt.com)；也支持 skill 根目录或当前目录的 .env`);
  }
}

main();
