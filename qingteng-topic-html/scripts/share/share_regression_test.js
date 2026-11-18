#!/usr/bin/env node
'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const {
  bundleHTML,
  countZoomButtons,
  inspectRasterDataURIs,
} = require('./bundle-html');
const { inspectBundledHTML, preflightAsset } = require('./share');

function pngHeader(width, height) {
  const data = Buffer.alloc(24);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(data, 0);
  data.writeUInt32BE(13, 8);
  data.write('IHDR', 12, 'ascii');
  data.writeUInt32BE(width, 16);
  data.writeUInt32BE(height, 20);
  return `data:image/png;base64,${data.toString('base64')}`;
}

async function main() {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'qt-share-test-'));
  try {
    const tiny = pngHeader(320, 180);
    const source = `<!doctype html><html><body>
      <button class="qt-t-zoom" type="button" data-qt-zoom><img src="${tiny}" alt="示例"></button>
      <button class="cta" type="button">立即报名</button>
      <script>const sample = '<button data-qt-zoom><img src="fake"></button>';</script>
    </body></html>`;
    const sourcePath = path.join(tempDir, 'zoom.html');
    fs.writeFileSync(sourcePath, source, 'utf8');

    const bundled = await bundleHTML(sourcePath, { fetchRemote: false });
    assert.strictEqual(countZoomButtons(bundled), 0, '可缩放图片按钮应在分享副本中解包');
    assert.match(bundled, /<img\s+src="data:image\/png;base64,[^"]+"\s+alt="示例">/);
    assert.match(bundled, /<button class="cta" type="button">立即报名<\/button>/, '普通按钮必须保留');
    assert.match(bundled, /const sample = '<button data-qt-zoom>/, '脚本字符串不得被改写');

    const raster = inspectRasterDataURIs(bundled);
    assert.strictEqual(raster.count, 1);
    assert.strictEqual(raster.withDimensions, 1);
    assert.strictEqual(raster.totalPixels, 320 * 180);
    assert.strictEqual(raster.maxWidth, 320);
    assert.strictEqual(raster.maxHeight, 180);

    const safeReport = inspectBundledHTML(bundled);
    assert.strictEqual(safeReport.status, 'pass');
    assert.strictEqual(safeReport.zoomButtons, 0);
    assert.strictEqual(safeReport.imageTags, 1, '脚本字符串中的伪图片不应计入预检');

    const riskyPath = path.join(tempDir, 'risky.html');
    fs.writeFileSync(riskyPath, `<img src="${pngHeader(3000, 3000)}" alt="大图">`, 'utf8');
    const riskyReport = await preflightAsset(riskyPath, { noFetch: true });
    assert.strictEqual(riskyReport.status, 'warn');
    assert.ok(riskyReport.warnings.some((message) => message.includes('转码为 PNG')));

    const nested = `<button data-qt-zoom><span><img src="${tiny}"></span></button>`;
    assert.strictEqual(countZoomButtons(nested), 1, '无法安全解包的嵌套按钮必须被预检发现');
    assert.strictEqual(inspectBundledHTML(nested).status, 'fail');

    console.log('✅ share regression tests passed');
  } finally {
    const tempRoot = path.resolve(os.tmpdir());
    const resolved = path.resolve(tempDir);
    if (resolved.startsWith(tempRoot + path.sep) && path.basename(resolved).startsWith('qt-share-test-')) {
      fs.rmSync(resolved, { recursive: true, force: true });
    }
  }
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
