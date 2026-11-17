import json, sys, collections
from quranic_phonemizer import Phonemizer
d=json.load(open(sys.argv[1],encoding='utf-8'))
p=Phonemizer(variants={"iqlab_nasal":"closed"})
THROAT={'ʔ':'hamza','h':'heh','ʕ':'ain','ħ':'ha','ɣ':'ghain','x':'kha'}
sites=[]; ayahs={}; pause=0; problems=[]
for ch in d:
    for v in ch['verses']:
        k=f"{ch['id']}:{v['id']}"; r=p.analyse(k)
        occ=[o for o in r.rule_occurrences if o.rule_id.value=='izhar']
        if not occ: continue
        snd={s.id.value:s for s in r.sounds}; words={w.id.value:w for w in r.words}
        kept=False
        for o in occ:
            if len(o.sound_ids)!=1: problems.append((k,'sound_ids',len(o.sound_ids))); continue
            n=snd[o.sound_ids[0].value]; nxt=snd.get(n.id.value+1)
            if nxt is None: pause+=1; continue                     # noon at a pause (ayah end): excluded
            w1=words[n.word_id.value]; w2=words[nxt.word_id.value]; same=(w2.id==w1.id)
            if nxt.token in THROAT: kind='halqi'; target=f"izhar_{THROAT[nxt.token]}"
            elif same and nxt.token in ('w','j'): kind='mutlaq'; target='izhar_mutlaq'
            else: kind='special'; target='izhar_special'
            sites.append(dict(surah=ch['id'],ayah=v['id'],target=target,kind=kind,
                word_refs=[w1.ref]+([] if same else [w2.ref]),words=[w1.text]+([] if same else [w2.text]),
                noon=n.token,following=nxt.token,scope='within_word' if same else 'cross_word'))
            kept=True
        if kept: ayahs[k]=dict(text=r.text(),phonemes=" ".join(r.phonemes()))
json.dump(dict(ayahs=ayahs,sites=sites,problems=problems,pause_excluded=pause),open(sys.argv[2],'w',encoding='utf-8'),ensure_ascii=False)
print('ayahs',len(ayahs),'| sites',len(sites),'| pause noons excluded',pause,'| problems',len(problems),problems[:3])
print('kinds',collections.Counter(s['kind'] for s in sites))
print('targets',collections.Counter(s['target'] for s in sites))
print('noon token',collections.Counter(s['noon'] for s in sites))
for s in sites:
    if s['kind']!='halqi': print('  ',s['target'],s['surah'],s['ayah'],s['words'],s['following'])
