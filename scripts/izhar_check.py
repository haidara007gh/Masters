import json, unicodedata, collections
D=json.load(open('code/izhar_all.json',encoding='utf-8'))
Q=json.load(open('dl/node_modules/quran-json/dist/quran.json',encoding='utf-8'))
NOON='ن'
TAN=set('ًٌٍٖٗٞ')    # standard + open tanween
HAR=set('َُِ')
SH='ّ'
HAMZA_MARK='ٔ'                                 # hamza written as a mark (e.g. on a tatweel)
THROAT=set('ءأإؤئآهعحغخ')                           # hamza in all its seats, ه ع ح غ خ; NOT ٱ (hamzat al-wasl)
STOP=set('ۖۗۘۙۚۛۜ۝۞')
def mark(c): return unicodedata.category(c) in ('Mn','Mc','Me')
def letters(w):
    out=[]
    for c in w:
        if c=='ـ': out.append(['ـ',set()]); continue    # keep tatweel as a seat
        if mark(c) and out: out[-1][1].add(c)
        elif not mark(c): out.append([c,set()])
    return out
def base(L,j):
    c,m=L[j]
    if c=='ـ' and HAMZA_MARK in m: return 'ء'
    return c
halqi=collections.Counter(); mutlaq=collections.Counter()
for ch in Q:
    for v in ch['verses']:
        k=f"{ch['id']}:{v['id']}"
        ws=[letters(w) for w in v['text'].split() if not set(w)<=STOP]
        for wi,L in enumerate(ws):
            for li,(c,m) in enumerate(L):
                is_noon=(c==NOON and not (m&(HAR|{SH}|TAN)))
                trig=is_noon or bool(m&TAN)
                if not trig: continue
                j=li+1
                if m&TAN and j<len(L) and L[j][0] in ('ا','ى'): j+=1
                if j<len(L): nxt=base(L,j); same=True
                elif wi+1<len(ws): nxt=base(ws[wi+1],0); same=False
                else: continue                                   # ayah end: excluded
                if nxt in THROAT: halqi[k]+=1
                elif is_noon and same and nxt in ('و','ي'): mutlaq[k]+=1
ph_h=collections.Counter(f"{s['surah']}:{s['ayah']}" for s in D['sites'] if s['kind']=='halqi')
ph_m=collections.Counter(f"{s['surah']}:{s['ayah']}" for s in D['sites'] if s['kind']=='mutlaq')
for name,mine,ph in [('halqi',halqi,ph_h),('mutlaq',mutlaq,ph_m)]:
    keys=set(mine)|set(ph)
    diff=[(k,mine[k],ph[k]) for k in sorted(keys,key=lambda x:tuple(map(int,x.split(':')))) if mine[k]!=ph[k]]
    print(f"{name}: text method {sum(mine.values())} | phonemizer {sum(ph.values())} | ayahs differing {len(diff)}", diff[:20])
