import json, csv, collections
D=json.load(open('code/idgham_all.json',encoding='utf-8'))
ORDER=['idgham_bi_ghunnah','idgham_bila_ghunnah','idgham_shafawi','idgham_mutamathilayn',
       'idgham_mutajanisayn_kamil','idgham_mutajanisayn_naqis','idgham_mutaqaribayn']
rows=[]
for t in ORDER:
    ks=sorted({(s['surah'],s['ayah']) for s in D['sites'] if s['rule']==t})
    for (su,ay) in ks:
        a=D['ayahs'][f"{su}:{ay}"]
        rows.append([t,su,ay,'','',a['text'],a['phonemes'],''])
H=['tajweed_target','surah','ayah','speaker_id','audio','ayah_uthmani','phoneme_ref','phoneme_realized']
with open('out/idgham_dataset.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(H); w.writerows(rows)
srows=[]
for t in ORDER:
    for s in sorted([x for x in D['sites'] if x['rule']==t],key=lambda x:(x['surah'],x['ayah'],int(x['word_refs'][0].split(':')[2]))):
        pos=[r.split(':')[2] for r in s['word_refs']]
        srows.append([t,s['surah'],s['ayah'],'-'.join(pos),s['words'][0],s['words'][1] if len(s['words'])>1 else '',
                      'cross_word' if len(s['words'])>1 else 'within_word'])
with open('out/idgham_sites.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['tajweed_target','surah','ayah','word_position','trigger_word','next_word','scope']); w.writerows(srows)
print('dataset rows',len(rows),'sites',len(srows))
print(collections.Counter(r[0] for r in rows)); print(collections.Counter((r[0],r[6]) for r in srows))
print('distinct ayahs with any idgham',len({(r[1],r[2]) for r in rows}))
