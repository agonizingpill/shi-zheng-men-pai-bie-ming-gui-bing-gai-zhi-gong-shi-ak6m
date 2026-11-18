import re,hashlib,json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import precision_score,recall_score
NUM={'零':0,'〇':0,'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9}
GRID=(.35,.45,.55,.65,.75)
DEFAULT_PARAMS={'ngram':[1,3],'distance_threshold':.55,'candidate_floor':.2,'seed':42,'grid':list(GRID)}
DEFAULT_THRESHOLD=.55
def number(text):
 m=re.search(r'([0-9零〇一二三四五六七八九十]+)号',text)
 if not m:return None
 t=m.group(1)
 if t.isdigit():return int(t)
 if '十' in t:
  a,b=t.split('十');return (NUM.get(a,1) if a else 1)*10+(NUM.get(b,0) if b else 0)
 return int(''.join(str(NUM[x]) for x in t))
def normalize(text):
 n=number(text)
 return re.sub(r'([0-9零〇一二三四五六七八九十]+)号',f'{n}号',text) if n is not None else text
def params_of(value=None):
 p=dict(DEFAULT_PARAMS);p.update(value or {});return p
def _vectorizer(texts,params):
 vec=TfidfVectorizer(analyzer='char',ngram_range=tuple(params['ngram']));vec.fit([normalize(t) for t in texts]);return vec
def _similarity(vec,a,b):
 v=vec.transform([normalize(a),normalize(b)]);return float((v[0]@v[1].T).toarray()[0,0])
def pair_score(pair,vec):
 a,b=pair['left_text'],pair['right_text']
 same_number=number(a) is not None and number(a)==number(b)
 return same_number,_similarity(vec,a,b)
def _split(pairs,seed):
 streets=sorted({p['street'] for p in pairs})
 if len(streets)<2:raise ValueError('核定别名对至少覆盖两条街道，才能按街道分组验收')
 size=min(max(1,round(len(streets)*.25)),len(streets)-1)
 for s in range(seed,seed+50):
  order=np.random.RandomState(s).permutation(len(streets));hold={streets[i] for i in order[:size]};train={streets[i] for i in order[size:]}
  hold_pairs=[p for p in pairs if p['street'] in hold];train_pairs=[p for p in pairs if p['street'] in train]
  if {p['same'] for p in train_pairs}=={0,1} and {p['same'] for p in hold_pairs}=={0,1}:
   return train_pairs,hold_pairs,sorted(train),sorted(hold),s
 raise ValueError('无法在互不重叠的街道组中同时取得同入口与不同入口样本')
def measure(pairs,train_ids,holdout_ids,params=None,threshold=.55):
 p=params_of(params);by={x['id']:x for x in pairs};train=[by[i] for i in train_ids];hold=[by[i] for i in holdout_ids]
 vec=_vectorizer([x['left_text'] for x in train]+[x['right_text'] for x in train],p)
 detail=[];truth=[];pred=[]
 for x in hold:
  same_number,sim=pair_score(x,vec)
  hit=int(same_number and sim>=threshold);truth.append(int(x['same']));pred.append(hit)
  detail.append({'pair_id':x['id'],'street':x['street'],'left_text':x['left_text'],'right_text':x['right_text'],'same':int(x['same']),'predicted':hit,'similarity':round(sim,6)})
 return {'train_pairs':len(train),'holdout_pairs':len(hold),'precision':float(precision_score(truth,pred,zero_division=0)),'recall':float(recall_score(truth,pred,zero_division=0)),'false_merge':sum(1 for a,b in zip(truth,pred) if b==1 and a==0),'miss_merge':sum(1 for a,b in zip(truth,pred) if b==0 and a==1),'holdout_detail':detail}
def calibrate(pairs,params=None):
 p=params_of(params)
 if len(pairs)<4:raise ValueError('核定别名对不足，至少需要4对样本')
 if len({x['street'] for x in pairs})<2:raise ValueError('核定别名对至少覆盖两条街道，才能按街道分组验收')
 train,hold,train_streets,holdout_streets,seed=_split(pairs,int(p['seed']))
 vec=_vectorizer([x['left_text'] for x in train]+[x['right_text'] for x in train],p)
 best=None
 for z in p['grid']:
  truth=[int(x['same']) for x in train];pred=[]
  for x in train:
   same_number,sim=pair_score(x,vec);pred.append(int(same_number and sim>=float(z)))
  pr=float(precision_score(truth,pred,zero_division=0));rc=float(recall_score(truth,pred,zero_division=0))
  key=(pr+rc,rc,-float(z))
  if best is None or key>best[0]:best=(key,float(z))
 threshold=best[1]
 result=measure(pairs,[x['id'] for x in train],[x['id'] for x in hold],p,threshold)
 result.update({'threshold':threshold,'train_streets':train_streets,'holdout_streets':holdout_streets,'train_ids':[x['id'] for x in train],'holdout_ids':[x['id'] for x in hold],'split_seed':seed})
 return result
def match(entrances,aliases,rule=None):
 if len(entrances)<2 or len(aliases)<2:raise ValueError('至少两个入口和两个有文字的别名')
 p=params_of((rule or {}).get('params'));threshold=float(rule['threshold']) if rule and rule.get('threshold') is not None else DEFAULT_THRESHOLD
 texts=[normalize(a['text']) for a in aliases];vec=TfidfVectorizer(analyzer='char',ngram_range=tuple(p['ngram']));v=vec.fit_transform(texts);sim=(v@v.T).toarray();dist=np.clip(1-sim,0,2);np.fill_diagonal(dist,0)
 labels=AgglomerativeClustering(n_clusters=None,distance_threshold=float(p['distance_threshold']),metric='precomputed',linkage='average').fit_predict(dist)
 candidates=[];floor=float(p['candidate_floor'])
 for i,x in enumerate(entrances):
  for y in entrances[i+1:]:
   ix=[j for j,a in enumerate(aliases) if a['entrance_id']==x['id']];iy=[j for j,a in enumerate(aliases) if a['entrance_id']==y['id']]
   if not ix or not iy:continue
   score=float(max(sim[a,b] for a in ix for b in iy));conflict=x['number']!=y['number'] or x['street']!=y['street']
   if score>=floor:candidates.append({'source_id':x['id'],'target_id':y['id'],'similarity':round(score,6),'conflict':int(conflict),'above_threshold':int(score>=threshold)})
 return {'algorithm':'字符TF-IDF+AgglomerativeClustering average linkage','source_sha256':hashlib.sha256(json.dumps([entrances,aliases],ensure_ascii=False,sort_keys=True).encode()).hexdigest(),'rule':{'version_id':rule.get('id') if rule else None,'version':rule.get('version') if rule else None,'threshold':threshold,'params':p},'clusters':[{'alias_id':a['id'],'label':int(k)} for a,k in zip(aliases,labels)],'candidates':candidates}
