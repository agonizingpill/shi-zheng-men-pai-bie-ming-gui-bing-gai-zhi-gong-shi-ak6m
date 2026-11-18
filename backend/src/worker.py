import os,time,pathlib,logging
try:import redis
except ImportError:redis=None
from .database import Session
from .models import MatchRun,Entrance,Alias,Candidate,RuleVersion
from .common import lock,rows,dump
from .matching import match
from . import rule_service
log=logging.getLogger('worker')
def run_job(s,kind,id):
 if kind=='run':
  lock(s);run=s.get(MatchRun,id)
  if not run or run.state!='queued':return
  try:
   rule=rule_service.active(s)
   result=match([dump(x) for x in rows(s,Entrance)],[dump(x) for x in rows(s,Alias)],dump(rule) if rule else None);run.result=result
   for d in result['candidates']:s.add(Candidate(run_id=run.id,**{k:v for k,v in d.items() if k in ('source_id','target_id','similarity','conflict')}))
   run.state='ready'
  except Exception as e:run.state='failed';run.error=str(e)[:500];logging.exception('matching failed')
  s.commit()
 elif kind=='rule':
  x=s.get(RuleVersion,id)
  if x and x.state=='queued':rule_service.evaluate(s,id)
 else:log.error('unknown job %s',kind)
def main():
 pathlib.Path('/artifacts/address-heartbeat').parent.mkdir(parents=True,exist_ok=True)
 q=redis.from_url(os.environ['REDIS_URL'],decode_responses=True)
 while True:
  pathlib.Path('/artifacts/address-heartbeat').write_text(str(time.time()))
  item=q.blpop('address:matching',timeout=2)
  if not item:continue
  kind,raw=str(item[1]).split(':',1)
  with Session() as s:run_job(s,kind,int(raw))
if __name__=='__main__':main()
