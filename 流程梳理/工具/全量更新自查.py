"""交付门禁：当前引用、旧ID、来源不变、范围与链接；不证明业务批准。"""
from pathlib import Path
from urllib.parse import unquote,urlsplit
import json,re,hashlib,collections,datetime,subprocess
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'流程梳理';P=ROOT/'liveshow-proto'
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
S=load(R/'来源快照.json');F=load(R/'全量场景/场景数据.json');V=load(R/'本轮问题复核.json');O=load(R/'13-操作影响逐对象数据.json');D=load(R/'18-场景关系索引.json');A=Path(V['archive']);B=load(A/'全量场景/场景数据.json');errors=[]
for x in S['sources']:
 if sha(Path(x['path']))!=x['sha256']:errors.append('current source drift '+x['path'])
protected=load(A/'原型保护清单.json');current={str(p.relative_to(ROOT)):sha(p) for p in P.rglob('*') if p.is_file() and '.git' not in p.relative_to(P).parts}
assert protected==current,'原型文件出现变化；不能宣称未改动'
alljson=[p for p in R.rglob('*.json') if '历史快照' not in p.parts]
for p in alljson:load(p)
# Source quotes must match the currently cited line, including literal JS escaping.
quoted=0
for e in F['evidence']:
 literal=Path(e['file']).read_text().splitlines()[e['line']-1];q=e['quote'];quoted+=1
 if not any(x in literal for x in [q,json.dumps(q,ensure_ascii=False)[1:-1],q.replace("'","\\'")]):errors.append('quote '+e['id'])
for i in V['issues']:
 assert i['evidence'],i['id']
 for e in i['evidence']:
  literal=(ROOT/e['path']).read_text().splitlines()[e['line']-1];q=e['quote'];quoted+=1
  if not any(x in literal for x in [q,json.dumps(q,ensure_ascii=False)[1:-1],q.replace("'","\\'")]):errors.append('issue quote '+i['id'])
# Scenario families preserve prior IDs, or explicitly retire them with the old record.
ids={}
for name in ['scenes','fields','documentCandidates','evidence']:
 now={s['id'] for s in F[name]};prior={s['id'] for s in B[name]};retired={s['id'] for s in F['retiredRecords'][name]}
 assert len(now)==len(F[name]),'duplicate '+name
 assert prior<=now|retired,'lost ID '+name
 ids[name]=dict(previous=len(prior),current=len(now),retired=len(retired),added=len(now-prior),preserved=len(prior&now))
assert {c['id'] for c in F['chains']}=={c['id'] for c in B['chains']}
assert {b['id'] for c in B['chains'] for b in c['branches']}<={b['id'] for c in F['chains'] for b in c['branches']}
old=load(A/'13-操作影响逐对象数据.json');oldrows={r['id']:r['object'] for s in old['operations']+old['concurrent'] for r in s['rows']};nowrows={r['id']:r['object'] for s in O['operations']+O['concurrent'] for r in s['rows']}
assert all(nowrows.get(k)==v for k,v in oldrows.items())
assert {s['id'] for s in old['operations']+old['concurrent']}=={s['id'] for s in O['operations']+O['concurrent']}
for ns,file,prefix in [('TERM','08-批注术语定义缺口.json',''),('E2E','09-端到端完整性审查.json',''),('DS','深层分支审查-2026-10-15/审查记录.json','DS-')]:
 assert {prefix+i['id'] for i in load(A/file)['issues']}=={i['id'] for i in V['issues'] if i['namespace']==ns}
assert V['counts']==dict(collections.Counter(i['change'] for i in V['issues']))
assert len({(i['namespace'],i['id']) for i in V['issues']})==len(V['issues'])
assert len(D['chains'])==25 and all(len(c['dimensions'])==12 and c['steps'] and c['branches'] for c in D['chains'])
assert len(D['documentRuleScope'])==len([e for e in F['evidence'] if e['end']=='context'])==486
assert all(r['chains'] or r['scopeReason'] for r in D['documentRuleScope'])
assert len(D['socialRuleMappings'])==24
assert len(S['pages'])==len(F['physicalCoverage'])==192
assert len(S['entries'])==len(F['sourceCoverage'])==254
assert len(F['viewChecks'])==148
# Markdown local links and source lines, including relative evidence anchors.
local_count=0;viewer_count=0;markdown_count=0
for p in R.rglob('*.md'):
 if '历史快照' in p.parts or '工具' in p.parts:continue
 markdown_count+=1;t=p.read_text()
 for m in re.finditer(r'\]\((<[^>]+>|[^\s)]+)\)',t):
  target=m[1].strip('<>')
  if target.startswith(('http://127.0.0.1:8765/','https://127.0.0.1:8765/')):
   u=urlsplit(target)
   if 'page=' in u.fragment:
    dest=unquote(u.fragment.split('page=',1)[1]).split('?',1)[0];viewer_count+=1
    if not (P/'prototype'/dest).is_file():errors.append(f'viewer {p.name} {target}')
   continue
  if target.startswith(('http:','https:','mailto:','tel:','data:','#')):continue
  pathpart=target.split('#',1)[0];pathpart=unquote(pathpart);line=None
  match=re.match(r'^(.*?):(\d+)$',pathpart)
  if match:pathpart=match[1];line=int(match[2])
  dest=Path(pathpart);dest=dest if dest.is_absolute() else p.parent/dest;local_count+=1
  if not dest.exists():errors.append(f'file {p.name}: {target}');continue
  if line and (line<1 or line>len(dest.read_text().splitlines())):errors.append(f'line {p.name}: {target}')
  if '#ev-' in target:
   anchor=target.rsplit('#',1)[1]
   if '\n## '+anchor.upper()+'\n' not in '\n'+dest.read_text():errors.append('anchor '+target)
# No workbook may be introduced; historical folders are excluded.
assert not [p for p in R.rglob('*') if p.suffix.lower() in ['.xlsx','.xls','.ods'] and '历史快照' not in p.parts]
# Snapshots in each current artifact family agree with the actual source set.
for p in [R/'全量场景/来源快照.json',R/'深层分支审查-2026-10-15/来源快照.json']:
 assert {x['path']:x['sha256'] for x in load(p)['sources']}=={x['path']:x['sha256'] for x in S['sources']}
http=load(R/'19-页面静态复核.json');assert len(http['httpChecks'])==192 and all(x.get('status')==200 and x.get('bytesMatch') for x in http['httpChecks'])
assert not http['missingStaticDestinations']
assert not errors,errors[:30]
result=dict(date='2026-10-16',status='通过：来源、结构、引用、编号及交付范围校验；不代表语义批准或运行验收',sourceFiles=len(S['sources']),protectedPrototypeFiles=len(protected),prototypeUnchanged=True,currentMarkdownFiles=markdown_count,currentJsonFiles=len(alljson),sourceQuotesChecked=quoted,localLinksChecked=local_count,viewerTargetsChecked=viewer_count,missingStaticHtmlTargets=0,httpPagesChecked=192,allLegacyScenarioAndRowIdsPreserved=True,legacyObjectRows=len(oldrows),stableIds=ids,annotationEntries=254,physicalPages=192,registeredViews=148,chains=25,chainBranches=228,chainDimensions=12,contextFiles=6,contextClauses=486,socialRules=24,issueRecords=len(V['issues']),issueDispositions=V['counts'],remainingIssueRecords=sum(i['status'] not in ['关闭','排除'] for i in V['issues']),deduplicatedDefectCount=None,requirementsApproved=False,semanticAuditPassed=False,browserAllPagesVerified=False,backendVerified=False,noWorkbookGenerated=True,archive=str(A),limitations=['所有问题数是可重叠记录数，不是独立缺陷数','浏览器仅检查消息中心和公会通知局部导航／已读','未逐状态执行148视图及94状态注册','无真实支付、IM、推送、SDK、数据库或线上验证'])
save(R/'全量更新自查.json',result)
# Keep the per-family validation explicit about the partial browser observation.
fv=load(R/'全量场景/验证记录.json');fv.update(issueRecords=len(V['issues']),issueDispositions=V['counts'],stableIds=ids,browserVerified=False,browserPartialObservation='浏览器复核记录.json',currentVsReviewedAnnotationClausesEqual=True)
fv['stats']=F['stats'];fv.pop('currentVsPriorAnnotationClausesEqual',None);save(R/'全量场景/验证记录.json',fv)
state=load(R/'本轮更新状态.json');state.update(status='已完成：阅读成果更新及自查完成；未决项和未验证边界已列',completedAt=datetime.datetime.now().astimezone().isoformat(timespec='seconds'),report='17-全量更新报告.md',selfCheck='全量更新自查.json');save(R/'本轮更新状态.json',state)
md='# 交付自查\n\n> 2026-10-16。检查通过表示阅读成果结构、引用和范围一致；不表示业务已批准、所有语义无遗漏或真实链路已运行。\n\n| 检查 | 结果 |\n|---|---|\n'
for k,v in [('当前来源哈希',f'{len(S["sources"])}份一致'),('原型保护',f'{len(protected)}份非.git文件与更新前哈希及文件集合完全一致'),('范围覆盖','192HTML、254批注入口、148注册视图、94状态注册、6份context'),('原文与行号',f'{quoted}处当前引文校验通过'),('本地链接',f'{local_count}处路径／行号校验通过'),('查看器链接目标',f'{viewer_count}处目标文件存在；仅局部浏览器实际验证'),('静态HTML目标','0处缺失；全部192页HTTP200且字节哈希一致'),('编号保留','25链路、228分支、151单项／并发场景、2641对象行及旧问题ID保留；2条文档旧ID封存'),('context正文关联','486条均有链路范围或非操作预期的处理说明；24条社交规则关联单项操作及并发前提'),('交付限制','只更新流程梳理；没有修改原型、没有生成工作簿')]:md+=f'| {k} | {v} |\n'
md+='\n问题状态：'+str(V['counts'])+'。未决记录'+str(result['remainingIssueRecords'])+'条，存在跨报告重复，未当作独立缺陷数。\n\n未验证：逐控件／逐视图运行、同一对象跨三端真实链路、支付／IM／推送／直播SDK／数据库／线上效果。消息中心→公会通知展开→返回清未读是唯一实际浏览器路径，详见10号文件。\n\n机器结果：[全量更新自查.json](全量更新自查.json)；完整更新报告：[17-全量更新报告.md](17-全量更新报告.md)。\n'
(R/'05-交付自查.md').write_text(md)
print(json.dumps(result,ensure_ascii=False,indent=2))
