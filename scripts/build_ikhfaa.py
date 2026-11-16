import json, csv, collections
D=json.load(open('code/ikhfaa_all.json',encoding='utf-8'))
# following phoneme -> the phonemizer's own letter name (quranic_phonemizer.model.canon.CanonLetter)
LET={'t':'ta','θ':'tha','ʒ':'jeem','d':'dal','ð':'thal','z':'zay','s':'seen','ʃ':'sheen',
     'sˤ':'sad','dˤ':'dad','tˤ':'tah','ðˤ':'zah','f':'fa','q':'qaf','k':'kaf'}
ORDER=[f"ikhfaa_{n}" for n in LET.values()]   # alphabetical (abjad) order of the 15 letters
sites=[]
for s in D['sites']:
    t=f"ikhfaa_{LET[s['following']]}"
    pos='-'.join(r.split(':')[2] for r in s['word_refs'])
    sites.append(dict(t=t,surah=s['surah'],ayah=s['ayah'],pos=pos,w1=s['words'][0],
                      w2=s['words'][1] if len(s['words'])>1 else '',scope=s['scope'],
                      nasal=s['nasal'],following=s['following']))
rows=[]
for t in ORDER:
    for (su,ay) in sorted({(x['surah'],x['ayah']) for x in sites if x['t']==t}):
        a=D['ayahs'][f"{su}:{ay}"]; rows.append([t,su,ay,'','',a['text'],a['phonemes'],''])
with open('out/ikhfaa_dataset.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['tajweed_target','surah','ayah','speaker_id','audio','ayah_uthmani','phoneme_ref','phoneme_realized']); w.writerows(rows)
with open('out/ikhfaa_sites.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['tajweed_target','surah','ayah','word_position','trigger_word','next_word','scope','nasal_phoneme','following_phoneme'])
    for t in ORDER:
        for x in sorted([x for x in sites if x['t']==t],key=lambda x:(x['surah'],x['ayah'],int(x['pos'].split('-')[0]))):
            w.writerow([t,x['surah'],x['ayah'],x['pos'],x['w1'],x['w2'],x['scope'],x['nasal'],x['following']])
print('dataset rows',len(rows),'| sites',len(sites),'| distinct ayahs',len({(r[1],r[2]) for r in rows}))
for t in ORDER: print(f"{t:14s} ayahs {sum(1 for r in rows if r[0]==t):5d}  sites {sum(1 for x in sites if x['t']==t):5d}")
