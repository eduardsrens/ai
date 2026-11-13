"""Pocket Party: a local, turn-based party board game. Rules live in Python."""
import random
import time

VERSION = 2
TYPES = ['start'] + [('home' if i in (7,21,35) else 'chance' if i in (5,14,23,32,44) else 'family' if i in (11,26,41) else 'trap' if i%6==0 else 'payday' if i%4==0 else 'life') for i in range(1,49)]
ITEMS = {'rocket':{'name':'Pocket rocket','description':'Deal 7 damage to a rival.'}, 'magnet':{'name':'Key magnet','description':'Steal up to 8 keys from a rival.'}, 'shield':{'name':'Bubble shield','description':'Block the next attack or trap.'}, 'swap':{'name':'Switcheroo','description':'Swap positions with a rival.'}}
COLORS = ['#d7795c','#6b9ba8','#92a86d','#b497ba']
MINIS = ['reaction','memory','mash']

def new_game():
    return dict(version=VERSION,phase='setup',players=[],current=0,round=1,max_rounds=8,roll=None,rolled=False,used_item=False,pending=None,event={'title':'Good friends. Questionable decisions.','text':'Gather 2–4 players. One screen. A little friendly chaos.','kind':'welcome'},history=[],mini=None)

def record(g,title,text,kind='life'):
    g['event']=dict(title=title,text=text,kind=kind)
    g['history'].insert(0,dict(title=title,text=text,kind=kind,round=g['round']))
    g['history']=g['history'][:80]

def require(g,phase):
    if g['phase']!=phase:raise ValueError('That action is not available right now.')

def start(g,names):
    require(g,'setup')
    if not isinstance(names,list) or not 2<=len(names)<=4:raise ValueError('Choose 2 to 4 players.')
    clean=[str(n).strip()[:18] for n in names]
    if any(not n for n in clean) or len(set(n.lower() for n in clean))!=len(clean):raise ValueError('Each player needs a different name.')
    g['players']=[dict(id=i,name=n,color=COLORS[i],position=0,hp=20,keys=10,trophies=0,items=['rocket','shield'],shield=False) for i,n in enumerate(clean)]
    g['phase']='handoff'
    record(g,'Let the friendly chaos begin.',f'{len(clean)} friends. {g["max_rounds"]} rounds. Most trophies wins.','welcome')
    return g

def ready(g):
    if g['phase']=='handoff':g['phase']='playing'
    elif g['phase']=='minigame_handoff':
        g['phase']='minigame'
        g['mini']['started']=time.time()
        if g['mini']['kind']=='memory':
            rng=random.SystemRandom();g['mini']['gems']=[rng.choice(['gold','green','blue']) for _ in range(20)]
    else:raise ValueError('No handoff is waiting.')
    return g

def player(g):return g['players'][g['current']]

def damage(g,p,amount):
    if p['shield']:
        p['shield']=False
        return f'{p["name"]}’s bubble shield blocked it!'
    p['hp']=max(0,p['hp']-amount)
    if not p['hp']:
        lost=min(p['keys'],8);p['keys']-=lost;p['position']=0;p['hp']=20
        return f'{p["name"]} got knocked out! Lost {lost} keys and respawned at the start with full health.'
    return f'{p["name"]} took {amount} damage. {p["hp"]} HP left.'

def spin(g,rng=None):
    require(g,'playing')
    if g['rolled'] or g['pending']:raise ValueError('Finish this turn before rolling again.')
    rng=rng or random.SystemRandom();p=player(g);roll=rng.randint(1,6);old=p['position'];p['position']=(old+roll)%49
    g.update(roll=roll,rolled=True)
    kind=TYPES[p['position']]
    if kind=='trap':record(g,'A very unfriendly shortcut.',damage(g,p,4),'trap')
    elif kind=='family':
        healed=min(6,20-p['hp']);p['hp']+=healed;record(g,'A little breather.',f'{p["name"]} recovered {healed} HP at the campfire.','family')
    elif kind=='chance':
        item=rng.choice(list(ITEMS));
        if len(p['items'])<3:
            p['items'].append(item);record(g,'Something up your sleeve.',f'{p["name"]} found a {ITEMS[item]["name"].lower()}!','chance')
        else:
            p['keys']+=5;record(g,'Pockets full. Lucky you.',f'{p["name"]} got 5 keys instead of an item.','chance')
    else:
        keys=8 if kind=='payday' else 3;p['keys']+=keys
        record(g,'A little pocket money.',f'{p["name"]} collected {keys} keys.','payday')
    passed_chest=any((old+step)%49 in (7,21,35) for step in range(1,roll+1))
    if passed_chest and p['hp']>0:
        g['pending']={'kind':'chest','title':'A trophy with your name on it.','text':'You passed a trophy chest. Trade 20 keys for one trophy?', 'options':[{'id':'buy','label':'Claim a trophy','detail':'20 keys → 1 trophy','disabled':p['keys']<20},{'id':'skip','label':'Keep your keys','detail':'Save them for the next chest'}]}
    return g

def choose(g,option):
    require(g,'playing')
    if not g['pending'] or option not in ('buy','skip'):raise ValueError('No such choice is waiting.')
    p=player(g)
    if option=='buy':
        if p['keys']<20:raise ValueError('You need 20 keys for a trophy.')
        p['keys']-=20;p['trophies']+=1;record(g,'A shiny little victory.',f'{p["name"]} traded 20 keys for a trophy!','home')
    g['pending']=None
    return g

def use_item(g,item,target=None):
    require(g,'playing');p=player(g)
    if g['used_item'] or g['rolled']:raise ValueError('Use one item before you roll.')
    if item not in p['items']:raise ValueError('That item is not in your pocket.')
    if item=='shield':
        if p['shield']:raise ValueError('Your shield is already active.')
        p['shield']=True;text=f'{p["name"]} is shielded against the next attack or trap.'
    else:
        if not isinstance(target,int) or target==g['current'] or not 0<=target<len(g['players']):raise ValueError('Choose another player as your target.')
        t=g['players'][target]
        if item=='rocket':text=damage(g,t,7)
        elif item=='magnet':
            if t['shield']:t['shield']=False;text=f'{t["name"]} blocked the magnet with a shield!'
            else:
                amount=min(8,t['keys']);t['keys']-=amount;p['keys']+=amount;text=f'{p["name"]} stole {amount} keys from {t["name"]}!'
        elif item=='swap':
            if t['shield']:t['shield']=False;text=f'{t["name"]} blocked the switcheroo!'
            else:p['position'],t['position']=t['position'],p['position'];text=f'{p["name"]} swapped places with {t["name"]}!'
    p['items'].remove(item);g['used_item']=True;record(g,ITEMS[item]['name']+'!',text,'chance');return g

def end_turn(g):
    require(g,'playing')
    if not g['rolled'] or g['pending']:raise ValueError('Roll and finish your choices first.')
    g.update(rolled=False,used_item=False,roll=None)
    if g['current']+1<len(g['players']):g['current']+=1;g['phase']='handoff'
    else:
        g['phase']='minigame_handoff';g['mini']=dict(kind=MINIS[(g['round']-1)%3],index=0,scores=[],gems=None,started=None)
    return g

def minigame(g,body):
    require(g,'minigame');m=g['mini'];idx=m['index']
    if m['kind']=='reaction':
        elapsed=float(body.get('elapsed',0))
        if not 0<=elapsed<=10000:raise ValueError('Try again within ten seconds.')
        import math
        position=(math.sin(elapsed/1000*3.4-math.pi/2)+1)/2
        score=round(100*(1-abs(position-.5)*2))
    elif m['kind']=='memory':
        answer=int(body.get('answer',-1))
        if not 0<=answer<=20:raise ValueError('Enter a number from 0 to 20.')
        count=m['gems'].count('gold');score=max(0,100-abs(answer-count)*25)
    else:
        taps=int(body.get('taps',0))
        if not 0<=taps<=100:raise ValueError('Invalid tap count.')
        if time.time()-m['started']<4.5:raise ValueError('The five-second sprint is still running.')
        score=min(100,taps*2)
    m['scores'].append({'player':idx,'score':score});m['index']+=1
    if m['index']<len(g['players']):g['phase']='minigame_handoff'
    else:
        scores=sorted(m['scores'],key=lambda x:(-x['score'],x['player']))
        best=scores[0]['score'];winners=[]
        for rank,result in enumerate(scores):
            p=g['players'][result['player']];p['keys']+=[10,7,4,2][rank]
            if result['score']==best:p['trophies']+=1;winners.append(p['name'])
        record(g,'A round of applause.', ' & '.join(winners)+' won the minigame and earned a trophy! Everyone received keys.','home')
        if g['round']==g['max_rounds']:g['phase']='finished'
        else:g['phase']='round_results'
    return g

def next_round(g):
    require(g,'round_results');g['round']+=1;g['current']=0;g['phase']='handoff';g['mini']=None;return g
