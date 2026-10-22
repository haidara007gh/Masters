import json, sys, time
from quranic_phonemizer import Phonemizer
d=json.load(open(sys.argv[1],encoding='utf-8'))
p=Phonemizer()
out={}
t0=time.time()
for ch in d:
    s=ch['id']
    for v in ch['verses']:
        a=v['id']
        r=p.analyse(f"{s}:{a}")
        n=sum(1 for o in r.rule_occurrences if o.rule_id.value=='iqlab')
        out[f"{s}:{a}"]=dict(n_iqlab=n, text=r.text(), phonemes=" ".join(r.phonemes()))
    if s%10==0: print('surah',s,round(time.time()-t0,1),'s',flush=True)
json.dump(out,open(sys.argv[2],'w',encoding='utf-8'),ensure_ascii=False)
print('done',len(out),round(time.time()-t0,1),'s')
