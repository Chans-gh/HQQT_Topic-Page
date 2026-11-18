#!/usr/bin/env node
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const pageModes = JSON.parse(fs.readFileSync(path.join(root, 'assets', 'page-modes.json'), 'utf8'));
const components = JSON.parse(fs.readFileSync(path.join(root, 'assets', 'components', 'catalog.json'), 'utf8'));
const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));

assert.strictEqual(pageModes.schema, 'qt-page-modes/1');
assert.strictEqual(pageModes.version, pkg.version, 'page-mode catalog must match package version');
assert.ok(Array.isArray(pageModes.modes));
assert.deepStrictEqual(pageModes.modes.map((item) => item.id), [
  'report', 'course', 'catalog', 'operations', 'campaign', 'custom',
]);

const ids = new Set(components.components.map((item) => item.type));
for (const mode of pageModes.modes) {
  assert.ok(mode.label && mode.criteria, `${mode.id}: label/criteria required`);
  assert.ok(Array.isArray(mode.densities) && mode.densities.length, `${mode.id}: densities required`);
  assert.ok(Array.isArray(mode.component_priority), `${mode.id}: component priority required`);
  for (const component of mode.component_priority) {
    assert.ok(ids.has(component), `${mode.id}: unknown component ${component}`);
  }
  assert.ok(Array.isArray(mode.preview_focus) && mode.preview_focus.length === 2, `${mode.id}: two preview focus areas required`);
}

assert.strictEqual(pageModes.preview_policy.max_directions, 2);
assert.strictEqual(pageModes.preview_policy.requires_list_approval, true);
assert.ok(pageModes.preview_policy.forbidden.includes('自动分享预览'));
console.log('✅ page mode catalog tests passed');
