import json, sys, collections
from quranic_phonemizer import Phonemizer
d=json.load(open(sys.argv[1],encoding='utf-8'))
p=Phonemizer(variants={"iqlab_nasal":"closed"})
sites=[]; ayahs={}; problems=[]
for ch in d:
    for v in ch['verses']:
        k=f"{ch['id']}:{v['id']}"; r=p.analyse(k)
        occ=[o for o in r.rule_occurrences if o.rule_id.value=='ikhfaa']
        if not occ: continue
        ayahs[k]=dict(text=r.text(),phonemes=" ".join(r.phonemes()))
        snd={s.id.value:s for s in r.sounds}; words={w.id.value:w for w in r.words}
        for o in occ:
            if len(o.sound_ids)!=1: problems.append((k,'sound_ids',len(o.sound_ids))); continue
            n=snd[o.sound_ids[0].value]; nxt=snd.get(n.id.value+1)
            if nxt is None: problems.append((k,'no following sound')); continue
            w1=words[n.word_id.value]; w2=words[nxt.word_id.value]
            sites.append(dict(surah=ch['id'],ayah=v['id'],word_refs=[w1.ref]+([w2.ref] if w2.id!=w1.id else []),
                words=[w1.text]+([w2.text] if w2.id!=w1.id else []),nasal=n.token,following=nxt.token,
                scope='within_word' if w2.id==w1.id else 'cross_word'))
json.dump(dict(ayahs=ayahs,sites=sites,problems=problems),open(sys.argv[2],'w',encoding='utf-8'),ensure_ascii=False)
print('ayahs',len(ayahs),'sites',len(sites),'problems',len(problems),problems[:5])
print('nasal tokens',collections.Counter(s['nasal'] for s in sites))
print('following tokens',collections.Counter(s['following'] for s in sites))
print('scope',collections.Counter(s['scope'] for s in sites))
