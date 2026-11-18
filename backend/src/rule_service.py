import hashlib,json
from sqlalchemy import select
from .models import VerifiedPair,RuleVersion,RuleActivation
from .common import *
from .matching import params_of,calibrate,measure
def create_pair(s,d):
 lock(s)
 if d['same'] not in (0,1):fail('核定结论只能是同入口或不同入口')
 x=VerifiedPair(**d);s.add(x);s.flush();return x
def snapshot(s,x):
 ids=list(x.sample_ids or []);found={p.id:p for p in s.scalars(select(VerifiedPair).where(VerifiedPair.id.in_(ids))).all()}
 return [dump(found[i]) for i in ids if i in found]
def create(s,d=None):
 r=lock(s);pairs=rows(s,VerifiedPair)
 if len(pairs)<4:fail('核定别名对不足4对，不能校准规则')
 d=d or {}
 params=params_of()
 params.update({'ngram':[d.get('ngram_min',params['ngram'][0]),d.get('ngram_max',params['ngram'][1])],'distance_threshold':d.get('distance_threshold',params['distance_threshold']),'candidate_floor':d.get('candidate_floor',params['candidate_floor']),'seed':d.get('seed',params['seed'])})
 if params['ngram'][0]>params['ngram'][1]:fail('字符n-gram下界不能大于上界')
 ids=[x.id for x in pairs];last=s.scalars(select(RuleVersion).order_by(RuleVersion.version.desc())).first()
 body=[{'id':x.id,'street':x.street,'left_text':x.left_text,'right_text':x.right_text,'same':int(x.same)} for x in pairs]
 x=RuleVersion(version=(last.version if last else 0)+1,state='queued',params=params,attempt=1,sample_ids=ids,source_sha256=hashlib.sha256(json.dumps(body,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),created=r.now)
 s.add(x);s.flush();return x
def retry(s,id):
 lock(s);x=get(s,RuleVersion,id)
 if x.state not in ['queued','failed','running']:fail('只有排队中、中断或失败的评估可以重试')
 x.state='queued';x.attempt=(x.attempt or 1)+1;x.error=''
 return x
def decide(s,x,report):
 current=s.scalars(select(RuleVersion).where(RuleVersion.state=='active')).first()
 x.precision=report['precision'];x.recall=report['recall'];x.false_merge=report['false_merge'];x.miss_merge=report['miss_merge']
 x.threshold=report['threshold'];x.train_streets=report['train_streets'];x.holdout_streets=report['holdout_streets']
 x.train_pairs=report['train_pairs'];x.holdout_pairs=report['holdout_pairs'];x.holdout_detail=report['holdout_detail'];x.holdout_ids=report['holdout_ids'];x.train_ids=report['train_ids']
 if current and current.version>x.version:
  x.state='superseded';x.decision=f'V{current.version} 已生效，本版晚出分仅留档，不得顶替'
  return x
 if current:
  base=measure(snapshot(s,x),x.train_ids,x.holdout_ids,current.params,current.threshold)
  x.baseline={'version':current.version,'threshold':current.threshold,'false_merge':base['false_merge'],'miss_merge':base['miss_merge'],'precision':base['precision'],'recall':base['recall']}
  if report['false_merge']>base['false_merge']:
   x.state='declined';x.decision=f'同批验收错合 {report["false_merge"]} 多于现行 V{current.version} 的 {base["false_merge"]}，沿用现行规则'
   return x
  x.state='passed';x.decision=f'同批验收错合 {report["false_merge"]} 不多于现行 V{current.version} 的 {base["false_merge"]}，可人工启用'
  return x
 x.state='passed';x.decision='首版校准完成，可人工启用'
 return x
def evaluate(s,id):
 lock(s);x=get(s,RuleVersion,id)
 if x.state!='queued':return x
 token=x.attempt;x.state='running';s.commit()
 try:report=calibrate(snapshot(s,x),x.params)
 except Exception as e:
  lock(s);x=get(s,RuleVersion,id)
  if x.attempt!=token:return x
  x.state='failed';x.error=str(e)[:500];s.commit();return x
 lock(s);x=get(s,RuleVersion,id)
 if x.attempt!=token or x.state!='running':return x
 try:decide(s,x,report)
 except Exception as e:
  s.rollback();lock(s);x=get(s,RuleVersion,id)
  if x.attempt!=token:return x
  x.state='failed';x.error=str(e)[:500];s.commit();return x
 x.error='';s.commit();return x
def active(s):
 return s.scalars(select(RuleVersion).where(RuleVersion.state=='active')).first()
def activate(s,id,now):
 x=get(s,RuleVersion,id)
 if x.state=='active':return x,activation(s,id)
 if x.state!='passed':fail('只有校准通过且尚未启用的规则版本可启用')
 old=active(s)
 if old and old.version>=x.version:fail('已有更新版本生效，旧版不得顶替')
 if x.precision is None:fail('该版本尚无完整验收结果')
 a=RuleActivation(version_id=x.id,previous_version_id=old.id if old else None,activated=now,note=(x.decision or '')[:500]);s.add(a);s.flush()
 if old:old.state='superseded'
 for other in s.scalars(select(RuleVersion).where(RuleVersion.state=='passed')).all():
  if other.version<x.version:other.state='superseded'
 x.state='active';s.flush()
 return x,a
def activation(s,id):
 return s.scalars(select(RuleActivation).where(RuleActivation.version_id==id)).first()
