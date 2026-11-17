import json, csv
D=json.load(open('code/izhar_all.json',encoding='utf-8'))
# halqi targets in the traditional order of the throat letters (ء ه ع ح غ خ), then mutlaq and the two special cases;
# letter names are the phonemizer's own (quranic_phonemizer.model.canon.CanonLetter)
ORDER=['izhar_hamza','izhar_heh','izhar_ain','izhar_ha','izhar_ghain','izhar_kha','izhar_mutlaq','izhar_special']
sites=[]
for s in D['sites']:
    pos='-'.join(r.split(':')[2] for r in s['word_refs'])
    sites.append(dict(t=s['target'],surah=s['surah'],ayah=s['ayah'],pos=pos,w1=s['words'][0],
                      w2=s['words'][1] if len(s['words'])>1 else '',scope=s['scope'],kind=s['kind'],
                      noon=s['noon'],following=s['following']))
assert {x['t'] for x in sites} <= set(ORDER)
rows=[]
for t in ORDER:
    for (su,ay) in sorted({(x['surah'],x['ayah']) for x in sites if x['t']==t}):
        a=D['ayahs'][f"{su}:{ay}"]; rows.append([t,su,ay,'','',a['text'],a['phonemes'],''])
with open('out/izhar_dataset.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['tajweed_target','surah','ayah','speaker_id','audio','ayah_uthmani','phoneme_ref','phoneme_realized']); w.writerows(rows)
with open('out/izhar_sites.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['tajweed_target','surah','ayah','word_position','trigger_word','next_word','scope','izhar_type','noon_phoneme','following_phoneme'])
    for t in ORDER:
        for x in sorted([x for x in sites if x['t']==t],key=lambda x:(x['surah'],x['ayah'],int(x['pos'].split('-')[0]))):
            w.writerow([t,x['surah'],x['ayah'],x['pos'],x['w1'],x['w2'],x['scope'],x['kind'],x['noon'],x['following']])
print('dataset rows',len(rows),'| sites',len(sites),'| distinct ayahs',len({(r[1],r[2]) for r in rows}))
for t in ORDER: print(f"{t:14s} ayahs {sum(1 for r in rows if r[0]==t):5d}  sites {sum(1 for x in sites if x['t']==t):5d}")
