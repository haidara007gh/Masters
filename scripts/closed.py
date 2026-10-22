import csv, json
from quranic_phonemizer import Phonemizer
p=Phonemizer(variants={"iqlab_nasal":"closed"})
rows=list(csv.DictReader(open('out/iqlab_dataset.csv',encoding='utf-8-sig')))
diff_other=0; n_changed=0; iq_total=0
for r in rows:
    res=p.analyse(f"{r['surah']}:{r['ayah']}")
    new=" ".join(res.phonemes()); old=r['phoneme_ref']
    iq_total+=sum(1 for o in res.rule_occurrences if o.rule_id.value=='iqlab')
    if new!=old: n_changed+=1
    # only ŋ->m̃ substitutions allowed
    o,nw=old.split(),new.split()
    if len(o)!=len(nw) or any(a!=b and not (a=='ŋ' and b=='m̃') for a,b in zip(o,nw)): diff_other+=1
    if res.text()!=r['ayah_uthmani']: diff_other+=1
    r['phoneme_ref']=new
print('rows',len(rows),'changed',n_changed,'rows with other differences',diff_other,'iqlab sites',iq_total)
w=csv.DictWriter(open('out/iqlab_dataset_closed.csv','w',encoding='utf-8-sig',newline=''),fieldnames=list(rows[0].keys()))
w.writeheader(); w.writerows(rows)
for r in rows[:1]+[x for x in rows if x['surah']=='2' and x['ayah']=='68']: print(r['surah'],r['ayah'],r['phoneme_ref'])
