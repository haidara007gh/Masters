import json, csv, collections, unicodedata
D=json.load(open('code/idgham_all.json',encoding='utf-8'))
def is_mark(c): return unicodedata.category(c) in ('Mn','Mc','Me') or c=='ـ'
def first_letter(w):
    for c in w:
        if not is_mark(c): return c
LET={'ي':'yaa','ن':'noon','م':'meem','و':'waw','ل':'lam','ر':'raa'}  # names follow the Qur'anic Phonemizer's rule descriptions
FAM={'idgham_bi_ghunnah':{'yaa','noon','meem','waw'},'idgham_bila_ghunnah':{'lam','raa'}}
sites=[]
for s in D['sites']:
    if s['rule'] not in FAM: continue
    if len(s['words'])==2: nm=LET[first_letter(s['words'][1])]; scope='cross_word'
    else:
        assert s['words'][0]=='طسٓمٓ' and s['rule']=='idgham_bi_ghunnah'; nm='meem'; scope='within_word'  # sin|meem inside the letter-name word
    assert nm in FAM[s['rule']], (s,nm)
    t=f"{s['rule']}_{nm}" if s['rule']=='idgham_bila_ghunnah' else f"idgham_bi_ghunnah_{nm}"
    sites.append(dict(t=t,surah=s['surah'],ayah=s['ayah'],pos='-'.join(r.split(':')[2] for r in s['word_refs']),
                      w1=s['words'][0],w2=s['words'][1] if len(s['words'])>1 else '',scope=scope))
ORDER=['idgham_bi_ghunnah_yaa','idgham_bi_ghunnah_noon','idgham_bi_ghunnah_meem','idgham_bi_ghunnah_waw',
       'idgham_bila_ghunnah_lam','idgham_bila_ghunnah_raa']
rows=[]
for t in ORDER:
    for (su,ay) in sorted({(x['surah'],x['ayah']) for x in sites if x['t']==t}):
        a=D['ayahs'][f"{su}:{ay}"]; rows.append([t,su,ay,'','',a['text'],a['phonemes'],''])
with open('out/idgham_dataset.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['tajweed_target','surah','ayah','speaker_id','audio','ayah_uthmani','phoneme_ref','phoneme_realized']); w.writerows(rows)
with open('out/idgham_sites.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['tajweed_target','surah','ayah','word_position','trigger_word','next_word','scope'])
    for t in ORDER:
        for x in sorted([x for x in sites if x['t']==t],key=lambda x:(x['surah'],x['ayah'],int(x['pos'].split('-')[0]))):
            w.writerow([t,x['surah'],x['ayah'],x['pos'],x['w1'],x['w2'],x['scope']])
print('rows',len(rows),'sites',len(sites))
for t in ORDER: print(t,'ayahs',sum(1 for r in rows if r[0]==t),'sites',sum(1 for x in sites if x['t']==t))
