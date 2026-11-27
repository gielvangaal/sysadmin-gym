"""Append-only event history and history-weighted exercise selection."""
import json, math, random, time
from collections import Counter, defaultdict

DEFAULT={'version':'3.2.0','tasks_per_round':7,
 'modules':[{'name':'network','enabled':True,'count':3,'every':1},
            {'name':'permissions','enabled':True,'count':1,'every':1},
            {'name':'files','enabled':True,'count':1,'every':1},
            {'name':'shell','enabled':True,'count':1,'every':1},
            {'name':'observe','enabled':True,'count':1,'every':1},
            {'name':'tls','enabled':True,'count':1,'every':3}],
 'adaptive':{'enabled':True,'base_weight':1.0,'failure_bonus':1.7,
             'topic_failure_bonus':0.6,'recent_success_discount':0.55,
             'uncompleted_bonus':0.6,'unseen_bonus':0.7,'min_weight':0.2}}

def config(root):
    path=root/'gym-config.json'
    cfg=json.loads(path.read_text()) if path.exists() else DEFAULT
    assert 5<=int(cfg['tasks_per_round'])<=20
    names=set()
    for m in cfg['modules']:
        assert m['name'] not in names and int(m['every'])>0 and int(m['count'])>=0
        names.add(m['name'])
    return cfg

def read_history(root):
    path=root/'history'/'events.jsonl'
    stats=defaultdict(lambda:{'pass':0,'fail':0,'skipped':0,'last':None})
    topics=defaultdict(lambda:{'pass':0,'fail':0,'skipped':0})
    rounds=0
    checked=set()
    if path.exists():
        for line in path.read_text().splitlines():
            if not line.strip():continue
            ev=json.loads(line)
            if ev['event']=='reset':
                rounds+=1
                for r in ev['results']:
                    if r['ok'] is None:
                        stats[r['id']]['skipped']+=1;topics[r['group']]['skipped']+=1
            if ev['event']=='check':
                for r in ev['results']:
                    identity=(ev['session'],r['id'])
                    if identity in checked:
                        stats[r['id']]['last']=r['ok']
                        continue
                    checked.add(identity)
                    key='pass' if r['ok'] else 'fail'
                    stats[r['id']][key]+=1
                    topics[r['group']][key]+=1
                    stats[r['id']]['last']=r['ok']
    # Old progress.json contains completed v3 rounds; keep it as a baseline
    # only for tasks with no new events, avoiding double counting.
    old=root/'progress.json'
    if old.exists():
        legacy=json.loads(old.read_text())
        for tid,totals in legacy.items():
            if tid not in stats:
                stats[tid]['pass']=totals.get('pass',0)
                stats[tid]['fail']=totals.get('fail',0)
                stats[tid]['last']=None
    return {'tasks':stats,'topics':topics,'rounds':rounds}

def record(root,event):
    directory=root/'history';directory.mkdir(exist_ok=True)
    event['timestamp']=time.strftime('%Y-%m-%dT%H:%M:%S%z')
    # Append and fsync: a check event is durable before user resets workspace.
    import os
    with (directory/'events.jsonl').open('a') as f:
        f.write(json.dumps(event,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())

def weight_for(task,history,cfg):
    rules=cfg['adaptive']
    if not rules['enabled']:return 1.0
    st=history['tasks'].get(task['id'],{})
    topic=history['topics'].get(task['group'],{})
    failures=st.get('fail',0);success=st.get('pass',0)
    topic_total=topic.get('fail',0)+topic.get('pass',0)
    topic_rate=topic.get('fail',0)/topic_total if topic_total else 0
    # Saturating bonuses prevent an old streak from dominating indefinitely.
    w=rules['base_weight']+rules['failure_bonus']*(1-math.exp(-failures/2))
    w+=rules['topic_failure_bonus']*topic_rate
    w+=rules['uncompleted_bonus']*(1-math.exp(-st.get('skipped',0)/2))
    if not failures and not success:w+=rules['unseen_bonus']
    if st.get('last') is True:w*=rules['recent_success_discount']
    return max(rules['min_weight'],w)

def summary(root):
    h=read_history(root)
    print('Completed rounds:',h['rounds'])
    for name,t in sorted(h['topics'].items()):
        print(f'{name:14} FIRST PASS {t["pass"]:3} FIRST FAIL {t["fail"]:3} UNCHECKED {t["skipped"]:3}')
    print('Most missed exercises:')
    for tid,t in sorted(h['tasks'].items(),key=lambda it:(-it[1]['fail'],it[0]))[:12]:
        print(f'  {tid:22} pass={t["pass"]} fail={t["fail"]} unchecked={t["skipped"]}')
