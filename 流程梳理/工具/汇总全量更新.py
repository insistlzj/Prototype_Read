"""渲染本轮阅读成果并验证来源；不写原型、不生成工作簿。"""
from pathlib import Path
import json,re,hashlib,collections,datetime,concurrent.futures,urllib.request
from urllib.parse import urlsplit,unquote,quote
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'流程梳理';P=ROOT/'liveshow-proto';DATE='2026-10-16'
def load(p):return json.loads(p.read_text())
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def md(name,text):(R/name).write_text(text)
def link(p,line=None,label=None):return f'[{label or Path(p).name}](<{p}{":"+str(line) if line else ""}>)'
def cell(t):return str(t).replace('|','\\|').replace('\n','<br>')
S=load(R/'来源快照.json');F=load(R/'全量场景/场景数据.json');O=load(R/'13-操作影响逐对象数据.json');V=load(R/'本轮问题复核.json');ARCH=Path(V['archive']);H=load(R/'深层分支审查-2026-10-15/审查记录.json');EN={(e['end'],e['key']):e for e in S['entries']};EV={e['id']:e for e in F['evidence']}
# Read only current review decisions. Historical claims remain in archive/historicalRecord.
issues=[i for i in V['issues'] if i['namespace']!='OP']
oldop=load(ARCH/'11-操作与组合影响表.json');currop=load(R/'11-操作与组合影响表.json')
for old,new in zip(oldop['conflicts'],currop['conflicts']):
 refs=[dict(path=str(Path(new['file']).relative_to(ROOT)),line=new['line'],quote=new['quote'],verification='当前文档原文核对')]
 issues.append(dict(id='OP-'+new['id'],namespace='OP',legacyId=new['id'],title=new['title'],status='关闭' if new['status'].startswith('已关闭') else '仍成立',change='关闭' if new['status'].startswith('已关闭') else '保留',conclusion=new['other'],remaining='' if new['status'].startswith('已关闭') else new['other'],evidence=refs,historicalRecord=old,verification='当前三端批注和全部context复核',requirementsApproved=False))
V['issues']=issues
V['counts']=dict(collections.Counter(i['change'] for i in issues));V['namespaces']={'Q':'02旧范围问题','PAGE':'07旧页面差异A编号','TERM':'08术语D/V/R/C编号','E2E':'09旧E编号','DS':'深层分支旧C编号，加DS前缀避免重名','OP':'11旧C编号，加OP前缀','SCOPE':'全量及逐对象待确认','NEW':'本轮新增独立编号'}
save(R/'本轮问题复核.json',V)
HEADER=f'> 更新日期：{DATE}。当前原型与业务文档静态阅读成果，未获需求批准。旧成果已归档。局部浏览器检查见10号记录，不能代表全部页面／后端通过。\n\n'
byid={i['id']:i for i in issues}
def evidence_md(i):
 out=''
 for e in i['evidence']:
  f=ROOT/e['path'];out+='- '+link(f,e['line'])+'：“'+e['quote'].replace('\n',' ')+'”'
  if e.get('page'):out+=' · [带批注页面]('+e['page']+')'
  if e.get('view'):out+='；手动选择 '+e['view']
  out+='\n'
 return out

def render_issues(title,rows):
 text='# '+title+'\n\n'+HEADER+'编号按所属报告区分；同主题跨报告重复出现，不是去重后的独立缺陷数。关闭表示旧指控已有反证或被新规则消除，不代表整个功能验收通过。\n\n| ID | 当前状态 | 主题 |\n|---|---|---|\n'
 for i in rows:text+=f'| {i["id"]} | {i["status"]} | {cell(i["title"])} |\n'
 for i in rows:
  text+=f'\n## {i["id"]} {i["title"]}\n\n状态：{i["status"]}；变化分类：{i["change"]}。\n\n本轮判断：{i["conclusion"]}\n\n'
  if i.get('remaining'):text+='需要确认／修复：'+i['remaining']+'\n\n'
  text+='验证方式：'+i['verification']+'。\n\n'+evidence_md(i)
  if i.get('evidenceBoundary'):text+='\n证据边界：'+i['evidenceBoundary']+'\n'
  text+='\n原始记录：'+link(ARCH/'本轮问题复核.json' if (ARCH/'本轮问题复核.json').exists() else ARCH/'00-阅读入口.md',label='更新前归档')+'；完整旧字段保存在本轮问题复核.json的historicalRecord。\n'
 return text
md('20-全量问题复核.md',render_issues('全量旧问题复核与新增问题',issues))
md('02-冲突与待确认.md',render_issues('范围冲突与待确认：保留Q01—Q16',[i for i in issues if i['namespace']=='Q']))
md('07-批注与页面不一致审查.md',render_issues('批注与页面不一致：当前静态复核',[i for i in issues if i['namespace'] in ['PAGE','NEW']]))
md('08-批注术语定义缺口.md',render_issues('批注术语与定义缺口：当前复核',[i for i in issues if i['namespace']=='TERM']))
md('09-端到端完整性审查.md',render_issues('端到端旧问题复核：E01—E30',[i for i in issues if i['namespace']=='E2E'])+'\n当前完整链路及逐步承接见'+link(R/'全量场景/01-全业务链路场景.md')+'，12维场景关系见'+link(R/'18-场景关系索引.md')+'。旧版09中L01—L10是历史分组，保留在historicalRecord，不能直接当作当前25条L编号。\n')
for ns,name in [('TERM','08-批注术语定义缺口.json'),('E2E','09-端到端完整性审查.json')]:
 rows=[i for i in issues if i['namespace']==ns]
 out=dict(date=DATE,scope='当前三端批注、全部6份context、192页结构及相关共享脚本',completion='静态来源和问题复核完成；真实端到端未运行',counts=dict(records=len(rows),dispositions=dict(collections.Counter(i['status'] for i in rows))),issues=rows,sources=S['sources'],limitations=['旧链路分组仅在historicalRecord中保留；当前采用全量场景25条链路','无正式批准证据','外部支付／IM／直播SDK／数据库未验证'])
 if ns=='TERM':out['coverage']=F['sourceCoverage'];out['defined_examples']=[]
 else:out.update(chains=F['chains'],annotation_coverage=F['sourceCoverage'],page_inventory=F['physicalCoverage'])
 save(R/name,out)

# All physical pages: parse controls, actual file destinations and script references.
class PageParser(HTMLParser):
 def __init__(self):super().__init__();self.nodes=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag in ['a','button','input','select','textarea','form','iframe','script']:self.nodes.append(dict(tag=tag,line=self.getpos()[0],attributes=a))
rows=[];allmissing=[]
for p in map(Path,S['pages']):
 raw=p.read_text();parser=PageParser();parser.feed(raw);related=[e for e in S['entries'] if str(p) in e['pages']];targets=[]
 for node in parser.nodes:
  for attr in ['href','src','action']:
   val=node['attributes'].get(attr)
   if not val or val.startswith(('#','javascript:','mailto:','tel:','data:','http:','https:','//')) or any(x in val for x in ['${','{{','<%']):continue
   part=unquote(urlsplit(val).path)
   if not part:continue
   target=(P/'prototype'/part.lstrip('/')) if part.startswith('/') else (p.parent/part).resolve()
   record=dict(line=node['line'],attribute=attr,value=val,target=str(target),exists=target.is_file());targets.append(record)
   if not record['exists']:allmissing.append(dict(page=str(p),**record))
 row=dict(file=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),end=p.relative_to(P/'prototype/pages').parts[0],registered=any(e['registered'] for e in related),annotations=[e['end']+'/'+e['key'] for e in related],controls=parser.nodes,staticDestinations=targets,inlineScriptLines=[n for n,l in enumerate(raw.splitlines(),1) if '<script' in l and 'src=' not in l],review='HTML、脚本引用、静态导航、状态注册已盘点；业务规则按关联批注／链路核对，未逐控件运行',runtime='仅消息中心与公会通知页本轮打开；其他页面未运行' if p.name in ['message-center.html','host-guild-notifications.html'] else '未运行')
 rows.append(row)
# HTTP reachability is separately labelled and verifies the existing server directory.
server='http://127.0.0.1:8765';index_bytes=urllib.request.urlopen(server+'/index.html',timeout=5).read();server_matches=hashlib.sha256(index_bytes).digest()==hashlib.sha256((P/'prototype/index.html').read_bytes()).digest();assert server_matches
urls=[(str(p),server+'/'+quote(str(p.relative_to(P/'prototype')))) for p in map(Path,S['pages'])]
def httpcheck(item):
 file,url=item
 try:
  with urllib.request.urlopen(url,timeout=10) as r:b=r.read();return dict(file=file,url=url,status=r.status,bytesMatch=hashlib.sha256(b).digest()==hashlib.sha256(Path(file).read_bytes()).digest())
 except Exception as e:return dict(file=file,url=url,error=str(e))
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:http=list(pool.map(httpcheck,urls))
assert all(i.get('status')==200 and i.get('bytesMatch') for i in http),[i for i in http if not i.get('bytesMatch')]
save(R/'19-页面静态复核.json',dict(date=DATE,pages=rows,missingStaticDestinations=allmissing,httpChecks=http,serverRootMatches=True,browserCoverage=['message-center.html','host-guild-notifications.html'],limitations=['HTTP200与文件一致仅证明服务及内容可达，不证明渲染或交互正确','动态拼接导航需阅读代码，未自动推测参数','HTML扫描不替代逐状态浏览器验证']))
text='# 页面静态复核与服务可达性\n\n'+HEADER+f'192份HTML全部读取并盘点控件、脚本和静态目标；192个页面HTTP200且内容哈希与当前文件一致。未逐控件／逐状态操作，不用这一结果宣称页面语义或运行验收通过。静态缺失目标共{len(allmissing)}处。\n\n| 页面 | 批注／注册 | 控件数 | 静态目标数 | 验证边界 |\n|---|---|---|---|---|\n'
for row in rows:text+=f'| {link(row["file"])} | {len(row["annotations"])}/{row["registered"]} | {len(row["controls"])} | {len(row["staticDestinations"])} | {row["runtime"]} |\n'
if allmissing:
 text+='\n## 缺失静态目标\n\n'
 for i in allmissing:text+='- '+link(i['page'],i['line'])+' → `'+i['value']+'`\n'
md('19-页面静态复核.md',text)
# 07 machine manifest now covers all pages while preserving old A issue associations.
legacy_pages=load(ARCH/'07-审查页面来源.json')['pages']
save(R/'07-审查页面来源.json',dict(date=DATE,scope='全部192页结构及当前源哈希；旧15项差异与新增5项另列',pages=[dict(page=row['file'],sha256=row['sha256'],legacyIssueIds=[p['id'] for p in legacy_pages if p['page']==row['file']],annotations=row['annotations'],runtime=row['runtime']) for row in rows],issues=[i for i in issues if i['namespace'] in ['PAGE','NEW']],staticManifest='19-页面静态复核.json'))

# Each document clause records scope explicitly, rather than only a filename/hash.
section_map=[
 ('账号与登录',['L01','L02','L03']),('用户资料',['L02']),('首页与发现',['L23','L08']),('直播观看与互动',['L08','L09']),('礼物与打赏',['L12','L13']),('签到与任务',['L19']),('邀请拉新',['L20']),('用户成长与身份',['L17','L15']),('粉丝团（',['L16','L17']),('钱包与充值',['L11','L13','L14']),('IM 社交',['L21','L24']),('工会（',['L04','L05']),('个人中心',['L01','L02','L03']),('合规与安全',['L09','L03']),('主播入驻',['L04']),('主播个人主页',['L23','L17']),('开播设置',['L07','L08']),('直播间管理',['L09']),('连麦与 PK',['L10']),('粉丝团管理',['L16']),('主播收益与提现',['L18','L22']),('主播数据中心',['L22']),
 ('工会账号与信息',['L06','L02']),('成员与入会管理',['L04','L05']),('主播管理',['L07','L05']),('主播结算',['L18']),('工会运营',['L24']),('数据与收益',['L22']),('运营账号与虚拟',['L25']),('封禁处置',['L03','L09']),('工会管理',['L06','L04','L05']),('直播管理与监控',['L07','L09','L22']),('内容审核',['L09','L02']),('礼物与道具配置',['L12','L15','L17']),('运营配置',['L19','L20','L23','L24']),('财务结算',['L18','L14']),('数据分析与报表',['L22']),('系统配置',['L25']),('用户管理',['L01','L03','L21']),
 ('用户与主播身份',['L01','L03','L04']),('主播的入会/退会',['L04','L05']),('公会账号与权限',['L06']),('直播场次',['L07','L22']),('直播间进入规则',['L08']),('开播权限',['L07']),('连麦机制',['L10']),('账号关系',['L21']),('直播中主播',['L09']),('粉丝群',['L16']),('主播连麦',['L10']),('举报与处置',['L09']),('金币充值与消费',['L11','L13']),('礼物和门票',['L12','L08']),('幸运礼物',['L12','L13']),('道具',['L15']),('退款订单',['L14']),('主播收益',['L22','L12']),('对账与结算',['L18']),('资金充值到分成示例',['L11','L12','L18']),('运营账号',['L25']),('任务、邀请与系统通知',['L19','L20','L24'])]
docmap=[]
for ev in F['evidence']:
 if ev['end']!='context':continue
 title=ev['section'];cids=[];reason=''
 if ev['key']=='社交关系规则补充.md':cids=['L09','L10'] if '各角色' in title else ['L21','L09','L16','L10'];reason='逐条核对拉黑／删除后的动作资格及角色权限；单项规则不直接决定并发终态'
 elif ev['key']=='消息通知规则.md':cids=['L24','L21'] if any(t in title for t in ['互动','一对一']) else ['L24','L16'] if '粉丝团' in title else ['L24','L04','L05','L09'] if '系统通知' in title else ['L24'];reason='对应消息事件、接收角色和点击落点；按记录类型核对'
 else:
  leaf=title.split(' / ')[-1]
  for token,ids in section_map:
   if token in leaf:cids=ids;break
  if not cids:
   if '核心用例' in title:cids=[c['id'] for c in F['chains']];reason='角色用例范围目录，保留为范围参照，不作为具体状态迁移预期'
   elif '参与方' in title or '上架与币种' in title or '端口语言' in title:reason='全局角色／语言／币种约束，适用于三端；不单独构造操作结果'
   else:reason='范围说明或跨主题备注，需回当前完整小节理解；不据独立行推出确定业务结果'
  if not reason:reason='按当前小节业务对象映射相关链路；候选适用范围，逐条结果仍以完整原文和同条件批注为准'
 evidence_scope=[r['id'] for r in F['scenes'] if set(r['chains'])&set(cids)]
 docmap.append(dict(evidence=ev['id'],file=ev['file'],line=ev['line'],quote=ev['quote'],chains=cids,sceneScope=evidence_scope,scopeReason=reason,sourceType=ev['kind'],execution='未执行',notConcurrentProof=True))
# 12 dimensions: explicit conditions/effects, old branch IDs and current open questions.
DIMS=['角色与权限','业务对象与关联标识','前置条件','正常路径','异常与恢复','逆向操作','时间与周期','并发与重复','配置变化','历史与数据归属','跨端与通知','终态与验证边界']
chains=[]
for c in F['chains']:
 related=[]
 for i in issues:
  keys={e.get('key') for e in i['evidence']}
  inherited=i.get('historicalRecord',{}).get('chains',[]) if i['namespace']=='DS' else []
  if set(keys)&set(c['keys']) or c['id'] in i.get('chains',[]) or c['id'] in inherited:related.append(i['id'])
 documents=[r['evidence'] for r in docmap if c['id'] in r['chains']]
 branches=c['branches'];openbranches=[b['id'] for b in branches if b['status']!='已明确'];page_scenes=[s['id'] for s in F['scenes'] if c['id'] in s['chains']]
 dim=[]
 for name in DIMS:
  notes={
  '角色与权限':c['roles']+'；每步按执行时账号、关系与授权核对，不跨角色套用',
  '业务对象与关联标识':c['object']+'；页面静态示例不是同一对象后端追踪证据',
  '前置条件':c['start']+'；具体限制见各步骤完整批注',
  '正常路径':' → '.join(s['action'] for s in c['steps']),
  '异常与恢复':'；'.join(b['scenario']+'：'+b['result'] for b in branches if re.search('失败|异常|超时|拒绝|不足|重试|断|失效',b['scenario'])) or '原清单未列独立失败规则；不补造失败终态，外部失败恢复未运行',
  '逆向操作':'；'.join(b['scenario']+'：'+b['result'] for b in branches if re.search('取消|删除|退出|移除|解除|恢复|下架|退会|注销',b['scenario'])) or '未列逆向分支；是否允许撤销须看原文，不将缺少规则写成不适用',
  '时间与周期':'；'.join(b['scenario']+'：'+b['result'] for b in branches if re.search('日|月|时|周期|期|先后|截止',b['scenario'])) or '来源未给独立周期；仅保留事件顺序，时区问题见D05',
  '并发与重复':'；'.join(b['scenario']+'：'+b['result'] for b in branches if re.search('同时|并发|重复|重试|先成功|顺序|迟到',b['scenario'])) or '本链路未找到完整并发裁决；不能把单项结果相加当终态',
  '配置变化':'；'.join(b['scenario']+'：'+b['result'] for b in branches if re.search('配置|修改|变更|开关|上下架|停用|启用|锁定',b['scenario'])) or '无独立配置变更结果；关联后台配置仍须按新旧记录生效点核对',
  '历史与数据归属':'；'.join(b['scenario']+'：'+b['result'] for b in branches if re.search('历史|归属|重入|重新|退款|跨日|收益|记录',b['scenario'])) or '终态及查询见主路径末步；数据库持久化未验证',
  '跨端与通知':'涉及端：'+', '.join(sorted({e['end'] for e in S['entries'] if e['key'] in c['keys']}))+'；接收事件与去向逐条参照消息通知规则。未用多个静态账号证明真实同步',
  '终态与验证边界':c['end']+'；未解决／未核实分支：'+(', '.join(openbranches) or '本清单无已列阻塞')+'；后端与线上未验证'}
  dim.append(dict(dimension=name,result=notes[name],status='存在待确认／未核实项，见关联问题' if openbranches else '当前来源可定位，未运行',evidenceScope=list(dict.fromkeys(eid for s in c['steps'] for eid in s['evidence'])),boundary='来源包只标适用范围，不作为每个分支的精确直接证据'))
 chains.append(dict(id=c['id'],title=c['title'],object=c['object'],roles=c['roles'],steps=c['steps'],branches=branches,dimensions=dim,scenarioIds=page_scenes,documentEvidence=documents,issues=related,openIssues=[iid for iid in related if byid[iid]['status'] not in ['关闭','排除']],runtime='未运行同一业务对象的三端链路'))
# 条目到问题是范围关联，避免页上任意一句就被当成问题的精确证据。
relationships=dict(date=DATE,chains=chains,documentRuleScope=docmap,socialRuleMappings=O['ruleCoverage'],legacySceneIds=[s['id'] for s in O['operations']+O['concurrent']],boundaries=['语义判断以本轮问题复核和完整原文为准','关联是适用范围，不证明所有条件均已定义','并发候选没有结果的对象继续留空','不穷尽任意事件数的组合'])
save(R/'18-场景关系索引.json',relationships)
text='# 深层场景关系索引\n\n'+HEADER+'25条链路沿用原编号，228个分支保留；每条链路按12个维度记录当前范围、异常、逆向、时序、并发、配置、归属与跨端。候选关联不自动成为已批准预期。\n\n'
for c in chains:
 text+=f'## {c["id"]} {c["title"]}\n\n对象：{c["object"]}；角色：{c["roles"]}。关联逐页场景{len(c["scenarioIds"])}条、文档条目{len(c["documentEvidence"])}条。\n\n关联未决项：'+(', '.join(c['openIssues']) or '本清单未匹配独立问题，仍未运行')+'。\n\n| 维度 | 结果／剩余条件 |\n|---|---|\n'
 for d in c['dimensions']:text+=f'| {d["dimension"]} | {cell(d["result"])} |\n'
 text+='\n主路径与分支原文：'+link(R/'全量场景/01-全业务链路场景.md',label=c['id']+'完整链路')+'；逐条证据见'+link(R/'全量场景/10-来源原文.md')+'。\n\n'
text+='## context逐条适用范围\n\n不只登记文件名：全部486条正文规则／范围／示例逐条记录链路、场景范围或不单独构造业务预期的理由。单项权限不推导并发终态。完整场景ID集合存JSON，避免Markdown重复展开数十万关系。\n\n| 证据ID | 来源 | 链路 | 处理与边界 |\n|---|---|---|---|\n'
for row in docmap:text+=f'| {row["evidence"]} | {link(row["file"],row["line"])} | {", ".join(row["chains"])} | {cell(row["scopeReason"])} |\n'
text+='\n## 社交补充逐条落实\n\n| 行 | 单项操作 | 说明 |\n|---|---|---|\n'
for row in O['ruleCoverage']:text+=f'| {row["line"]} | {", ".join(row["operations"])} | {cell(row["note"])}；并发仅作为前提，不推出最终顺序 |\n'
md('18-场景关系索引.md',text)

# Flows retain the original F01—F10 navigation IDs and map to current L chains.
oldflow=(ARCH/'01-主要流程与分支.md').read_text();flowtitles=re.findall(r'^## (F\d+) ([^\n]+)',oldflow,re.M)
FM={'F01':['L01','L02','L03'],'F02':['L04','L05'],'F03':['L07','L08','L10'],'F04':['L11','L12','L13','L14'],'F05':['L18','L22'],'F06':['L05','L06'],'F07':['L09'],'F08':['L16','L21','L24'],'F09':['L19','L20'],'F10':['L25','L06']}
if not flowtitles:flowtitles=[(k,k) for k in FM]
text='# 主要流程与分支\n\n'+HEADER+'F01—F10为原阅读分组，L01—L25为当前链路；二者只作导航映射，不混用编号。当前规则来源互相支持不代表业务已批准。\n\n'
for fid,title in flowtitles:
 text+=f'## {fid} {title}\n\n'
 for c in [x for x in chains if x['id'] in FM.get(fid,[])]:
  text+=f'### {c["id"]} {c["title"]}\n\n'
  for s in c['steps']:
   ev=EV[s['evidence'][0]]
   text+=f'- {s["id"]}：{s["action"]} → {s["result"]}。'+link(ev['file'],ev['line'],s['page'])+'\n'
  text+='\n异常、逆向、恢复：'+ '；'.join(b['id']+' '+b['scenario']+'：'+b['result'] for b in c['branches'])+'\n\n终态：'+next(x['end'] for x in F['chains'] if x['id']==c['id'])+'。未决项：'+(', '.join(c['openIssues']) or '本表未匹配独立问题')+'。\n\n'
text+='## 本次明确的口径变化\n\n- 主播和公会周期涨粉统一为新增关注人数减取关人数，允许负数。\n- 平台／场次／粉丝团贡献加入成功门票实际支付金币；幸运返奖不冲减贡献。财富等级仍按送礼成长，不能因名称相近自动加入购票成长。\n- 公会及主播总收益含门票，礼物明细仅礼物，两者不要求数值相等。\n- 消息中心有公会通知时提供入口；当前主播仍可从主播中心进入。\n\n本节出处见当前20个变化条目的完整批注：'+link(R/'重建差异.json')+'、'+link(R/'全量场景/10-来源原文.md')+'。\n'
md('01-主要流程与分支.md',text)
text='# 原型阅读顺序\n\n'+HEADER+'先主路径，再逆向、异常、跨端和时间边界；问题涉及哪条链路就读取其全部相关来源，不机械全量重扫。\n\n| 次序 | 范围 | 链路 |\n|---|---|---|\n'
for n,(title,ids) in enumerate([('账号／角色／凭证',['L01','L02','L03']),('入会认证与退出',['L04','L05','L06']),('开播准入与秩序连麦',['L07','L08','L09','L10']),('充值送礼、账单退款',['L11','L12','L13','L14']),('装扮与粉丝团、等级',['L15','L16','L17']),('分成账户和统计',['L18','L22']),('签到与邀请',['L19','L20']),('社交与通知',['L21','L24']),('发现配置及运营权限',['L23','L25'])],1):text+=f'| {n} | {title} | {", ".join(ids)} |\n'
text+='\n每条链路的步骤、结束条件、未决分支、12维关系见'+link(R/'18-场景关系索引.md')+'；页面名未知时先检索03和04号索引，再回当前批注。\n'
md('06-原型阅读顺序.md',text)
# Browser observations are intentionally limited to the actions actually performed.
browser=dict(date=DATE,service=server,serverRootMatches=True,method='Chrome浏览器实际点击，当前新建阅读标签，不修改原型文件',observations=[dict(step=1,page='message-center.html',result='页面及对应批注显示，公会通知入口位于会话列表，消息未读总数9；Sari预览含回复即好友文案'),dict(step=2,action='点击公会通知',page='host-guild-notifications.html?from=message-center&notice=guild-schedule&seen=guild',result='本周直播排班展开，按钮为收起，另3条为展开全文'),dict(step=3,action='点击返回',page='message-center.html?seen=guild',result='消息未读总数8，公会通知未读1消失，其他会话仍在')],notVerified=['未逐页验证192页浏览器渲染','未逐状态操作148个注册视图或94处状态注册','未运行同一对象跨三端链路','支付、IM、直播SDK、推送、文件解析、数据库和线上行为','历史浏览器故障本轮没有重现为全局阻塞；公会通知页批注展开未单独验证'])
save(R/'浏览器复核记录.json',browser)
md('10-继续复核与浏览器阻塞诊断.md','# 本轮浏览器复核与验证边界\n\n'+HEADER+'本轮浏览器可用；旧阻塞诊断仅在历史归档，不能继续当作当前全局阻塞。现有8765服务与当前index文件哈希一致，未重启或终止未知服务。\n\n'+ '\n'.join(f'- {x.get("action","打开消息中心")}：{x["result"]}。' for x in browser['observations'])+'\n\n未验证：\n\n'+'\n'.join('- '+x for x in browser['notVerified'])+'\n\n192页HTTP可达与静态检查见'+link(R/'19-页面静态复核.md')+'。HTTP成功不能证明视图自动展开或后端生效。\n')
# Update old dated deep-review endpoints as current compatibility entrypoints.
DROOT=R/'深层分支审查-2026-10-15'
(DROOT/'00-审查入口.md').write_text('# 深层分支审查入口\n\n'+HEADER+'目录日期保留以免旧链接失效；内容更新于本轮，更新前版本见'+link(ARCH/'深层分支审查-2026-10-15/00-审查入口.md')+'。当前25条链路、228个分支、12维关系见'+link(R/'18-场景关系索引.md')+'；问题按原C编号保留，跨报告用DS前缀。\n')
for p in DROOT.glob('*.md'):
 if p.name.startswith('01-'):p.write_text(render_issues('深层分支旧问题复核',[i for i in issues if i['namespace']=='DS']))
 elif p.name.startswith('02-'):p.write_text('# 深层分支矩阵\n\n'+HEADER+link(R/'全量场景/01-全业务链路场景.md')+'记录全部228个原分支，保留Lxx-Bxx；'+link(R/'18-场景关系索引.md')+'补充12维场景关系。\n')
 elif p.name.startswith('03-'):p.write_text('# 深层来源覆盖\n\n'+HEADER+link(R/'全量场景/07-来源页面视图覆盖.md')+'列出254批注入口、192HTML、148注册视图、94状态注册与6份context。覆盖不等于语义验收。\n')
save(DROOT/'来源快照.json',dict(date=DATE,sources=S['sources']))
save(DROOT/'验证记录.json',dict(date=DATE,annotationEntries=254,physicalPages=192,viewChecks=148,chains=25,branches=228,stableIdsPreserved=True,sourceHashesMatch=True,semanticAuditPassed=False,backendVerified=False,browserCoverage=browser['observations']))
# Regenerated scene reports must use current dispositions for all prior candidates.
for item in F['extraPending']:
 if item['id'] in byid:
  cur=byid[item['id']];item.update(status=cur['status'],question=cur['conclusion'])
for scene in F['scenes']:
 scope_ids=[i['id'] for i in issues if any(e.get('key')==scene['key'] for e in i['evidence'])]
 scene['relatedIssues']=list(dict.fromkeys(scene['relatedIssues']+scope_ids))
 scene['issueDispositions']={iid:byid[iid]['status'] for iid in scene['relatedIssues'] if iid in byid}
 scene['openIssues']=[iid for iid,status in scene['issueDispositions'].items() if status not in ['关闭','排除']]
 scene['relationBoundary']='同入口范围关联，不表示所有问题均适用于本场景全部条件；精确条件见问题证据'
F['issueLedger']=str(R/'本轮问题复核.json');F['stats']['pendingIssueCandidates']=sum(i['status'] not in ['关闭','排除'] for i in issues);F['stats']['issueRecords']=len(issues);F['documentRuleScopeIndex']=str(R/'18-场景关系索引.json');F['browserVerification']=browser
save(R/'全量场景/场景数据.json',F)
md('全量场景/08-冲突缺口与未核实.md',render_issues('全量场景关联问题：本轮状态',issues))
# Correct old hard-coded narrative that no longer matches changed clauses or page counts.
p=R/'全量场景/01-全业务链路场景.md';t=p.read_text().replace('当前条目已逐条比对一致','当前条目已逐条比对，20个变化入口已重新复核').replace('L09-B02、L09-B04、L22-B09已收窄过度结论','L09-B02、L09-B04、L22-B09已收窄过度结论，L22-B05、L22-B06已按新规则更新');p.write_text(t)
p=R/'全量场景/00-全量场景入口.md'
t=p.read_text().split('\n本轮全量问题状态及关闭依据以',1)[0]
t=t.replace('四份未注册系统页用文件入口追溯','四份有批注但未注册的系统页及两份无批注旧页面均用文件入口追溯')
t=t.replace('所有场景均未执行；','业务场景均未执行；消息中心与公会通知有局部导航观察；').replace('查看器链接仅静态校验，未验证浏览器展开。','查看器链接目标均静态校验；仅消息中心／公会通知局部链接实际打开。')
t=t.replace('| 问题与范围候选 | 44 | 未正式裁决 |',f'| 未决问题记录 | {F["stats"]["pendingIssueCandidates"]} | 跨报告有重复，不是独立缺陷数 |')
t=t.replace('所有运行状态为未执行：未测试真实支付、IM、直播SDK、数据库或线上效果。','业务场景未执行；消息中心／公会通知有局部导航观察。未测试真实支付、IM、直播SDK、数据库或线上效果。')
p.write_text(t+'\n本轮全量问题状态及关闭依据以'+link(R/'20-全量问题复核.md')+'为准；来源变化条目见'+link(R/'重建差异.json')+'。\n')

# Do not carry historical replacement narratives as current source versions.
md('12-原型替换重建说明.md','# 当前原型定位与更新说明\n\n'+HEADER+'当前原型根目录：'+link(P/'prototype/index.html')+'；Git HEAD：`'+V['prototypeHead']+'`。本轮读取全部6份context与三端批注，保留旧编号，修复引用，旧成果归档至'+link(ARCH/'00-阅读入口.md')+'。具体变更与验证见'+link(R/'17-全量更新报告.md')+'；上一次原型替换的过程叙述仅见归档，不作为当前版本判断。\n')
# Root entry favors current evidence and precise boundaries.
text='# 原型阅读入口\n\n'+HEADER+f'当前原型：{link(P/"prototype/index.html")}；来源版本 `{V["prototypeHead"][:12]}`。当前盘点192份独立HTML、254个批注入口（含64个虚拟视图批注）、148个注册视图、6份context文档。25条业务链路及228个分支用于阅读，不是已执行测试用例。\n\n| 需要什么 | 入口 |\n|---|---|\n'
for a,b in [('更新了什么、还剩什么','17-全量更新报告.md'),('快速按页面找当前来源','03-来源细节索引.md'),('全部独立页面','04-独立页面清单.md'),('主流程与旁枝','01-主要流程与分支.md'),('复杂场景、跨端和并发关系','18-场景关系索引.md'),('当前问题与关闭依据','20-全量问题复核.md'),('逐页业务场景与原文','全量场景/00-全量场景入口.md'),('单项逐对象／并发候选','13-操作影响阅读入口.md'),('页面和静态链接检查','19-页面静态复核.md'),('本轮浏览器验证范围','10-继续复核与浏览器阻塞诊断.md'),('来源哈希','来源快照.json'),('自查结果','05-交付自查.md')]:text+='| '+a+' | '+link(R/b)+' |\n'
text+='\n日常问答先用索引定位，回当前批注和相关context完整条目，涉及实现再查HTML与共享脚本。新增或变化文件必须直接读取；哈希一致仅允许复用定位，不证明旧判断正确。Q、A、D/V/R/C、E、DS、OP编号按报告命名空间区分，不互相覆盖。\n\n旧成果：'+link(ARCH/'00-阅读入口.md')+'。原型未修改，未生成工作簿。\n'
md('00-阅读入口.md',text)
counts=V['counts'];pending=[i for i in issues if i['status'] not in ['关闭','排除']]
text='# 全量更新报告\n\n'+HEADER+'已按当前原型更新索引、来源快照、页面清单、主流程、全量场景、逐对象关系、深层分支与旧审查报告。只修改阅读成果，未修改原型、未生成工作簿。\n\n## 当前范围与版本\n\n'+f'- 原型根：{P}；Git HEAD：`{V["prototypeHead"]}`。\n- 192份HTML、254个批注入口、64份虚拟视图批注、148个注册视图、94处页面状态注册；6份context全部列入逐条来源／范围关系。\n- 25条链路、228个链路分支、1228条逐页规则场景、1070条字段检查点、486条context正文候选、3320条原文证据。主路径／分支／逐页记录可重叠，不是去重业务数量。\n- 八类操作31个单项、120个并发候选、2641个逐对象行保留；45操作／69组合摘要仍可按旧编号查找。\n- 6份页面未注册查看器，其中4份有批注的系统参数／审计页面，另2份admin-system-permission.html、my-outfits.html无独立批注，范围仍待确认。\n\n'
text+='## 与更新前的变化\n\n'+link(R/'重建差异.json')+'记录20个批注入口变化；未增删独立页面或批注入口。主要变化是贡献纳入门票、粉丝指标统一净增、公会／主播收益纳入门票、粉丝群群主身份和公会通知入口。原文已重新定位。\n\n'
text+=f'问题记录共{len(issues)}条（跨报告有重复，不能当作独立缺陷数）：关闭{counts.get("关闭",0)}，变化{counts.get("变化",0)}，保留{counts.get("保留",0)}，排除／分类修正{counts.get("分类修正",0)}，新增{counts.get("新增",0)}。未决记录{len(pending)}条；旧问题保留编号及更新前记录。\n\n'
text+='关闭代表项：DS-C01／A11（当前净增允许负数）、E29／DS-C26（门票总收益与礼物明细范围已区分）、Q08／E06（停用使初审与终审申请失效）、Q11／E21（结束后举报仍可处理）、A03／A04（运营账号非法送礼示例已修正）、E03（运营登录映射已明确）。A02因现行批注不再支持旧的全部缺字段指控而撤销；OP-C01—C03旧社交冲突关闭。详细反证见20号报告。\n\n'
text+='新增5项：主页私信未携带peer、媒体消息绕过非好友额度、被送礼互动通知的范围未同步、回复即好友的示例文案不符，以及改密／重置成功未返回登录。导航与额度问题为静态代码发现；通知为范围待确认，示例文案另在浏览器观察到。\n\n'
text+='## 剩余重点问题\n\n- 幸运礼物：余额净变动符号、扣款与结算时点、未结算可用余额、跨日归属、收益基数和舍入范围仍需统一。\n- 账号／身份：未注册手机号邮箱分流、绑定展示承接、主播注销与公会／申请／权限终态、新主播公会权限初值未完整闭合。\n- 直播／交易：公会有效与停用边界、断流重连终态、重复开播、购票与结束竞争、首充限购并发、道具过期购买与礼物改价确认仍待明确。\n- 社交／任务／统计：非好友角色例外、群主团籍豁免、现有连麦遇拉黑、有效观看计时、固定任务与可配条件、同日任务关闭再开、同公会多段归属与实际时区仍有未决项。\n- 范围：线上提现、申诉冻结、邀请返利、平台发币与公会管理账号停用等旧清单描述未与当前原型统一；不能擅自以某一来源覆盖。\n\n完整未决和关闭项：'+link(R/'20-全量问题复核.md')+'。\n\n'
text+='## 验证与未验证\n\n- 全部当前来源哈希、证据原文及行号、页面映射和编号由脚本检查；旧ID保留或封存，不把新规则重用为不相关旧场景。\n- 全部192页HTTP200且内容与当前文件哈希一致；这只证明本机服务内容可达。\n- 浏览器实际检查消息中心→公会通知→返回：最新通知展开，消息未读总数9→8。其他192页的逐控件、148视图、94状态注册未全量操作。\n- 未运行同一业务对象跨三端链路；支付、IM、直播SDK、渠道退款、真实导入、数据库及线上效果均未验证。静态候选不是正式产品裁决；无审核冻结／批准证据。\n- 字段／条目映射覆盖不代表语义无遗漏，复杂并发未知项没有补造预期。\n\n'
text+='## 历史与交付\n\n'+link(ARCH/'00-阅读入口.md',label='完整更新前归档')+'；原型保护清单保留更新前全文件哈希。当前自查见'+link(R/'05-交付自查.md')+'。未来同类更新先重建来源，再人工复核问题与链路，不能仅运行生成脚本宣称全量语义更新。\n'
md('17-全量更新报告.md',text)
print(json.dumps(dict(issues=len(issues),counts=counts,pending=len(pending),pages=len(rows),missingStaticTargets=len(allmissing),documentClauses=len(docmap),chains=len(chains)),ensure_ascii=False))
