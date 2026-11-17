#!/usr/bin/env node
'use strict';
const fs=require('fs');
const path=require('path');
const root=path.resolve(__dirname,'..');
const pkg=JSON.parse(fs.readFileSync(path.join(root,'package.json'),'utf8'));
const data=JSON.parse(fs.readFileSync(path.join(root,'assets/input-sources.json'),'utf8'));
const validator=fs.readFileSync(path.join(root,'scripts/input_sources.py'),'utf8');
const record=fs.readFileSync(path.join(root,'scripts/record.py'),'utf8');
const fail=message=>{throw new Error(message)};
if(data.schema!=='qt-input-adapters/1'||data.version!==pkg.version)fail('input adapter schema/version mismatch');
const expected=['text','feishu','docx','pdf','spreadsheet','web','image','video','mixed'];
const kinds=data.adapters.map(item=>item.kind);
if(new Set(kinds).size!==kinds.length||expected.some(kind=>!kinds.includes(kind)))fail('input adapter kinds incomplete/duplicate');
for(const item of data.adapters){
 if(!item.label||!Array.isArray(item.methods)||!item.methods.length||!Array.isArray(item.inspect)||!item.inspect.length||!Array.isArray(item.loss_risks))fail(`incomplete adapter: ${item.kind}`);
 if(item.methods.some(method=>!data.methods.includes(method)||method==='pending'))fail(`invalid declared method: ${item.kind}`);
}
for(const value of ['not-run','complete','partial','blocked'])if(!data.statuses.includes(value))fail(`missing status ${value}`);
if(!data.notice.includes('does not parse'))fail('catalog must state deterministic boundary');
for(const token of ['input_contract','qt-input-source/1','not-run','partial','blocked','local input missing or SHA mismatch'])if(!validator.includes(token))fail(`validator contract missing ${token}`);
for(const token of ['validate_inputs(record, require_read=True','inputs/','snapshot source input is not self-contained'])if(!record.includes(token))fail(`record integration missing ${token}`);
console.log('✅ multi-format input adapter catalog tests passed');
