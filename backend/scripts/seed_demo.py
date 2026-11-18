from src.database import Session,Base,engine
from src.models import *
from src.security import password_hash
from src.common import rows

def seed():
 Base.metadata.create_all(engine)
 with Session() as s:
  for role in ['operator','supervisor','viewer']:
   if not any(x.email==role+'@changqiao.local' for x in rows(s,User)):s.add(User(email=role+'@changqiao.local',password=password_hash('Address2026!'),role=role))
  if not s.get(Registry,1):s.add(Registry(id=1,now='2026-11-18T09:00:00'))
  have={(x.street,x.left_text,x.right_text) for x in rows(s,VerifiedPair)}
  for street in ['长桥路','青石街','河滨路','新民巷','榕树街','学府路']:
   for left,right,same,note in [('18号','十八号',1,'旧门牌与现牌面同入口'),('18号南入口','十八号南门',1,'南侧入口方位写法差异'),('18号','81号',0,'数字不同，81号另有独立入口'),('18号','19号',0,'相邻门牌为独立入口')]:
    if (street,street+left,street+right) not in have:s.add(VerifiedPair(street=street,left_text=street+left,right_text=street+right,same=same,note='模拟核定：'+note))
  if not any(x.code=='CQ-018-A' for x in rows(s,Entrance)):
   for code,num,label,lat in [('CQ-018-A',18,'长桥路18号正门',31.210),('CQ-018-B',18,'长桥路十八号旧门牌',31.2101),('CQ-081',81,'长桥路81号',31.211),('CQ-018-C',18,'长桥路18号南入口',31.2102)]:
    e=Entrance(code=code,street='长桥路',number=num,label=label,lat=lat,lng=121.48);s.add(e);s.flush();a=Alias(entrance_id=e.id,text=label);s.add(a);s.flush();s.add(Evidence(alias_id=a.id,reference='照片-'+code,description='2026年11月现场门牌照片与老地籍图位置核验说明'))
   s.flush();es=rows(s,Entrance);p=Proposal(code='P031',source_id=es[1].id,target_id=es[0].id,reason='历史十八号门牌与现18号正门同宗同入口');s.add(p);s.flush();s.add(Objection(proposal_id=p.id,code='Y031',note='住户认为旧门牌对应独立南入口，申请现场复核',state='open'))
  s.commit()
if __name__=='__main__':seed()
