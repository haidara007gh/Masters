import json, sys, collections
from quranic_phonemizer import Phonemizer
d=json.load(open(sys.argv[1],encoding='utf-8'))
p=Phonemizer(variants={"iqlab_nasal":"closed"})
out={}; sites=[]
for ch in d:
    for v in ch['verses']:
        k=f"{ch['id']}:{v['id']}"
        r=p.analyse(k)
        occ=[o for o in r.rule_occurrences if o.rule_id.value.startswith('idgham')]
        out[k]=dict(text=r.text(),phonemes=" ".join(r.phonemes()),types=sorted({o.rule_id.value for o in occ}))
        for o in occ:
            ws=[r.words[i.value] for i in o.word_ids]
            sites.append(dict(surah=ch['id'],ayah=v['id'],rule=o.rule_id.value,
                              word_refs=[w.ref for w in ws],words=[w.text for w in ws]))
json.dump(dict(ayahs=out,sites=sites),open(sys.argv[2],'w',encoding='utf-8'),ensure_ascii=False)
c=collections.Counter(s['rule'] for s in sites)
print(c)
print('ayahs per type',{t:len({(s['surah'],s['ayah']) for s in sites if s['rule']==t}) for t in c})
print('word-count per site',collections.Counter((s['rule'],len(s['words'])) for s in sites))
