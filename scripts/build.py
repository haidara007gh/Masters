import json, csv, collections
d=json.load(open('dl/node_modules/quran-json/dist/quran.json',encoding='utf-8'))
ph=json.load(open('code/phon_all.json',encoding='utf-8'))
src=open('code/detect.py',encoding='utf-8').read().split("rows=[]; mism=[]")[0].replace("src, out = sys.argv[1], sys.argv[2]\nd = json.load(open(src, encoding='utf-8'))","")
ns={}; exec(src,ns); mb=ns['method_b']; MS=ns['SMALL_MEEMS']

main=[]; sites_rows=[]; boundary=[]
for ch in d:
    for ai,v in enumerate(ch['verses']):
        k=f"{ch['id']}:{v['id']}"; t=v['text']; words=t.split()
        sites=mb(t)
        if sites:
            main.append([ 'iqlab', ch['id'], v['id'], '', '', ph[k]['text'], ph[k]['phonemes'], '' ])
            for (wi,w,nw,trig,scope) in sites:
                nxt = words[wi] if scope=='cross_word' else ''
                sites_rows.append([ch['id'],v['id'],wi,w,nxt,trig,scope])
        # boundary signs
        last=len(words)
        in_last=sum(1 for s in sites if s[0]==last and s[4]=='same_word')
        last_signs=sum(1 for c in words[-1] if c in MS)
        if last_signs>in_last:
            if ai+1<len(ch['verses']):
                nxtw=ch['verses'][ai+1]['text'].split()[0]; where=f"first word of {ch['id']}:{ai+2}"
            else:
                nxtw='بِسۡمِ'; where='bismillah opening next surah'
            boundary.append([ch['id'],v['id'],words[-1],nxtw,where,'yes' if sites else 'no'])

H=['tajweed_target','surah','ayah','speaker_id','audio','ayah_uthmani','phoneme_ref','phoneme_realized']
with open('out/iqlab_dataset.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(H); w.writerows(main)
with open('out/iqlab_sites.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['surah','ayah','word_position','trigger_word','next_word','trigger','scope']); w.writerows(sites_rows)
with open('out/iqlab_ayah_end_only.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['surah','ayah','last_word','following_word','following_word_location','ayah_also_has_internal_iqlab']); w.writerows(boundary)

print('main rows',len(main),'sites',len(sites_rows),'boundary',len(boundary))
print('trigger',collections.Counter(r[5] for r in sites_rows)); print('scope',collections.Counter(r[6] for r in sites_rows))
print('boundary w/o internal:',sum(1 for b in boundary if b[5]=='no'),' with:',sum(1 for b in boundary if b[5]=='yes'))
per=collections.Counter(r[1] for r in main)
print('surahs with iqlab',len(per),'; without:',[s for s in range(1,115) if s not in per])
print('top surahs',per.most_common(6))
print('max sites in one ayah',collections.Counter((r[0],r[1]) for r in sites_rows).most_common(3))
