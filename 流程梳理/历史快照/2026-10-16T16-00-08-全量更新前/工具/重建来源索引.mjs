import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';

// 只重建定位资料；业务结论在操作表中单独维护，不由关键词自动裁定。
const root = path.resolve(import.meta.dirname, '../..');
const proto = path.join(root, 'liveshow-proto/prototype');
const out = path.join(root, '流程梳理');
const stamp = new Date().toISOString().replace(/[:.]/g, '-');
const date = new Date().toLocaleDateString('sv-SE', { timeZone: 'Asia/Shanghai' });
const walk = dir => fs.readdirSync(dir, { withFileTypes: true }).flatMap(e => e.isDirectory() ? walk(path.join(dir, e.name)) : [path.join(dir, e.name)]).sort();
const read = f => fs.readFileSync(f, 'utf8');
const hash = f => crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
const fileLink = (f, line) => `[${path.basename(f)}](<${f}${line ? ':' + line : ''}>)`;
const htmlPages = walk(path.join(proto, 'pages')).filter(f => f.endsWith('.html'));
const viewer = read(path.join(proto, 'index.html'));
const array = name => {
  const literal = viewer.match(new RegExp(`const ${name} = (\\[[\\s\\S]*?\\n    \\]);`));
  assert(literal, `查看器数组未找到：${name}`);
  return vm.runInNewContext('(' + literal[1] + ')');
};
const registrations = Object.fromEntries(['user', 'guild', 'admin'].map(e => [e, array(e + 'Pages')]));
const groups = array('adminPageGroups');
const entries = [];
const titles = new Map(htmlPages.map(f => [f, (read(f).match(/<title>([\s\S]*?)<\/title>/i)?.[1] || path.basename(f)).trim()]));
for (const end of ['user', 'guild', 'admin']) {
  const source = path.join(proto, 'annotations', end + '.js');
  const raw = read(source);
  const sandbox = { window: {} };
  vm.runInNewContext(raw, sandbox, { timeout: 1000 });
  assert(sandbox.window.PROTO_ANNOTATIONS, `缺少批注对象：${source}`);
  for (const [key, value] of Object.entries(sandbox.window.PROTO_ANNOTATIONS)) {
    const parent = key.startsWith('views/') ? key.split('/')[1] + '.html' : key;
    const pages = htmlPages.filter(f => path.relative(path.join(proto, 'pages'), f).startsWith(end + '/') && path.basename(f) === parent);
    const line = raw.split('\n').findIndex(l => l.includes(`'${key}':`) || l.includes(`"${key}":`) || l.includes(`['${key}'] =`) || l.includes(`["${key}"] =`)) + 1;
    assert(line > 0 && Array.isArray(value.sections), `无法定位条目：${end}/${key}`);
    assert(pages.length <= 1, `页面名称有歧义：${end}/${parent}`);
    const registered = registrations[end].find(p => p.file === parent);
    const group = end === 'admin' ? groups.find(g => g.allFiles.includes(parent))?.title : undefined;
    const nav = [({user:'用户／主播端',guild:'公会端',admin:'管理后台'})[end], group, registered?.title || titles.get(pages[0]) || parent].filter(Boolean).join(' → ');
    const url = pages.length ? 'http://127.0.0.1:8765/index.html?read=' + parent.slice(0,-5) + '#page=' + encodeURIComponent(path.relative(proto, pages[0]).split(path.sep).join('/')) : '';
    entries.push({ end, key, line, source, pages, sections: value.sections, nav, url, registered: Boolean(registered), view: key.startsWith('views/') ? key.split('/').at(-1).replace(/\.html$/, '') : '' });
  }
}
const snapshotFile = path.join(out, '来源快照.json');
const old = fs.existsSync(snapshotFile) ? JSON.parse(read(snapshotFile)) : { sources: [], entries: [], pages: [] };
const sourcePaths = [...walk(path.join(proto, 'annotations')), ...walk(path.join(root, 'liveshow-proto/context')), ...htmlPages, ...walk(path.join(proto, 'assets')), path.join(proto, 'index.html'), path.join(root, 'AGENTS.md'), path.join(root, 'liveshow-proto/AGENTS.md'), path.join(root, 'liveshow-proto/项目说明.md')].filter(f => fs.existsSync(f));
const sources = [...new Set(sourcePaths)].map(f => ({ path:f, sha256:hash(f) }));
const byKey = new Map(old.entries.map(e => [e.end + '/' + e.key, e]));
const nowKeys = new Set(entries.map(e => e.end + '/' + e.key));
const added = entries.filter(e => !byKey.has(e.end + '/' + e.key)).map(e => e.end + '/' + e.key);
const changed = entries.filter(e => byKey.has(e.end + '/' + e.key) && JSON.stringify(e.sections) !== JSON.stringify(byKey.get(e.end + '/' + e.key).sections)).map(e => e.end + '/' + e.key);
const removed = old.entries.filter(e => !nowKeys.has(e.end + '/' + e.key)).map(e => e.end + '/' + e.key);
const missingMappings = entries.filter(e => !e.pages.length).map(e => e.end + '/' + e.key);
const delta = { date, comparedWith:old.date, oldEntries:old.entries.length, entries:entries.length, oldPages:old.pages.length, pages:htmlPages.length, added, changed, removed, missingMappings, newPages:htmlPages.filter(p => !old.pages.includes(p)), removedPages:old.pages.filter(p => !htmlPages.includes(p)), changedTrackedSources:sources.filter(s => old.sources.some(o => o.path === s.path && o.sha256 !== s.sha256)).map(s => s.path), addedTrackedSources:sources.filter(s => !old.sources.some(o => o.path === s.path)).map(s => s.path) };
const archive = path.join(out, '历史快照', stamp);
fs.mkdirSync(archive, {recursive:true});
for (const name of ['00-阅读入口.md','03-来源细节索引.md','04-独立页面清单.md','来源快照.json','11-操作与组合影响表.md','11-操作与组合影响表.json']) if (fs.existsSync(path.join(out,name))) fs.copyFileSync(path.join(out,name), path.join(archive,name));
const header = `> 重建日期：${date}。当前原文索引；未证明需求已经批准，未验证后端行为。\n`;
let detail = '# 页面与批注来源细节索引\n' + header + `\n共 ${entries.length} 个批注入口；views 是同页视图。链接指向所属页面，视图需在查看器手动选择。导航名称来自当前查看器，未注册入口明确标出。\n`;
for (const e of entries) {
  detail += `\n## ${e.end}/${e.key}\n\n导航：${e.nav}${e.registered ? '' : '（独立页面未注册）'}。${e.view ? `视图键：${e.key}。` : ''}\n\n来源：${fileLink(e.source,e.line)}；${e.url ? `[带批注页面](${e.url})` : '缺少所属页面映射'}。\n`;
  for (const s of e.sections) detail += `\n**${s.t}**\n\n${s.d.join('\n')}\n`;
}
const cell = x => String(x || '').replace(/\|/g,'\\|').replace(/\n/g,'<br>');
let inventory = '# 独立页面清单\n' + header + `\n物理 HTML ${htmlPages.length} 个；查看器注册 ${Object.values(registrations).reduce((a,b)=>a+b.length,0)} 个；批注入口 ${entries.length} 个，其中同页视图 ${entries.filter(e=>e.view).length} 个。这些数量不证明语义审查通过。\n\n| 端 | 导航目录／标题 | 源页面 | 带批注页面 | 批注入口 | 注册 |\n|---|---|---|---|---|---|\n`;
for (const p of htmlPages) {
  const related = entries.filter(e=>e.pages.includes(p));
  const main = related.find(e=>!e.view) || related[0];
  inventory += '| ' + [path.relative(path.join(proto,'pages'),p).split('/')[0], cell(main?.nav || titles.get(p)), fileLink(p), main?.url ? `[查看](${main.url})` : '', related.map(e=>`${e.key}：${fileLink(e.source,e.line)}`).join('<br>'), main?.registered ? '是' : '否'].join(' | ') + ' |\n';
}
fs.writeFileSync(path.join(out,'03-来源细节索引.md'), detail);
fs.writeFileSync(path.join(out,'04-独立页面清单.md'), inventory);
fs.writeFileSync(snapshotFile, JSON.stringify({date,scope:path.join(root,'liveshow-proto'),limitations:'原文提取和静态映射；操作表为局部语义复核，其余历史语义报告未随本次重建自动复核。',sources,pages:htmlPages,entries},null,2)+'\n');
fs.writeFileSync(path.join(out,'重建差异.json'),JSON.stringify(delta,null,2)+'\n');
console.log(JSON.stringify({date,archive,pages:htmlPages.length,entries:entries.length,views:entries.filter(e=>e.view).length,added,changed:changed.length,removed,missingMappings},null,2));
