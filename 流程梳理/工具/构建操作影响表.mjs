import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';

const root = path.resolve(import.meta.dirname, '../..');
const out = path.join(root, '流程梳理');
const snapshot = JSON.parse(fs.readFileSync(path.join(out, '来源快照.json'), 'utf8'));
// 这份操作归纳必须随业务变化人工复核，不能靠重新提取原文自动认证。
const reviewed = JSON.parse(fs.readFileSync(path.join(out,'本轮语义复核来源.json'),'utf8'));
assert.equal(snapshot.date,reviewed.date,'本轮语义复核日期不匹配');
for (const source of reviewed.sources) assert.equal(crypto.createHash('sha256').update(fs.readFileSync(source.path)).digest('hex'),source.sha256,'人工复核后来源变化：'+source.path);
const lookup = new Map(snapshot.entries.map(e => [e.end + '/' + e.key, e]));
const sources = {
  U:'user/user-home.html', F:'user/views/user-home/friend.html', B:'user/blacklist-management.html',
  I:'user/interaction-notifications.html', FL:'user/friend-list.html', FC:'user/my-fan-clubs.html',
  CM:'user/fan-club.html', CS:'user/fan-club-settings.html', GC:'user/fan-group-chat.html',
  GO:'user/group-manage-owner.html', GM:'user/group-manage-member.html',
  MOD:'user/moderator-management.html', HP:'user/views/live-room-host/profile-host.html',
  MU:'user/views/live-room-host/muted-users.html', R:'user/views/live-room-host/restore-speaking-confirm.html',
  K:'user/views/live-room/profile-moderator-remove.html', MV:'user/views/live-room/profile-moderator-mute.html',
  AV:'user/views/live-room-host/audience-viewers.html', END:'user/views/live-room-host/end-confirm.html',
  CO:'user/live-room-cohost-active.html', CE:'user/views/live-room-cohost-active/cohost-exit-confirm.html',
  AP:'user/guild-application-form.html', LE:'user/guild-leave-application.html', HIST:'user/guild-application-records.html',
  JR:'guild/guild-join-review.html', JD:'guild/guild-join-review-detail.html', LR:'guild/guild-leave-review.html',
  LD:'guild/guild-leave-review-detail.html', HD:'guild/guild-host-detail.html',
  UA:'admin/admin-user-list.html', UD:'admin/admin-user-detail.html', HL:'admin/admin-host-list.html',
  HR:'admin/admin-host-review-detail.html', GD:'admin/admin-guild-detail.html', GR:'admin/admin-guild-recommendation.html',
  OA:'admin/admin-operation-account-detail.html', OAC:'admin/admin-operation-guild-controls.html',
  AC:'admin/admin-system-account.html', ROLE:'admin/admin-system-role.html',
  SYS:'user/system-notifications.html', LIVE:'user/live-notifications.html', CHAT:'user/direct-message.html',
  SET:'user/chat-settings.html', HF:'user/host-center.html', GS:'guild/guild-host-summary.html',
  CR:'user/views/live-room-host/contribution-rank.html'
};
for (const [id,key] of Object.entries(sources)) assert(lookup.has(key), `来源缺失 ${id} ${key}`);
const singles = [];
const add = (id,operation,relations,permissions,history,notifications,refs) => singles.push({id,operation,relations,permissions,history,notifications,refs:refs.split(' ')});
add('A01','关注','建立单向关注；同步关系状态和计数','','','被关注者收到互动通知','U I');
add('A02','取消关注','解除单向关注；好友、团籍独立保留','若为该主播房管，身份自动解除','历史开播提醒保留；主播中心周期净增扣除取关','后续不再接收该主播开播提醒','U MOD LIVE HF');
add('A03','申请好友','建立待处理申请；已有待处理时不重复生成','申请处理中双方不可私信','','接收方收到申请通知','I F');
add('A04','同意好友申请','建立双向好友；双方进入好友列表','建立后可持续私信','接收方原申请记录更新已同意','申请人收到同意结果，可进入单聊','I FL F');
add('A05','拒绝好友申请','不建立好友关系','','原申请记录更新已拒绝','申请人收到拒绝结果','I');
add('A06','删除好友','解除双向好友；不自动取消关注','生效后双方不能发私信','删除方清空会话及历史；被删除方保留','', 'F FL');
add('A07','拉黑','双向解除关注、对方团籍／群籍、房管授权；待处理好友申请失效；好友保留','双向禁关注、申请好友、私信、进入对方直播间；仍可搜索／查看公开主页；主播拉黑房内用户立即退房；平台管理员豁免普通黑名单准入','单聊历史仍可查看；黑名单仅列本人主动拉黑记录','失效申请：申请人收结果，接收方原记录更新，不另通知','B F I');
add('A08','取消拉黑','只解除本方向记录；已解除关注、团籍、申请、房管不自动恢复','全部拉黑解除后，保留好友立即恢复私信','从主动黑名单移除','', 'B');
add('A09','加入粉丝团','团籍与群籍同步；须满足最新加入条件、人数上限','有效团籍才能查看／发送群消息','按本次入团时间排序；重入不恢复旧会话和未读；历史贡献保留','','CS FC GC CM');
add('A10','主动退出粉丝团','解除团籍与群籍；不影响关注','失去群聊权限；群历史不再开放','粉丝等级、亲密度清零；历史贡献保留；团榜不再展示本人','','FC GC GM');
add('A11','主播移除粉丝团成员','团籍、群籍同步解除；不影响关注；更新成员数','失去群聊权限','粉丝等级、亲密度清零；历史贡献保留','','CM FC GC');
add('A12','群单人禁言','','限制该成员在该粉丝群发言；账号＋群绑定，退团重入仍有效','','','CM GC');
add('A13','解除群单人禁言','','批注提到主播解除单人禁言；与全员禁言的叠加结果为跨页归纳，独立解除流程未完整说明','','','CM GC GO');
add('A14','开启群全员禁言','','当前群除群主外所有成员不能发言','','','GO');
add('A15','关闭群全员禁言','','恢复群发言；单人禁言仍有效','','','GO');
add('A16','设置房管','建立长期房管授权；当前关注、无拉黑、未被踢出；最多3人','获得禁言、踢出、屏蔽评论权限','更新资料卡／名单／人数','','MOD HP');
add('A17','取消房管','立即撤销房管授权','处置时重验当前权限；撤权先生效拒绝；仍可作为普通观众留房','已成功的处置保留；更新名单／人数','','MOD AV');
add('A18','直播间禁言','','只限制当前场次公屏发言；不影响观看、赠礼、私信','更新输入框、资料卡、禁言列表','','MV MU');
add('A19','恢复直播间发言','','解除本场禁言并恢复公屏输入','移出禁言名单；已恢复／场次结束不重复执行','','R MU');
add('A20','踢出直播间','','立即退房，本场不可重进；下场可重新准入','在线名单移除；历史贡献保留；门票失效不退款','','K AV CR');
add('A21','结束直播','连麦、待处理邀请失效','本场门票、禁言／踢出失效；房管长期授权保留','历史消息、消费、处置和收益保留；另一主播直播继续','','END CO MOD');
add('A22','退出连麦','只解除连麦关系','双方各自直播继续','本场贡献、消息、观众数据继续累计','','CE');
add('A23','提交入会认证','生成处理中申请，先公会初审；只允许一笔处理中申请','','申请历史可查询','','AP HIST');
add('A24','公会通过入会申请','原申请自动进入平台审核；尚未完成入会／认证','','旧单审核结果保留','','AP JD');
add('A25','公会／平台驳回入会申请','本次申请结束，不获得本次入会结果','','旧单保留；重新申请新单不继承旧审核','用户系统通知含驳回结果','AP JD SYS');
add('A26','平台通过入会认证','加入申请公会并获得主播身份','开播仍需符合账号、公会、平台与公会权限条件','','通知获得主播身份，指向公会详情','HR SYS');
add('A27','提交退会申请','生成处理中退会申请；不等于已经退会；只允许一笔处理中','','','', 'LE');
add('A28','退会申请通过','解除公会关系及主播身份；创建的粉丝团解散，所有成员团籍／群籍解除','立即结束当前直播；群聊权限解除','成员粉丝等级、亲密度清零；历史申请保留','用户收到退会通过系统通知','LE LD HIST SYS');
add('A29','退会申请驳回','保留公会关系、主播身份；可重新申请','','旧申请保留','用户收到驳回系统通知','LE LD HIST SYS');
add('A30','公会移除主播','解除公会关系及主播身份；解散其粉丝团；待审退会申请失效','立即结束当前直播','申请记录保留；记录失效原因和时间；成员粉丝等级／亲密度清零','用户收到被移除系统通知','LE HD HIST SYS');
add('A31','封禁用户','','立即下线、在播时关播、禁止登录；旧会话和尚未成功的操作拒绝','已成功操作保留；填写原因留痕','','UA');
add('A32','解封用户','','只恢复登录，不自动恢复直播权限','填写原因并留痕；与封禁按服务端成功顺序生效','','UA UD');
add('A33','平台关闭直播权限','','立即关播、禁止开播；公会管理权限同步关闭且不可开启','前后值、操作人、时间留痕','','HL');
add('A34','平台开启直播权限','','允许后续开播仍须满足其他条件；公会管理权限需单独开启；不自动重建场次','前后值、操作人、时间留痕','','HL');
add('A35','锁定公会直播管理权限','','公会开关只读，设置跟随平台；最终关闭时立即关播','保留锁定前公会设置','','HL HD');
add('A36','解锁公会直播管理权限','','恢复锁定前设置并重算；最终关闭则关播；恢复开启不自动新建场次','','','HL HD');
add('A37','公会关闭主播直播权限','','立即关播、禁止再次开播；锁定时不可改','','','HD');
add('A38','停用公会','用户端隐藏且不可搜索；初审／终审待审入会单失效；退会待审保留','撤销管理账号对此公会管理权；当前选中此公会的会话退出；有其他可管理公会可登录；主播和运营账号不受影响','旧单只读；记录失效原因／时间；推荐移除','','GD JR LR GR');
add('A39','启用公会','不恢复旧失效入会单；不自动恢复推荐','账号仍按自身最新状态判断；退会待审可由有权限公会长继续处理','历史记录保留','','GD JR LR GR');
add('A40','停用公会长账号','','当前会话失效；新操作拒绝；已受理请求继续；不等于停用公会','原入会／退会待审保留，待有权限账号处理','','GD JR LR');
add('A41','重置公会长密码','','密码立即生效，旧会话失效；变更前已受理请求继续，新操作拒绝','','','GD');
add('A42','平台停用运营账号','','旧会话失效、不可送礼；公会不可改账号启停','不影响有权限且未停用公会发放虚拟币','','OA');
add('A43','平台关闭运营账号公会管理权限','','只限制公会修改运营账号状态；不影响有权限且未停用公会发币','','','OA');
add('A44','停用后台账号／重置密码','','会话立即失效返回登录；旧页面不得发新操作；变更前提交请求继续','内置超级管理员账号不可停用','','AC');
add('A45','停用后台角色／撤销角色权限','','按当前所有有效角色重算权限；高权限处置执行时重验，撤权后拒绝','内置超级管理员角色不可修改或停用','','ROLE');

const combinations = [];
const combo = (id,operation,result,refs,status='当前批注有说明') => combinations.push({id,operation,result,refs:refs ? refs.split(' ') : [],status});
combo('M01','好友 → 取消关注','关注和好友分别维护；不因取关自动解除好友。','U F');
combo('M02','粉丝团成员 → 取消关注','不退出粉丝团。','U FC');
combo('M03','房管 → 取消关注主播','房管身份立即解除。','MOD');
combo('M04','取关撤房管 → 重新关注','不自动恢复房管，主播须重新添加。','MOD');
combo('M05','房管 → 任一方拉黑','房管身份自动解除；好友关系仍保留。','MOD B');
combo('M06','拉黑撤房管 → 取消拉黑','不自动恢复房管。','MOD B');
combo('M07','好友申请待处理 → 任一方拉黑','申请失效；申请人收到结果，被申请人原记录改状态且不另发通知，文案不透露拉黑方。','I');
combo('M08','好友 → 拉黑 → 解除全部拉黑','好友保留、期间禁发私信；全部解除后立即恢复发送。关注、团籍、房管、旧申请不自动恢复。','F B');
combo('M09','双方各自拉黑 → 一方取消','另一方向记录仍存在，双向限制继续。','B');
combo('M10','删除好友 → 再次申请待处理','双方仍不可发送私信。','F');
combo('M11','删除好友 → 重新成为好友','双方恢复发送；删除方原历史不恢复，被删除方历史保留。','F');
combo('M12','删除好友与发送同时发生','服务端顺序决定；删除生效后的发送拒绝。','F');
combo('M13','重新成为好友 → 再次删除','按本次删除方／被删除方分别处理会话和历史。','F');
combo('M14','退团／被移除 → 重新入团','等级／亲密度从0开始；历史贡献继续计入总贡献及对应周期榜；旧会话、未读不恢复；群单人禁言仍有效。','FC GC CM');
combo('M15','已有团籍 → 主播提高入团条件','不移除已有成员；新加入校验最新条件。','CS');
combo('M16','群单人禁言 ＋ 全员禁言 → 关闭全员禁言','单人禁言仍生效。','GO');
combo('M17','本场禁言 → 离房 → 本场重进','离房不自动解除禁言，重进继续生效。','MU');
combo('M18','本场禁言 → 恢复发言','解除本场禁言，移出名单并恢复公屏输入。','R');
combo('M19','本场禁言 → 结束场次 → 下一场','旧禁言失效，下一场默认恢复。','MU END');
combo('M20','购票 → 被踢出','门票失效且不退款，本场不能重进。','K');
combo('M21','购票／密码校验通过 → 拉黑或本场踢出','拉黑、封禁、本场踢出优先于房间准入，不能靠已购票或密码通过绕过。','B K', '跨页归纳；准入优先级另见系统概要');
combo('M22','本场被踢出 → 下一场','旧踢出限制失效，可重新按新场次准入条件进入。','K END');
combo('M23','被本场踢出 → 设置为房管','不可新增该用户为房管。','HP');
combo('M24','房管 → 场次结束','房管授权长期保留，结束场次不清除。','MOD');
combo('M25','公会／平台驳回 → 再次申请入会','新申请重新从公会初审开始，旧审核不继承。','AP JD');
combo('M26','入会初审／终审待审 → 公会停用','均失效，原因和时间留存，不可继续旧单。','JR HR');
combo('M27','公会停用导致入会单失效 → 启用公会','不恢复旧申请；用户可另交新单。','JR HR');
combo('M28','退会待审 → 公会移除主播','退会单失效，原因“主播已被公会移除”；历史申请保留。','HD LE');
combo('M29','退会驳回 → 再次申请退会','原公会和主播身份保留，可提交新退会申请。','LE LD');
combo('M30','正在直播 → 退会通过／移除主播','立即关播、失去公会关系与主播身份；解散其粉丝团并解除全部成员群籍，等级／亲密度清零。','LE LD');
combo('M31','退会／移除 → 重新认证为主播','需重新创建粉丝团。','LE');
combo('M32','退出旧公会 → 加入新公会','旧关系历史保留；主播中心周期数据只展示当前公会最近一段有效关系期间，粉丝数／列表不受转会影响；公会业绩按当前公会关系有效期间统计。','HIST GS HF','跨页归纳；两端统计范围分别保留');
combo('M33','关闭直播权限 → 封禁 → 解封','解封只恢复登录，不自动恢复已关闭的直播权限。','HL UA UD');
combo('M34','平台开启 ＋ 公会关闭（未锁定）','不满足双重开播条件。','HD');
combo('M35','平台关闭 ＋ 公会原开启','关闭平台权限仍禁止开播且立即关播；公会管理权限同步关闭。','HL');
combo('M36','平台开启、公会原关闭 → 锁定公会管理权限','锁定期间公会设置跟随平台且不可改；能否开播仍受其他资格条件约束。','HL');
combo('M37','锁定期间可播 → 解锁恢复原公会关闭','重新计算最终权限，变关闭则立即关播。','HL HD');
combo('M38','封禁／关闭权限／退会导致关播 → 原连麦与邀请','当前场次结束使连麦、待处理邀请失效；对方主播直播继续。','UA HL LE END CO','跨页归纳');
const unknowns = [
 ['Q01','从未是好友 → 申请 → 拒绝：原非好友3条额度是否重置？'],
 ['Q02','双方同时向对方申请好友：是否合并申请、如何处理？'],
 ['Q03','同意好友申请与拉黑同时提交：哪个结果生效？'],
 ['Q04','同一好友申请被同时同意／拒绝：如何防止重复或冲突？'],
 ['Q05','已有单聊历史 → 拉黑 → 解除全部拉黑','历史仍可查看；原好友立即恢复发送。','F B'],
 ['Q06','群单人禁言 → 退团 → 重入','同一账号＋粉丝群的单人禁言继续生效。','CM GC'],
 ['Q07','全员禁言仍开启 → 解除单人禁言','非群主仍受全员禁言限制。','GO','跨页归纳：单人解除本身没有独立完整流程'],
 ['Q08','退团 → 重入：旧群历史、会话、未读','旧消息不恢复、旧会话与未读不恢复；重新进入为新会话、未读0。','GM GC'],
 ['Q09','房管被本场禁言：是否仍可执行房管管理动作？'],
 ['Q10','房管被本场踢出：长期房管授权是否同时撤销？'],
 ['Q11','已禁言观众 → 新设房管：原禁言是否解除？'],
 ['Q12','取消房管与房管处置同时发生','执行时重验权限；撤权先生效拒绝，已成功处置保留。','MOD'],
 ['Q13','主播退会／被移除 → 重新认证：原房管授权如何处理？'],
 ['Q14','正在连麦 → 双方拉黑：是否立即结束现有连麦？'],
 ['Q15','已在仅团员可进入的密码房 → 退团：是否立即退房？'],
 ['Q16','先禁言再踢出 → 点击恢复发言：允许处理吗、踢出是否继续？'],
 ['Q17','入会／退会待审 → 申请人封禁：审核人能否继续审核？'],
 ['Q18','退会待审 → 主播直播权限关闭：退会处理是否受限？'],
 ['Q19','退会通过与公会移除同时处理：终态、通知、重复处理如何协调？'],
 ['Q20','平台锁定公会直播管理权限 → 公会移除／审批退会：是否也受锁定限制？'],
 ['Q21','平台与公会同时变更权限：服务端顺序、最终值如何确定？'],
 ['Q22','封禁 → 解封：团籍、群籍、私信、房管分别如何恢复？'],
 ['Q23','关闭直播权限 → 恢复开启：旧场次','仅允许后续开播，不自动重建场次。','HL HD'],
 ['Q24','取消关注 ＋ 删除好友 ＋ 拉黑：不同操作顺序的通知去重和历史结果？']
];
for (const [id,operation,result='',refs='',status] of unknowns) combo(id,operation,result,refs,status || (result ? '新版已补明' : '需求待确认'));
combo('M39','入会待审 → 仅停用公会长账号','原申请不结束，等待有权限公会长接手；不得重复提交。','JR');
combo('M40','退会待审 → 停用公会／公会长账号','保留原退会申请和公会关系；恢复后有权限账号继续处理，禁止重复提交。','LR GD');
combo('M41','开播请求与平台关闭权限同时发生','创建场次时重新校验；权限关闭先生效则拒绝创建，创建先成功则随后立即关播。','HL');
combo('M42','平台关闭直播权限 → 重新开启','公会管理权限不自动重开，须单独开启。','HL');
combo('M43','封禁与解封交错／结果未知后重试','以服务端成功顺序为准，提交检查最新状态；未知先查询原操作，同次重试不重复处置。','UA');
combo('M44','后台角色撤权 → 旧页面执行高权限操作','执行时重新校验，已撤销权限的请求拒绝。','ROLE');
combo('M45','后台／公会长账号停用或重置密码 → 变更前已提交请求','旧会话失效不能发起新操作；变更前已提交／受理的请求继续处理。','AC GD');
const conflicts = [
 {id:'C01',title:'拉黑是否解除好友',current:'当前批注及社交补充：好友保留。',other:'系统概要：解除好友，取消拉黑不恢复。',refs:['B','F'],doc:'系统概要 .md',needle:'|拉黑|',kind:'来源冲突'},
 {id:'C02',title:'拉黑能否相互搜索',current:'当前批注及社交补充：仍可搜索。',other:'系统概要：禁止相互搜索。',refs:['B'],doc:'系统概要 .md',needle:'|拉黑|',kind:'来源冲突'},
 {id:'C03',title:'解除拉黑后原好友私信',current:'当前批注：全部解除后立即恢复。',other:'系统概要把好友关系解除且不恢复，无法得到相同结果。',refs:['F','B'],doc:'系统概要 .md',needle:'|拉黑|',kind:'由C01引出的结果冲突，不另算独立根因'},
 {id:'C04',title:'停用公会是否改变管理账号自身状态',current:'当前批注：撤销对此公会管理权；账号状态与公会状态分别保存；有其他可管理公会可登录。',other:'后台需求清单：所有管理账号置停用，公会启用恢复原状态。',refs:['GD'],doc:'03-管理后台-项目需求清单.md',needle:'**工会状态管理**',kind:'来源冲突'},
 {id:'C05',title:'账号封禁后的关系冻结／解散',current:'当前批注明确下线、关播与操作拦截，未给出临时／永久封禁对应的团籍、公会关系恢复明细。',other:'后台需求清单提出按临时／永久冻结或解散及申诉恢复。',refs:['UA','UD'],doc:'03-管理后台-项目需求清单.md',needle:'**关系处置**',kind:'文档提出规则，但当前批注未形成完整可执行定义；不是已证实相反行为'},
 {id:'C06',title:'退会未结算分成锁定旧公会',current:'当前批注有退出、关播、身份变化与历史保留，但不能据此确定未结算金额锁定算法。',other:'公会需求清单要求未结算分成按规则锁定旧工会。',refs:['LE','HD'],doc:'02-公会App-项目需求清单.md',needle:'**退会处理**',kind:'关联资金定义缺口'},
 {id:'C07',title:'公会停用后既有主播是否还可开播',current:'公会详情说主播不受影响；主播详情开播条件却要求“公会有效”。',other:'后台需求清单明确停用公会不影响直播权限及正在进行的直播。缺少“公会有效”是否包含启用状态的定义。',refs:['GD','HD'],doc:'03-管理后台-项目需求清单.md',needle:'**工会状态管理**',kind:'描述容易误解；定义缺口，不能仅凭词语判为确定冲突'}
];
for (const c of conflicts) {
 c.status = ['C01','C02','C03'].includes(c.id) ? '已关闭：系统概要已同步' : '需求待确认';
 if(c.status.startsWith('已关闭')) {c.other='当前系统概要已与社交补充、批注一致；历史相反口径只在更新前归档。';c.kind='旧冲突已关闭';}
}
const used = [...new Set([...singles,...combinations,...conflicts].flatMap(r=>r.refs))];
const evidence = used.map(id => ({id,...lookup.get(sources[id])}));
for (const e of evidence) assert(e.pages.length === 1 && e.url && e.sections.length, `证据不完整：${e.id}`);
for (const c of conflicts) {
 c.file = path.join(root,'liveshow-proto/context',c.doc);
 const lines = fs.readFileSync(c.file,'utf8').split('\n');
 c.line = lines.findIndex(l=>l.includes(c.needle)) + 1;
 assert(c.line > 0, `文档引用失效：${c.id}`);
 c.quote = lines[c.line-1];
}
const all = [...singles,...combinations,...conflicts];
assert.equal(new Set(all.map(r=>r.id)).size,all.length,'重复编号');
for (const r of combinations.filter(r=>r.status==='需求待确认')) assert.equal(r.result,'','未知结果必须留空');
const escape = x => String(x || '').replace(/\|/g,'\\|').replace(/\n/g,'<br>');
const refs = r => r.refs.map(id=>`[${id}](#来源-${id.toLowerCase()})`).join('、');
let md = `# 操作与组合影响表\n\n> ${snapshot.date}，基于替换后的原型重建。范围：改变社交关系、团籍／群籍、房管、主播／公会身份与账号／直播管理权限的操作；不包含普通导航、输入、送礼等全部UI动作。\n> 空白表示当前未获得适用的明确依据，不能理解为“不影响”。当前批注不等于已批准需求；跨页归纳和来源冲突单列。M／Q编号用于继续逐项讨论。\n> 本次自动提取全部批注，但语义复核集中在下列操作与组合；本表聚焦关系权限；全业务本轮结果见17号报告和全量场景目录。\n\n## 单个操作\n\n| ID | 操作 | 关系／身份 | 权限／实时行为 | 历史／数据 | 通知 | 来源 |\n|---|---|---|---|---|---|---|\n`;
for (const r of singles) md += '| '+[r.id,r.operation,r.relations,r.permissions,r.history,r.notifications].map(escape).concat(refs(r)).join(' | ')+' |\n';
md += '\n## 多个操作的叠加与先后顺序\n\n| ID | 操作组合／问题 | 有依据的结果 | 状态 | 结果来源 |\n|---|---|---|---|---|\n';
for (const r of combinations) md += '| '+[r.id,r.operation,r.result,r.status].map(escape).concat(refs(r)).join(' | ')+' |\n';
const overview = path.join(root,'liveshow-proto/context/系统概要 .md');
const overviewLines = fs.readFileSync(overview,'utf8').split('\n');
const priorityLine = overviewLines.findIndex(l=>l.includes('账号封禁、账号拉黑和本场踢出等限制优先于房间准入规则。')) + 1;
assert(priorityLine > 0, 'M21准入优先级原文缺失');
md += `\nM21的直接文档依据：[系统概要](<${overview}:${priorityLine}>)：“${overviewLines[priorityLine-1].replace(/^- /,'')}”\n`;
md += '\n## 当前冲突与未同步内容\n\nC01—C03旧冲突已关闭，原编号保留；当前系统概要与社交补充、批注一致。C04—C07待确认。C03与C01同根因，不作独立缺陷累计。\n';
for (const c of conflicts) md += `\n### ${c.id} ${c.title}\n\n状态：${c.status}。类型：${c.kind}。\n\n- 当前：${c.current} 来源：${refs(c)}。\n- 另一来源／缺口：${c.other}\n- 原文：${c.quote}\n- 文档出处：[${c.doc}](<${c.file}:${c.line}>)。\n`;
md += '\n## 来源原文与带批注页面\n\n每个来源保留完整条目，避免把邻接的不同条件误套到当前操作。视图链接进入所属页面，需手动选择下面注明的视图。这里只完成文件与映射核验，未承诺浏览器自动展开视图。\n';
md += `\n补充文档：[社交关系规则补充](<${path.join(root,'liveshow-proto/context/社交关系规则补充.md')}>)、[消息通知规则](<${path.join(root,'liveshow-proto/context/消息通知规则.md')}>)。当前拉黑“可搜索／公开主页、好友保留”与社交补充一致，系统概要现已同步，旧冲突关闭。\n`;
for (const e of evidence) {
 md += `\n### 来源 ${e.id}\n\n导航目录：${e.nav}。${e.view ? `同页视图键：${e.key}。` : ''}\n\n[带批注页面](${e.url}) · [${e.end}/${e.key}](<${e.source}:${e.line}>)\n`;
 for (const s of e.sections) md += `\n**${s.t}**\n\n${s.d.join('\n')}\n`;
}
const data = {date:snapshot.date,scope:'关系、身份与权限操作；局部语义复核',blankMeaning:'未获得明确适用来源，不表示不影响',singles,combinations,conflicts,evidence};
fs.writeFileSync(path.join(out,'11-操作与组合影响表.md'),md);
fs.writeFileSync(path.join(out,'11-操作与组合影响表.json'),JSON.stringify(data,null,2)+'\n');
console.log(JSON.stringify({singles:singles.length,combinations:combinations.length,pending:combinations.filter(r=>!r.result).length,resolvedFormerQ:combinations.filter(r=>r.id.startsWith('Q')&&r.result).map(r=>r.id),evidence:evidence.length,conflicts:conflicts.length},null,2));
