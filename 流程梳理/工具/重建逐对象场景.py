"""渲染经人工复核的逐对象场景；来源变化时停止，不自动裁定新业务规则。"""
from pathlib import Path
import hashlib
import json
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '流程梳理'
data_file = OUT / '13-操作影响逐对象数据.json'
d = json.loads(data_file.read_text())
evidence = {e['id']: e for e in d['evidences']}
assert len(evidence) == len(d['evidences']), '重复证据ID'
for source in d['sources']:
    assert hashlib.sha256(Path(source['path']).read_bytes()).hexdigest() == source['sha256'], '请先语义复核变化来源：' + source['path']
for e in d['evidences']:
    lines = Path(e['file']).read_text().splitlines()
    literal = lines[e['line'] - 1]
    q = e['quote']
    assert q in literal or json.dumps(q, ensure_ascii=False)[1:-1] in literal or q.replace("'", "\\'") in literal, e['id'] + '原文引用失效'
    if e['url']:
        target = unquote(e['url'].split('#page=')[1]).split('?')[0]
        assert (ROOT / 'liveshow-proto/prototype' / target).is_file(), e['id'] + '页面缺失'
operation_ids = {o['id'] for o in d['operations']}
assert operation_ids == {oid for g in d['groups'].values() for oid in g['operations']}
all_ids = []
for scene in d['operations'] + d['concurrent']:
    all_ids.append(scene['id'])
    if 'operations' in scene:
        assert set(scene['operations']) <= operation_ids
    assert set(scene['effects']) <= {r['object'] for r in scene['rows']}
    for row in scene['rows']:
        all_ids.append(row['id'])
        assert bool(row['result']) == bool(row['evidence']), row['id']
        assert set(row['evidence']) <= evidence.keys()
        effect = scene['effects'].get(row['object'], {'result': '', 'evidence': []})
        assert row['result'] == effect['result'] and row['evidence'] == effect['evidence'], row['id']
    for b in scene.get('branches', []):
        all_ids.append(b['id'])
        assert b['condition'] and b['result'] and set(b['evidence']) <= evidence.keys()
    assert set(scene.get('ruleRefs', [])) <= evidence.keys()
assert len(set(all_ids)) == len(all_ids), '场景或行ID重复'
for item in d['conflicts'] + d.get('pending', []):
    assert set(item['evidence']) <= evidence.keys()
social_path = ROOT / 'liveshow-proto/context/社交关系规则补充.md'
rule_lines = {n for n, line in enumerate(social_path.read_text().splitlines(), 1)
              if (line.startswith('|') and not line.startswith(('|---', '||'))) or line.startswith(('- 若', '观众包括'))}
assert rule_lines == {r['line'] for r in d['ruleCoverage']}, '社交规则覆盖不全'
for r in d['ruleCoverage']:
    assert r['evidence'] in evidence and set(r['operations']) <= operation_ids
old = json.loads((Path(d['archive']) / data_file.name).read_text())
current_scenes = {s['id']: s for s in d['operations'] + d['concurrent']}
for previous in old['operations'] + old['concurrent']:
    assert previous['id'] in current_scenes
    now = {r['id']: r['object'] for r in current_scenes[previous['id']]['rows']}
    assert all(now.get(r['id']) == r['object'] for r in previous['rows']), '旧行编号丢失或重用'

def link(file, line=None, title=None):
    return f'[{title or Path(file).name}](<{file}{":" + str(line) if line else ""}>)'

def cell(text):
    return str(text).replace('|', '\\|').replace('\n', '<br>')

def refs(ids):
    return '；'.join(link(OUT / '15-操作影响依据原文.md', evidence_lines[i], i) for i in ids)

header = f'> 重建日期：{d["date"]}。当前文档／批注依据，不代表需求已批准；本库操作未运行后端测试或浏览器验证。\n\n'
ev_md = '# 八类操作影响：出处原文\n\n' + header
evidence_lines = {}
for e in d['evidences']:
    evidence_lines[e['id']] = len(ev_md.splitlines()) + 1
    ev_md += f'## {e["id"]}\n\n导航：{e["nav"]}。'
    if e['view']:
        ev_md += f'同页视图：{e["key"]}，需手动选择。'
    ev_md += '\n\n' + link(e['file'], e['line'])
    if e['url']:
        ev_md += f' · [带批注页面]({e["url"]})'
    ev_md += f'\n\n类型：{e["section"]}\n\n> {e["quote"]}\n\n'
ev_md += '## 来源冲突与修正\n\n'
for c in d['conflicts']:
    ev_md += f'### {c["id"]} {c["status"]}\n\n适用：{c["scope"]}。{c["explanation"]}\n\n原文：{c["quote"]}\n\n依据：{refs(c["evidence"])}\n\n'
ev_md += '## 具体待确认分支\n\n'
for item in d.get('pending', []):
    ev_md += f'### {item["id"]}\n\n{item["scope"]}：{item["question"]}\n\n依据：{refs(item["evidence"])}\n\n'

def scene_md(scene, level):
    text = f'{"#" * level} {scene["id"]} {scene["name"]}\n\n条件：{scene["condition"]}\n\n'
    if scene.get('ruleRefs'):
        text += '社交补充适用条目：' + refs(scene['ruleRefs']) + '。'
        if 'operations' in scene:
            text += '仅作为各操作前置／单项规则，不能据此确定并发先后、成功与终态。'
        text += '\n\n'
    text += '| 行ID | 待核对对象 | 当前来源支持的影响 | 出处 |\n|---|---|---|---|\n'
    for row in scene['rows']:
        text += '| ' + ' | '.join(map(cell, [row['id'], row['object'], row['result']])) + ' | ' + refs(row['evidence']) + ' |\n'
    if scene.get('branches'):
        text += '\n条件分支（不作为新增独立操作）：\n\n| ID | 条件 | 结果／边界 | 出处 |\n|---|---|---|---|\n'
        for b in scene['branches']:
            text += '| ' + ' | '.join(map(cell, [b['id'], b['condition'], b['result']])) + ' | ' + refs(b['evidence']) + ' |\n'
    return text + '\n'

single_md = '# 八类单项操作：逐对象影响\n\n' + header + d['definitions'] + '\n\n原有八类范围及编号保留；条件分支不新增独立操作。冲突和未明确条件见依据原文。\n\n'
for gid, group in d['groups'].items():
    single_md += f'## {gid} {group["title"]}\n\n'
    for scene in d['operations']:
        if scene['group'] == gid:
            single_md += scene_md(scene, 3)
concurrent_md = '# 八类操作同时发生：逐对象影响\n\n' + header + d['definitions'] + '\n\n仅重建当前全部并发候选；不表示所有候选均可同时受理，也不表示穷尽任意数量操作组合。新社交补充没有定义并发顺序，未知对象仍留空。\n\n'
for scene in d['concurrent']:
    concurrent_md += scene_md(scene, 2)
all_single = [r for o in d['operations'] for r in o['rows']]
all_concurrent = [r for o in d['concurrent'] for r in o['rows']]
d['stats'] = dict(groups=len(d['groups']), singleOperations=len(d['operations']), singleRows=len(all_single), singleKnown=sum(bool(r['result']) for r in all_single), concurrentScenarios=len(d['concurrent']), concurrentRows=len(all_concurrent), concurrentKnown=sum(bool(r['result']) for r in all_concurrent), evidence=len(evidence), conditionBranches=sum(len(o.get('branches', [])) for o in d['operations']), socialRuleEntries=len(d['ruleCoverage']))
report = '# 社交规则纳入与全部场景重建说明\n\n' + header
report += d['rebuildBoundary'] + '\n\n社交补充此前已在来源快照中，但旧逐对象清单没有把其正文登记为证据。全部有效规则条目现均直接关联至场景及条件边界，本轮复核引用及门票贡献变化。原型和业务文档未修改。\n\n'
report += '## 重建统计\n\n| 项目 | 旧版 | 本轮 |\n|---|---|---|\n'
for key, value in d['stats'].items():
    report += f'| {key} | {d["previousStats"].get(key, "—")} | {value} |\n'
report += '\n## 社交补充逐条覆盖\n\n| 原文 | 关联操作 | 处理方式 |\n|---|---|---|\n'
for rule in d['ruleCoverage']:
    report += f'| {refs([rule["evidence"]])} | {", ".join(rule["operations"])} | {rule["note"]} |\n'
report += '\n## 实质变化与验证边界\n\n- 删除好友：补充搜索、公开主页、再关注、好友申请、观看直播、加入粉丝团、连麦邀请和举报资格；其他独立限制仍适用。\n- 拉黑：补充观众主动拉黑主播的即时退房、双向主播条件、主动黑名单记录、再入团及连麦邀请限制。\n- 直播间处置：明确主播可处理房管，房管不能禁言／踢出其他房管，观众包含运营账号。\n- K01因系统概要同步而关闭，保留旧证据在历史快照；K02保留房管授权条件及解除规则的来源差异。\n- 账号禁用自动撤房管是新增批注；禁用与封禁是否同义、解封恢复规则未明确，保留P-SOC-01，不自动填成封禁结果。\n- 并发结果没有因单项规则补充而扩充；原有未知结果继续留空。\n- 所有旧场景／行ID保留，原文与当前行号、证据引用、页面文件映射、来源哈希和规则覆盖均校验；链接仅静态校验，未运行浏览器或后端。\n- 历史全量审查及11号摘要已纳入本轮复核；全量状态以17号更新报告及20号问题复核为准。\n'
report += '\n旧来源清单中的《海外直播APP需求术语解释.md》当前已不存在，本轮未将其作为现行来源；没有场景结果引用该文件。\n'
report += '\n历史归档：' + link(Path(d['archive']) / '13-操作影响阅读入口.md') + '\n'
entry = '# 八类操作影响阅读入口\n\n' + header + d['rebuildBoundary'] + '\n\n' + d['definitions'] + '\n\n'
for filename in ['13-单项操作逐对象影响.md', '14-并发操作逐对象影响.md', '15-操作影响依据原文.md', '16-社交规则纳入与场景重建说明.md']:
    entry += '- ' + link(OUT / filename) + '\n'
entry += '\n## 操作目录\n\n| 范围 | 操作 |\n|---|---|\n'
for gid, group in d['groups'].items():
    entry += '| ' + gid + ' ' + group['title'] + ' | ' + '<br>'.join(o['id'] + ' ' + o['name'] for o in d['operations'] if o['group'] == gid) + ' |\n'
entry += f'\n共{len(d["operations"])}个单项操作、{len(d["concurrent"])}个并发候选、{d["stats"]["conditionBranches"]}个条件分支。社交补充{len(d["ruleCoverage"])}条有效正文已逐条纳入。K01已关闭，K02及其他未知分支保留。\n\n独立操作仍只限上述八类；注销、登录、连麦、举报、通知开关、粉丝团创建、群禁言、公会启停、运营账号和后台角色管理不新增为独立操作，但有关影响和限制保留。\n'
outputs = {'13-单项操作逐对象影响.md': single_md, '14-并发操作逐对象影响.md': concurrent_md, '15-操作影响依据原文.md': ev_md, '16-社交规则纳入与场景重建说明.md': report, '13-操作影响阅读入口.md': entry}
# Validate rendered evidence links against the actual heading, not only IDs in JSON.
ev_lines = ev_md.splitlines()
assert all(ev_lines[n - 1] == '## ' + eid for eid, n in evidence_lines.items())
for name, content in outputs.items():
    (OUT / name).write_text(content)
data_file.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
validation = dict(date=d['date'], scope=d['scope'], stats=d['stats'], allActionsWithinScope=True, allConcurrentActionsWithinScope=True, blankResultsHaveBlankEvidence=True, oldScenarioAndRowIdsPreserved=True, sourceHashesMatch=True, evidenceQuotesAndLinesChecked=len(evidence), socialRuleCoverageChecked=len(d['ruleCoverage']), backendConcurrencyVerified=False, browserVerified=False, archive=d['archive'])
(OUT / '13-逐对象清单验证.json').write_text(json.dumps(validation, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(validation, ensure_ascii=False, indent=2))
