#!/usr/bin/env node
'use strict';
const fs=require('fs');
const path=require('path');
const root=path.resolve(__dirname,'..');
const patterns=fs.readFileSync(path.join(root,'assets/components/patterns.html'),'utf8');
const css=fs.readFileSync(path.join(root,'assets/components/topic.css'),'utf8');
const js=fs.readFileSync(path.join(root,'assets/components/topic.js'),'utf8');
const fail=message=>{throw new Error(message)};

for(const id of ['page-navigation','stage-navigation']){
 if(!patterns.includes(`<template id="${id}">`))fail(`missing ${id} pattern`);
}
if(!/data-qt-page-nav[^>]*aria-label=/.test(patterns))fail('navigation needs a named landmark');
if(!/href="#M\d+"/.test(patterns))fail('navigation examples need real fragment links');
if(/data-(?:day|stage)-(?:toggle|panel)/.test(patterns))fail('navigation must not hide Day/stage content');
for(const token of ['.qt-t-page-nav','aria-current="location"','overflow-x:auto','position:static']){
 if(!css.includes(token))fail(`missing navigation CSS contract: ${token}`);
}
for(const token of ['[data-qt-page-nav]','IntersectionObserver','aria-current','hashchange']){
 if(!js.includes(token))fail(`missing navigation runtime contract: ${token}`);
}
if(/\.hidden\s*=|setAttribute\(['"]hidden/.test(js.slice(js.indexOf('// Page/Day navigation'),js.indexOf('let dialog='))))fail('navigation runtime must not hide sections');
console.log('✅ long-page navigation contract tests passed');
