from sqlalchemy import Column,Integer,String,Float,ForeignKey,JSON,UniqueConstraint
from .database import Base
class User(Base):
 __tablename__='users'
 id=Column(Integer,primary_key=True);email=Column(String(160),unique=True,nullable=False);password=Column(String(160),nullable=False);role=Column(String(20),nullable=False)
class Registry(Base):
 __tablename__='registry'
 id=Column(Integer,primary_key=True);now=Column(String(32),nullable=False)
class Entrance(Base):
 __tablename__='entrances'
 id=Column(Integer,primary_key=True);code=Column(String(40),unique=True,nullable=False);street=Column(String(80),nullable=False);number=Column(Integer,nullable=False);label=Column(String(100),nullable=False);lat=Column(Float,nullable=False);lng=Column(Float,nullable=False)
class Alias(Base):
 __tablename__='aliases'
 id=Column(Integer,primary_key=True);entrance_id=Column(Integer,ForeignKey('entrances.id'),nullable=False);text=Column(String(120),unique=True,nullable=False);state=Column(String(20),default='verified',nullable=False)
class Evidence(Base):
 __tablename__='evidence'
 id=Column(Integer,primary_key=True);alias_id=Column(Integer,ForeignKey('aliases.id'),nullable=False);reference=Column(String(100),unique=True,nullable=False);description=Column(String(500),nullable=False)
class VerifiedPair(Base):
 __tablename__='verified_pairs'
 __table_args__=(UniqueConstraint('street','left_text','right_text',name='uq_verified_pair'),)
 id=Column(Integer,primary_key=True);street=Column(String(80),nullable=False);left_text=Column(String(120),nullable=False);right_text=Column(String(120),nullable=False);same=Column(Integer,nullable=False);note=Column(String(300),default='')
class RuleVersion(Base):
 __tablename__='rule_versions'
 id=Column(Integer,primary_key=True);version=Column(Integer,unique=True,nullable=False);state=Column(String(20),default='queued',nullable=False);params=Column(JSON,nullable=False);attempt=Column(Integer,default=1,nullable=False)
 threshold=Column(Float,nullable=True);train_streets=Column(JSON,nullable=True);holdout_streets=Column(JSON,nullable=True);train_pairs=Column(Integer,default=0);holdout_pairs=Column(Integer,default=0)
 precision=Column(Float,nullable=True);recall=Column(Float,nullable=True);false_merge=Column(Integer,nullable=True);miss_merge=Column(Integer,nullable=True);holdout_detail=Column(JSON,nullable=True);baseline=Column(JSON,nullable=True)
 sample_ids=Column(JSON,nullable=True);holdout_ids=Column(JSON,nullable=True);source_sha256=Column(String(64),default='');decision=Column(String(500),default='');error=Column(String(500),default='');created=Column(String(32),default='')
class RuleActivation(Base):
 __tablename__='rule_activations'
 id=Column(Integer,primary_key=True);version_id=Column(Integer,ForeignKey('rule_versions.id'),unique=True,nullable=False);previous_version_id=Column(Integer,nullable=True);activated=Column(String(32),nullable=False);note=Column(String(500),default='')
class MatchRun(Base):
 __tablename__='match_runs'
 id=Column(Integer,primary_key=True);state=Column(String(20),default='queued');result=Column(JSON,nullable=True);error=Column(String(500),default='')
class Candidate(Base):
 __tablename__='candidates'
 id=Column(Integer,primary_key=True);run_id=Column(Integer,ForeignKey('match_runs.id'),nullable=False);source_id=Column(Integer,ForeignKey('entrances.id'),nullable=False);target_id=Column(Integer,ForeignKey('entrances.id'),nullable=False);similarity=Column(Float,nullable=False);conflict=Column(Integer,nullable=False)
class Proposal(Base):
 __tablename__='proposals'
 id=Column(Integer,primary_key=True);code=Column(String(40),unique=True,nullable=False);source_id=Column(Integer,ForeignKey('entrances.id'),nullable=False);target_id=Column(Integer,ForeignKey('entrances.id'),nullable=False);reason=Column(String(500),nullable=False);state=Column(String(20),default='draft',nullable=False)
class Objection(Base):
 __tablename__='objections'
 id=Column(Integer,primary_key=True);proposal_id=Column(Integer,ForeignKey('proposals.id'),nullable=False);code=Column(String(40),unique=True,nullable=False);note=Column(String(500),nullable=False);state=Column(String(20),default='open');decision=Column(String(30),default='');resolution=Column(String(500),default='')
class Notice(Base):
 __tablename__='notices'
 id=Column(Integer,primary_key=True);proposal_id=Column(Integer,ForeignKey('proposals.id'),unique=True,nullable=False);starts=Column(String(32),nullable=False);ends=Column(String(32),nullable=False);state=Column(String(20),default='public',nullable=False)
class Redirect(Base):
 __tablename__='redirects'
 id=Column(Integer,primary_key=True);source_id=Column(Integer,ForeignKey('entrances.id'),nullable=False);target_id=Column(Integer,ForeignKey('entrances.id'),nullable=False);proposal_id=Column(Integer,ForeignKey('proposals.id'),unique=True,nullable=False);state=Column(String(20),default='active');reason=Column(String(500),default='');created=Column(String(32),nullable=False)
class Audit(Base):
 __tablename__='audit'
 id=Column(Integer,primary_key=True);actor=Column(String(160),nullable=False);action=Column(String(100),nullable=False);detail=Column(String(500),nullable=False)
