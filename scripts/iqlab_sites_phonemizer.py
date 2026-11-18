"""Rebuild data/iqlab_sites.csv from the Quranic Phonemizer's 'iqlab' labels (same method as the other rules),
keeping the old file's trigger column (noon_sakinah / tanween) by matching sites left to right within each ayah."""
import json, sys, csv, collections
from quranic_phonemizer import Phonemizer
quran, old_path, out_path = sys.argv[1:4]
d=json.load(open(quran,encoding='utf-8'))
p=Phonemizer(variants={"iqlab_nasal":"closed"})
old=collections.defaultdict(list)
for r in csv.DictReader(open(old_path,encoding='utf-8-sig')): old[(r['surah'],r['ayah'])].append(r)
rows=[]; problems=[]
for ch in d:
    for v in ch['verses']:
        k=(str(ch['id']),str(v['id']))
        if k not in old: continue
        r=p.analyse(f"{k[0]}:{k[1]}")
        snd={s.id.value:s for s in r.sounds}; words={w.id.value:w for w in r.words}
        occ=[o for o in r.rule_occurrences if o.rule_id.value=='iqlab']
        found=[]
        for o in occ:
            n=snd[o.sound_ids[0].value]; nxt=snd.get(n.id.value+1)
            w1=words[n.word_id.value]; w2=words[nxt.word_id.value]; same=w2.id==w1.id
            pos=w1.ref.split(':')[2]+('' if same else '-'+w2.ref.split(':')[2])
            found.append([ 'iqlab',k[0],k[1],pos,w1.text,'' if same else w2.text,'within_word' if same else 'cross_word',n.token,nxt.token])
        found.sort(key=lambda x:int(x[3].split('-')[0]))
        if len(found)!=len(old[k]): problems.append((k,len(found),len(old[k]))); continue
        for f,o in zip(found,old[k]): rows.append(f[:7]+[o['trigger']]+f[7:])
print('ayahs',len(old),'| sites',len(rows),'| ayahs with a different count:',problems[:5])
with open(out_path,'w',encoding='utf-8-sig',newline='') as fh:
    w=csv.writer(fh); w.writerow(['tajweed_target','surah','ayah','word_position','trigger_word','next_word','scope','trigger','nasal_phoneme','following_phoneme']); w.writerows(rows)
print('nasal',collections.Counter(r[8] for r in rows),'following',collections.Counter(r[9] for r in rows),'scope',collections.Counter(r[6] for r in rows))
