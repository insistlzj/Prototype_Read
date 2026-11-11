"""本轮人工复核的决策与可重复输出。只写阅读成果；不自动批准业务。"""
from pathlib import Path
import json,re,hashlib,datetime,difflib,collections,html,subprocess
from urllib.parse import unquote,urlsplit
ROOT=Path(__file__).resolve().parents[2]; R=ROOT/'流程梳理'; P=ROOT/'liveshow-proto'; DATE='2026-10-16'
STATE=json.loads((R/'本轮更新状态.json').read_text()); ARCH=Path(STATE['archive'])
def read(p):return json.loads(p.read_text())
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
S=read(R/'来源快照.json'); PREV=read(ARCH/'来源快照.json'); EN={(e['end'],e['key']):e for e in S['entries']}
# 旧编号均有独立命名空间；历史正文另存归档，绝不冒充当前结论。
ledger=[]
def ev(file,needle):
 file=Path(file);file=file if file.is_absolute() else P/file
 hits=[(n,l) for n,l in enumerate(file.read_text().splitlines(),1) if needle in l]
 assert hits,(str(file),needle)
 n,l=hits[0];return dict(path=str(file.relative_to(ROOT)),line=n,quote=needle,source_line=l,verification='当前文件原文核对')
def entry_ev(end,key,needle=None):
 e=EN[end,key];qs=[q for sec in e['sections'] for q in sec['d']]
 q=next((q for q in qs if needle and needle in q),None) if needle else None
 if not q:q=next((q for sec in e['sections'] if sec['t'] in ['业务','业务规则','交互'] for q in sec['d']),qs[-1])
 probes=[q,json.dumps(q,ensure_ascii=False)[1:-1],q.replace("'","\\'")]
 lines=Path(e['source']).read_text().splitlines();n=next((n for n,l in enumerate(lines,1) if n>=e['line'] and any(v in l for v in probes)),0)
 if not n:n=next(n for n,l in enumerate(lines,1) if any(v in l for v in probes))
 return dict(path=str(Path(e['source']).relative_to(ROOT)),line=n,quote=q,source_line=lines[n-1],page=e['url'],view=e['view'],key=key,end=end,verification='当前完整批注条目与关联页核对')
def old_refs(obj):
 out=[]
 for x in obj.get('evidence',obj.get('occurrences',[])):
  f=x.get('path',x.get('source',x.get('file','')));q=x.get('quote',x.get('text',''))
  if not f or not isinstance(f,str) or not q:continue
  p=Path(f);p=p if p.is_absolute() else ROOT/p
  if not p.is_file():continue
  probes=[q,json.dumps(q,ensure_ascii=False)[1:-1],q.replace("'","\\'")]
  hits=[(n,l) for n,l in enumerate(p.read_text().splitlines(),1) if any(v in l for v in probes)]
  if hits:
   n,l=hits[0];out.append(dict(path=str(p.relative_to(ROOT)),line=n,quote=q,source_line=l,verification='当前原文重新定位'))
 return out
# status、reason 是本次审阅决定，不从哈希一致、关键词或数量自动生成。
D={
'D01':('关闭','当前用户主页已改为累计成功赠送的礼物价值，成功、失败／撤销和运营账号排除在礼物展馆及榜单已有明确规则；不再沿用“有效礼物未解释”这一旧指控。'),
'D02':('关闭','安装邀请链接首次归因、下载安装并注册成功、同新用户一次、注册时发10金币均已写明；清单中的返利范围另见Q14。'),
'D07':('变化','分享成功事件已有定义：复制成功、图片保存成功或系统分享返回发送成功；同一行为重复回传去重。仅剩同房间多次独立分享是否均计数的去重业务键待确认。'),
'D08':('变化','任务页已写送出任意1个礼物，不能继续称完全没有单位；多档条件、连送数量与幸运礼物计数仍需明确并与DS-C02一起核对。'),
'D13':('变化','迟到成功不自动发币、查原渠道后退款／人工核对已有规则；仅支付有效期的起算、长度和精确截止待确认。'),
'D16':('变化','推送目标已区分当前公会主播与可登录公会端账号，不再泛指公会用户；关系快照取得时点和封禁／注销等目标排除仍待确认。'),
'D17':('关闭','推送管理字段和系统概要已定义服务端接受任务的去重账号数，不等同送达、展示、已读。'),
'D20':('变化','现已明确同一账号可管理多个公会及选中公会被停用时退出；新增／解除绑定的入口、执行时点与其他会话范围仍未完整说明。'),
'D21':('变化','须区分报表区间裁剪与实际推流区间，不再把所有“有效起止”视为同一术语；具体使用处的断流计时冲突另见D29。'),
'D22':('关闭','直播记录已明确实际开始的场次，进行中累计、结束后保留；不能再将“有效记录”作为全局未定义问题。'),
'D27':('变化','群免打扰已明确只关设备提醒，不影响接收和群内展示；单聊通知、App内横幅和角标的逐项范围仍需补清，不将群规则直接推广。'),
'R02':('变化','已明确指主播与公会在会关系，用户端限定最近一段；同公会多次入退会在公会端的全段或最近段范围仍待确认，关联DS-C33。'),
'R03':('变化','用户需求清单已有一期等级勋章范围，不要求凭空新增分档特权；加入页“等级权益”只保留引用不足的表达问题。'),
'D29':('变化','主播中心时长明确包含暂停断流，但直播数据字段仍称正常推流；这是具体计时口径冲突，不能只写全局没定义。'),
'D31':('变化','当前主播与公会指标均改为新增关注人数减取关人数；旧的“不扣取关”结论关闭。重复关注事件计数／周期去重维度仍待确认。'),
'V06':('变化','部分页面已写忽略大小写、昵称或ID模糊搜索；只保留未定义匹配语义的入口，不泛称所有页面缺失。'),
'C03':('关闭','购买扣减、返奖增加两条钱包流水与订单净消耗已统一；一次结算余额并不等于一条流水。余额时点和符号问题另见FULL-CONF-01、DS-C20。')}
E={
'E01':('变化','设置批注已写验证码绑定当前账号、占用拒绝且不合并资产；原型尚无完整绑定操作页／入口，收窄为展示与流程承接不足。'),
'E03':('关闭','公会运营账号详情批注已明确运营登录名映射@op.test邮箱，使用公会设置的密码，不走验证码；登录规则承接已补齐，真实认证未验证。'),
'E04':('仍成立','后台登录页仍属制作规范及批注明示待补齐，保留已知入口缺失；不把它列作新发现。'),
'E06':('关闭','当前三端与系统概要均明确公会初审、平台终审待审入会单失效，保留原因时间，旧单不复活并可申请其他启用公会。'),
'E09':('仍成立','当前开播按钮仍固定跳普通主播页?entry=start-live；start-live-config.js只调整分类文案，未传本场房型、票价与密码。仅静态实现差异。'),
'E11':('仍成立','common.js接受邀请仍只移除当前邀请并Toast，未进入连麦画面／清除全部邀请；确认的是当前演示承接不足，真实SDK未验证。'),
'E12':('变化','支付迟到成功的查渠道、待退款／人工核对已有路径；仅有效期起算长度、最后首充／限购资格并发仍未定义。'),
'E13':('关闭','当前退款中、渠道成功内部扣币未完仍处理中、补流水、原单重试和撤权后继续已有明确恢复规则；不再重复指控这些路径缺失。'),
'E14':('关闭','现有三端均保留扣减／返奖两条钱包流水，消费订单为净额；关闭旧的一条／两条流水冲突，另保留余额时序及符号问题。'),
'E15':('变化','唯一操作编号、逐次开奖留结果、超时只补未完成步骤已补齐；多笔待结算余额占用仍待确认，关联DS-C24。'),
'E18':('变化','批次和来源明细跨文件防重、重传查原结果已明确；同文件相同主播／公会ID多行是合法分项还是重复、金额如何汇总仍待确认。'),
'E19':('排除','真实解析、入账、持久化属于后端，原型可用Toast表达；本轮不要求静态演示实现真实财务效果。'),
'E20':('变化','当前通知文档有通过、驳回、移除等细分落点，公会详情支持来源返回及定位；仍需明确被移除无退会申请时的历史关系标识与直达定位，不能等同已运行验证。'),
'E21':('关闭','用户举报、系统概要和后台已统一结束后仍处理，只禁止再次强制关播；旧的结束即作废冲突已不存在。'),
'E23':('关闭','当前社交补充、系统概要、三端关联批注一致保留好友与公开搜索主页；解除全部拉黑后恢复原好友私信，已解除关注／团籍不恢复。'),
'E26':('变化','当前邀请安装归因和注册发10金币已明确；旧清单邀请码手调、返利与后台配置的本期范围冲突保留，不再称成功事件未定义。'),
'E27':('变化','分享成功事件和回传去重已明确，送礼页有任意1个礼物；剩有效观看状态、连送计数与可配多档一致性需确认。'),
'E28':('变化','月视图已重申最近一段关系与进行中累计，跨日旧任务实例失效已明确；只保留实际时区、断流口径、重入履历与重复关注计数。'),
'E29':('关闭','当前公会首页、主播列表／详情／场次、日收益均加入门票；礼物明细明确只统计礼物并解释门票属于本场总收益，原范围歧义关闭。')}
DS={
'C01':('关闭','用户端涨粉／直播数据与公会端新增粉丝现均为新增关注人数减取关人数，允许负数，原净增／毛增差异消失。'),
'C22':('变化','粉丝群新增“主播是群主、不展示灯牌”说明，全员禁言亦明确群主例外；但仅有效团籍可查看／逐次发送仍未明确群主准入例外，收窄为权限条件引用不足。'),
'C25':('变化','后台已标注金币收益是用户实际消费、不是主播收益，毛额／净额可用于不同目的；不判算错，保留跨端字段命名及对账映射待确认。'),
'C26':('关闭','总收益和主播收益明确含门票；礼物明细明确仅礼物，说明其与本场总收益不同，旧的下钻范围冲突关闭。'),
'C27':('变化','净增量排除退款有明确公式，并不自动代表余额净变化；仅保留报表用途／对账调整项待确认，不认定该公式错误。'),
'C40':('变化','用户需求清单已有不足1金币舍去，不能称所有来源没有精度；与当前收益批注的逐笔／汇总、保存／显示精度和等级计值仍未衔接。')}
Q={
'Q01':('仍成立','需求清单先入会再认证与三端合并申请、初审后终审的路径仍未同步；跨端一致不等于范围已获批准。'),
'Q02':('仍成立','当前财务批注为线下核算上传、无线上申请审批；项目说明与需求清单仍保留线上提现。实际付款是否入账、责任和账户用途待决定。'),
'Q03':('仍成立','当前退款仅扣用户到账金币，消费／主播收益／分成保留；旧清单与项目说明红冲冻结描述未同步，资金责任不自定。'),
'Q04':('仍成立','开播仍要求公会有效，停用公会又声明主播不受影响；需区分公会启用状态和有效在会关系。'),
'Q05':('仍成立','送出价值×比例与旧需求清单实际消耗×1%仍有收益基数差异；舍去不足1金币只见清单，逐笔／汇总精度亦未对齐。'),
'Q06':('仍成立','单笔内含独立开奖次数、赠送数量×1／×10／×100与长期返还比例仍未清楚映射，不能机械推定同一档。'),
'Q07':('变化','重复批次、跨文件来源明细防重和金额修正叠加已定义；自动SKU分账与线下导入范围差异、实际付款、同ID多行和跨履历归属仍待确认。'),
'Q08':('关闭','初审／终审待审核入会单均因公会停用失效；保留原因时间、恢复不续旧单、可向其他启用公会重新申请，旧缺口关闭。'),
'Q09':('变化','冷静期退款、删除后的独立账本与负余额保留已有定义；负余额申请资格、主播在播／公会关系／待审核申请最终如何终结仍待确认。'),
'Q10':('变化','平台业务日、跨日旧任务失效、配置次日生效和领取／关闭先成功规则已明确；实际时区、断流重连终止和同日重启实例仍未补齐。'),
'Q11':('关闭','结束后的举报仍可处理、强制关播不可选已统一；不再引用旧的自动作废规则。'),
'Q12':('仍成立','封禁、解封已有会话及开播权限规则；申诉、没收、关系冻结恢复仅在旧清单，需先确定本期范围。'),
'Q13':('变化','当前批注已明确从未为好友时每方向3条，申请中／删除后／拉黑均禁发；清单主播不限及用户须好友的例外仍冲突。'),
'Q14':('变化','当前安装链接首次归因、注册成功发10金币且无后台配置已明确；返利、手调邀请码和后台可配奖励的旧清单范围仍待决定。'),
'Q15':('仍成立','三端均为公会创建与发币、平台管额度权限；旧后台清单平台发币与分配职责尚未同步。'),
'Q16':('仍成立','概要四语USD与旧需求的印尼盾示例等仍需同步；项目说明引用多个当前不存在的context文档，保留缺失引用。')}
# 为变化／关闭项补充当前反证，未变项保留可核实的现行引用。
SUP={
'D01':[('user','user-home.html','送出为')], 'D02':[('user','invite-friends.html','受邀新用户')], 'D07':[('user','welfare-center.html','复制链接成功')],
'D08':[('user','all-tasks.html','任意')], 'D13':[('user','recharge.html','有效期')], 'D16':[('admin','admin-push-detail.html','公会主播')],
'D17':[('admin','admin-push-management.html','服务端成功接受')], 'D20':[('admin','admin-guild-detail.html','其他可管理')],
'D22':[('user','live-records.html','实际开始')], 'D27':[('user','group-manage-member.html','免打扰只关闭')],
'R02':[('user','live-data.html','最近一段')], 'R03':[], 'D29':[('user','host-center.html','暂停')], 'D31':[('user','host-center.html','涨粉'),('guild','guild-host-summary.html','新增粉丝')],
'C03':[('user','views/live-room/gift.html','两条流水')],
'E01':[('user','settings.html','只绑定当前账号')], 'E03':[], 'E06':[('admin','admin-host-review-detail.html','初审和平台终审')],
'E13':[('admin','admin-recharge-order-detail.html','内部扣币')], 'E14':[('user','views/live-room/gift.html','两条流水')],
'E15':[('user','views/live-room/gift.html','未完成步骤')], 'E18':[('admin','admin-settlement-record.html','批次编号')],
'E20':[('user','guild-detail.html','系统通知')], 'E21':[('user','live-room-report.html','仍可处理'),('admin','admin-report-handling.html','结束后')],
'E23':[('user','blacklist-management.html','好友关系保留')], 'E26':[('user','invite-friends.html','受邀新用户')],
'E27':[('user','welfare-center.html','复制链接成功')], 'E28':[('user','views/live-data/month.html','最近一段')],
'E29':[('guild','guild-home.html','门票'),('guild','guild-live-gift-detail.html','本页礼物收益')],
'DS-C01':[('user','host-center.html','涨粉'),('guild','guild-host-summary.html','新增粉丝')],
'DS-C22':[('user','fan-group-chat.html','主播是群主'),('user','fan-group-chat.html','仅有效')],
'DS-C25':[('admin','admin-live-detail.html','用户实际消费')], 'DS-C26':[('guild','guild-live-gift-detail.html','本页礼物收益')],
'DS-C27':[('admin','admin-recharge-statistics.html','净增量')],
'Q08':[('admin','admin-host-review-detail.html','初审和平台终审')], 'Q11':[('user','live-room-report.html','仍可处理')],
'Q10':[('admin','admin-task-detail.html','次日 00:00')], 'Q13':[('user','direct-message.html','各自最多')], 'Q14':[('user','invite-friends.html','暂无后台')],
'Q09':[('user','settings.html','独立保留交易账本')], 'Q07':[('admin','admin-settlement-record.html','批次编号')]}
def add(ns,obj,decisions):
 oid=obj['id'];lid=('DS-'+oid) if ns=='DS' else oid;status,reason=decisions.get(oid,('仍成立',obj.get('remaining',obj.get('gap','具体条件在现行来源中仍未完整定义；保留待确认。'))))
 refs=old_refs(obj)+[entry_ev(*args) for args in SUP.get(lid,[])]
 dedup={(x['path'],x['line'],x['quote']):x for x in refs}
 row=dict(id=lid,namespace=ns,legacyId=oid,title=obj.get('title',obj.get('term',oid)),status=status,change='关闭' if status=='关闭' else '分类修正' if status=='排除' else '变化' if status=='变化' else '保留',conclusion=reason,remaining='' if status in ['关闭','排除'] else reason,evidence=list(dedup.values()),historicalRecord=obj,historicalArchive=str(ARCH),verification='完整批注及相关文档静态核对；不等于后端／线上验证',requirementsApproved=False)
 ledger.append(row);return row
for ns,f,ds in [('TERM','08-批注术语定义缺口.json',D),('E2E','09-端到端完整性审查.json',E),('DS','深层分支审查-2026-10-15/审查记录.json',DS)]:
 for obj in read(ARCH/f)['issues']:add(ns,obj,ds)
# Q历史原文逐项保留；源位置重新读取，不沿用旧行号。
qtext=(ARCH/'02-冲突与待确认.md').read_text()
for match in re.finditer(r'^## (Q\d+) (.+)\n([\s\S]*?)(?=^## |\Z)',qtext,re.M):
 oid,title,body=match.groups();obj=dict(id=oid,title=title,historicalText=body,evidence=[])
 for m in re.finditer(r'\]\(<?(/Users/[^)>]+?)(?::(\d+))?>?\)',body):
  p=Path(m[1]);n=int(m[2] or 1)
  if p.is_file():
   # Locate by an unchanged historical line, not by an old line number in current file.
   op=ARCH/'来源快照.json';priorlines=None
   prot=ARCH/'原型保护清单.json'
   # Old raw context is not copied; use the known current entry/document selectors below.
 qmap={'Q01':[('user','guild-application-form.html')],'Q02':[('admin','admin-settlement-record.html')],'Q03':[('admin','admin-refund-order.html')],'Q04':[('admin','admin-guild-detail.html'),('user','start-live-settings.html')],'Q05':[('admin','admin-lucky-gift-config.html')],'Q06':[('admin','admin-lucky-gift-detail.html')],'Q07':[('admin','admin-settlement-record.html')],'Q09':[('user','settings.html')],'Q12':[('admin','admin-user-list.html')],'Q15':[('admin','admin-operation-accounts.html')]}
 row=add('Q',obj,Q);row['evidence'] +=[entry_ev(*a) for a in qmap.get(oid,[])]
# 15项旧页面差异，重新依据当前格式要求与共享脚本判断；旧运行数字只放历史。
AP=read(ARCH/'07-审查页面来源.json')['pages']
ATITLES=re.findall(r'^## (A\d+) (.+)$',(ARCH/'07-批注与页面不一致审查.md').read_text(),re.M)
AD={
'A01':('仍成立','当前RTP计算用单价=单次消耗×开奖次数作分母，但批注公式分母为单次消耗；次数>1时静态公式不符。'),
'A02':('关闭','当前消费订单详情批注只要求消费类型、数量、消费金币及主播信息；旧报告要求返奖、净消耗、主播收益、公会等全部字段没有同页现行依据，撤销原“缺字段”结论。报表字段要求另按报表核对。'),
'A03':('关闭','共享operation-accounts.js已不含幸运礼物，原Bima相关示例改为普通／定制礼物，旧非法示例不成立。'),
'A04':('关闭','公会与后台复用的运营送礼数据已只含普通／定制礼物，关闭旧示例不符项。'),
'A05':('仍成立','设置密码仍仅按验证码长度6及密码至少8位启用按钮，缺数字、上限和至少两类字符的本地校验。'),
'A06':('仍成立','修改密码仍以最少8位及一致性校验为主，缺当前批注规定的8—20位和两类字符校验。'),
'A07':('仍成立','重置密码仍只按验证码长度和至少8位校验；验证码数字与密码复杂度／上限未落地。'),
'A08':('仍成立','粉丝团贡献阈值只校验Number>=0，未校验非负整数；输入step=1未被按钮保存逻辑采用。'),
'A09':('仍成立','生日input无max，提交直接写入生日；当前不得晚于今日规则未在本地校验。'),
'A10':('仍成立','公会直播记录开播人数仍固定20，未按所选主播和日期去重；这是已知待补齐。'),
'A11':('关闭','现行新增粉丝已定义为净增且允许负数，Mock负数不再违反当前要求；旧“不能为负”的审查结论撤销。'),
'A12':('仍成立','主播业绩列表仍直接用item.income，getGuildDay对无数据日期有回退，筛选收益未完整联动；旧示例日期／金额不当成本轮运行结果。'),
'A13':('仍成立','公会业绩跨日startedHosts仍逐日求和，跨月也累加，不能证明按主播ID去重；保留已知实现差异。'),
'A14':('仍成立','退会通过按钮仍直接handleReview(approved)，没有通过前二次确认；制作规范允许后台Toast不免除已明确的同页确认。'),
'A15':('仍成立','公会主播主页粉丝数取getSummary().fans，该函数加总各日净增，不能代表当前仍关注总人数。')}
for oid,title in ATITLES:
 p=next(x for x in AP if x['id']==oid);obj=dict(id=oid,title=title,evidence=[])
 row=add('PAGE',obj,AD);file=Path(p['page']);e=next(e for e in S['entries'] if str(file) in e['pages'] and not e['view'])
 row['evidence']=[entry_ev(e['end'],e['key'])];row['page']=p['url'];row['pagePath']=str(file);row['verification']='当前HTML与共享脚本静态分析；本轮未重现旧报告的运行数值'
# 代码证据定位为实际现行行。
CODE={'A01':('prototype/pages/admin/gifts/admin-lucky-gift-detail.html','const cost = unitPrice(config)'), 'A02':('prototype/pages/admin/orders/admin-consumption-order-detail.html','消费金币'), 'A03':('prototype/assets/operation-accounts.js',"id: 'OG26082401'"),'A04':('prototype/assets/operation-accounts.js',"id: 'OG26082401'"),'A05':('prototype/pages/user/profile/account-password-set.html','function sync()'),'A06':('prototype/pages/user/profile/account-password-change.html','function sync()'),'A07':('prototype/pages/user/profile/account-password-reset.html','function sync()'),'A08':('prototype/pages/user/host/fan-club-settings.html','Number(contribution.value) >= 0'),'A09':('prototype/pages/user/profile/profile-edit.html','profileMock.birthday = birthday.value'),'A10':('prototype/pages/guild/data/guild-host-data.html','metric("开播人数", "20")'),'A11':('prototype/assets/guild-data-model.js','fans: started ?'),'A12':('prototype/pages/guild/people/guild-host-list.html','item.income'),'A13':('prototype/pages/guild/data/guild-income.html','startedHosts: selectedDays.reduce'),'A14':('prototype/pages/guild/approval/guild-leave-review-detail.html','handleReview("approved")'),'A15':('prototype/pages/guild/people/guild-host-detail.html','LUMA_FORMAT.integer(totals.fans)')}
for row in ledger:
 if row['namespace']=='PAGE':row['evidence'].append(ev(*CODE[row['id']]))
 if row['id']=='E03':row['evidence'].append(ev('prototype/annotations/guild.js','@op.test'))
 if row['id']=='DS-C40':row['evidence'].append(ev('context/01-用户主播App-项目需求清单.md','主播收益不足 1'))
 if row['id']=='R03':row['evidence'].append(ev('context/01-用户主播App-项目需求清单.md','其余等级权益'))
 if row['id']=='Q16':row['evidence'] +=[ev('项目说明.md','01-业务对象清单.md'),ev('context/系统概要 .md','统一使用美元')]
# 新问题不复用旧编号；与已有主题建立关联，避免当成独立缺陷重复计数。
NEW=[
('N20261016-01','主页私信未带当前对象标识','静态实现差异','user-home与host-home的私信跳转未带peer；单聊缺省选sari，非Sari对象可能错会话。',[entry_ev('user','direct-message.html','所选联系人'),ev('prototype/pages/user/social/user-home.html','location.href = "direct-message.html"'),ev('prototype/pages/user/social/host-home.html','location.href = "direct-message.html"'),ev('prototype/pages/user/social/direct-message.html','get("peer") || "sari"')],['L21']),
('N20261016-02','图片语音绕过非好友三条额度','静态实现差异','文字与表情检查sentCount，chat-media的图片、语音仅调用canSend，而canSend只看关系不看条数，且媒体不增加sentCount。当前演示不符合所有消息合计额度，真实IM未验证。',[entry_ev('user','direct-message.html','图片和语音'),ev('prototype/pages/user/social/direct-message.html','function canSend()'),ev('prototype/assets/chat-media.js','canSendDirectMessage')],['L21']),
('N20261016-03','互动通知的被送礼范围未同步','范围冲突','用户需求清单包含被送礼，通知规则和互动通知批注只列关注、申请及结果；先确认本期是否还需要赠礼互动通知，不直接断言缺功能。',[ev('context/01-用户主播App-项目需求清单.md','被送礼'),entry_ev('user','interaction-notifications.html','数据范围')],['L21','L11']),
('N20261016-04','回复即好友的演示文案与申请流程不一致','示例文案差异','Mock会话“回复消息我们就是好友啦”与申请同意才建好友的当前规则不符；消息中心已实际观察到该文案。',[ev('prototype/assets/mock.js','回复消息我们就是好友啦'),entry_ev('user','friend-list.html','接受好友申请')],['L21']),
('N20261016-05','修改与重置密码成功后的去向不符','静态实现差异','当前批注规定修改或重置成功后原会话失效并返回登录页；两个页面成功分支均go(settings.html)，演示未按规则返回登录。设置密码成功回设置页本身不列问题。',[entry_ev('user','account-password-change.html','返回登录页'),entry_ev('user','account-password-reset.html','返回登录页'),ev('prototype/pages/user/profile/account-password-change.html',"go('settings.html')"),ev('prototype/pages/user/profile/account-password-reset.html',"go('settings.html')")],['L02']),
]
for oid,title,typ,reason,refs,chains in NEW:ledger.append(dict(id=oid,namespace='NEW',legacyId=None,title=title,type=typ,status='新增：需求待确认' if typ=='范围冲突' else '新增：静态差异',change='新增',conclusion=reason,remaining=reason,evidence=refs,chains=chains,requirementsApproved=False,verification='当前源文件核对；04另在消息中心观察到示例文案'))
# 增补旧总账没有的范围候选，不让它们从重建中丢失。
oldfull=read(ARCH/'全量场景/场景数据.json')
for item in oldfull['extraPending']:
 obj=dict(id=item['id'],title=item['title'],gap=item['question'],evidence=[])
 refs=[]
 oldev={x['id']:x for x in oldfull['evidence']}
 for eid in item.get('evidence',[]):
  o=oldev[eid];refs+=old_refs(dict(evidence=[dict(path=o['file'],quote=o['quote'])]))
 row=add('SCOPE',obj,{})
 row['evidence']=refs;row['conclusion']=item['question'];row['remaining']=item['question']
# 确认范围补充；旧SCOPE-07已改为“精度有清单规则但未衔接”。
for row in ledger:
 if row['id']=='SCOPE-07':row.update(status='变化',change='变化',conclusion='收益基数仍为净消耗与送出价值两种；需求清单已有不足1金币舍去，当前批注未说明逐笔／汇总及等级使用精度。',remaining='统一基数与舍入范围，不再称全部来源均缺精度。')
 # 缺少旧完整引文时补相关原型条目，仅作为检索范围，绝不以邻近句证明缺口。
 if not row['evidence']:
  hist=row.get('historicalRecord',{});occ=hist.get('occurrences',[])
  for o in occ:
   if (o.get('end'),o.get('key')) in EN:row['evidence'].append(entry_ev(o['end'],o['key']))
  if not row['evidence'] and row['namespace']=='SCOPE':
   row['evidence']=[entry_ev('user','start-live-settings.html')] if row['id'].startswith('FULL-P') else [ev('context/社交关系规则补充.md','拉黑')]
  row['evidenceBoundary']='关联入口／检索范围证据，不单独证明缺少定义。旧原文见归档。'
 assert row['evidence'],row['id']
# 对已变化段落的旧引用只保留在historicalRecord，现行evidence均真实命中。
for row in ledger:
 for e in row['evidence']:
  line=(ROOT/e['path']).read_text().splitlines()[e['line']-1];q=e['quote']
  assert q in line or json.dumps(q,ensure_ascii=False)[1:-1] in line or q.replace("'","\\'") in line,(row['id'],e)
assert len({(x['namespace'],x['id']) for x in ledger})==len(ledger)
write(R/'本轮问题复核.json',dict(date=DATE,archive=str(ARCH),prototypeRoot=str(P),prototypeHead=subprocess.check_output(['git','-C',str(P),'rev-parse','HEAD'],text=True).strip(),status='全部旧记录重新核对；候选含重叠，不是去重缺陷数',issues=ledger,counts=dict(collections.Counter(x['change'] for x in ledger)),runtime='仅消息中心→公会通知→返回未读变化已操作；其他场景未执行'))
print('ledger',len(ledger),dict(collections.Counter(x['change'] for x in ledger)))
# 逐对象库：仅一条业务原文变化，门票贡献纳入粉丝团加入校验；其余93条逐条复核。
obj=read(ARCH/'13-操作影响逐对象数据.json');obj['date']=DATE;obj['archive']=str(ARCH);obj['sources']=S['sources'];obj['previousStats']=obj['stats']
obj['rebuildBoundary']='本轮按当前三端批注与6份context重核八类操作。保留原31个单项、120个并发候选及逐对象行ID；未知并发结果不由单项相加推导。全业务扩展见全量场景目录。'
for x in obj['evidences']:
 if x['id']=='E021':
  oldq=x['quote'];x['quote']=next(q for sec in EN['user','fan-club-settings.html']['sections'] for q in sec['d'] if '仅粉丝团所属主播' in q);x['previousQuote']=oldq
 q=x['quote'];probes=[q,json.dumps(q,ensure_ascii=False)[1:-1],q.replace("'","\\'")];lines=Path(x['file']).read_text().splitlines();x['line']=next(n for n,l in enumerate(lines,1) if any(v in l for v in probes))
for c in obj['conflicts']:
 p=Path(c['file']);c['line']=next(n for n,l in enumerate(p.read_text().splitlines(),1) if c['quote'] in l)
# 涉及入团门槛的旧行，结果需要与新原文保持一致，编号不变。
changed_rows=[]
for scene in obj['operations']+obj['concurrent']:
 for row in scene['rows']:
  if 'E021' in row['evidence'] and '送礼贡献' in row['result']:
   row['result']=row['result'].replace('送礼贡献','送礼和购票贡献');scene['effects'][row['object']]['result']=row['result'];changed_rows.append(row['id'])
obj['revision']=dict(date=DATE,changedEvidence=['E021'],changedRows=changed_rows,sourceChange='加入校验的历史贡献现含成功送礼和购票',runtime='未执行')
write(R/'13-操作影响逐对象数据.json',obj)
# 深层审查保留原目录地址与编号，但内容是本轮重核；日期以generatedAt标识，旧版在归档。
h=read(ARCH/'深层分支审查-2026-10-15/审查记录.json');lm={x['id']:x for x in ledger};h['generatedAt']=DATE;h['archive']=str(ARCH);h['scope']=[str(p) for p in sorted((P/'context').glob('*.md'))]+[str(P/f'prototype/annotations/{e}.js') for e in ['user','guild','admin']];h['read_entries']=S['entries']
for issue in h['issues']:
 row=lm['DS-'+issue['id']];issue['previousStatus']=issue['status'];issue.update(status='已关闭：当前依据已消除旧问题' if row['status']=='关闭' else '需求待确认',remaining=row['remaining'],counter_evidence=row['conclusion'],evidence=row['evidence'],reviewStatus=row['status'],verification=row['verification'])
for c in h['chains']:
 c['evidence']=[entry_ev(next(e['end'] for e in S['entries'] if e['key']==key),key) for key in c['keys']]
 for b in c['branches']:
  b['reviewedAt']=DATE
  if b['id']=='L22-B05':b.update(scenario='主播和公会周期净增粉丝',status='已明确',result='两端均为新增关注人数减取关人数，可为负；旧毛增差异已关闭，重复关注计数另见D31。')
  if b['id']=='L22-B06':b.update(status='已明确',result='公会总收益含礼物和门票；礼物明细仅礼物，门票属于本场总收益，范围已区分。')
  if b['id']=='L16-B08':b.update(status='缺少定义',result='主播群主身份和不展示灯牌已明确；仅有效团籍准入及每次发送校验仍需明确群主例外。')
  if 'C40' in b['issues']:b['result']+='；清单已有不足1金币舍去，逐笔或汇总、原始保存和计级仍未对齐。'
  b['issueDispositions']={i:lm['DS-'+i]['status'] for i in b['issues']}
h['counts']['branch_status']=dict(collections.Counter(b['status'] for c in h['chains'] for b in c['branches']));h['counts']['issueDisposition']=dict(collections.Counter(i['reviewStatus'] for i in h['issues']))
write(R/'深层分支审查-2026-10-15/审查记录.json',h)
# 将人工判断绑定到本轮具体来源哈希，后续变化必须再复核，不能只换日期重跑。
write(R/'本轮语义复核来源.json',dict(date=DATE,sources=S['sources'],issuesReviewed=len(ledger),changeLog='本轮问题复核.json',approvedRequirements=False,semanticAuditPassed=False))
