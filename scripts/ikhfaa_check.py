import json, unicodedata, collections
D=json.load(open('code/ikhfaa_all.json',encoding='utf-8'))
Q=json.load(open('dl/node_modules/quran-json/dist/quran.json',encoding='utf-8'))
NOON='ن'
TAN=set('ًٌٍٖٗٞ')   # standard + open tanween (U+0657 fathatan, U+0656 kasratan, U+065E dammatan)
HAR=set('َُِ')
SH='ّ'
IKH=set('تثجدذزسشصضطظفقك')
STOP=set('ۖۗۘۙۚۛۜ۝۞')
def mark(c): return unicodedata.category(c) in ('Mn','Mc','Me') or c=='ـ'
def letters(w):
    out=[]
    for c in w:
        if mark(c) and out: out[-1][1].add(c)
        elif not mark(c): out.append([c,set()])
    return out
mine=collections.Counter()
for ch in Q:
    for v in ch['verses']:
        k=f"{ch['id']}:{v['id']}"
        ws=[letters(w) for w in v['text'].split() if not set(w)<=STOP]
        for wi,L in enumerate(ws):
            for li,(c,m) in enumerate(L):
                trig = (c==NOON and not (m&(HAR|{SH}|TAN))) or bool(m&TAN)
                if not trig: continue
                j=li+1
                if m&TAN and j<len(L) and L[j][0] in ('ا','ى') : j+=1   # carrier alif / alif maqsura after fathatan
                if j<len(L): nxt=L[j][0]
                elif wi+1<len(ws): nxt=ws[wi+1][0][0]
                else: continue                                          # ayah end: stop, no ikhfaa
                if nxt in IKH: mine[k]+=1
ph=collections.Counter(f"{s['surah']}:{s['ayah']}" for s in D['sites'])
keys=set(mine)|set(ph)
diff=[(k,mine[k],ph[k]) for k in sorted(keys,key=lambda x:tuple(map(int,x.split(':')))) if mine[k]!=ph[k]]
print('sites: text method',sum(mine.values()),'| phonemizer',sum(ph.values()))
print('ayahs: text method',len(mine),'| phonemizer',len(ph))
print('ayahs where counts differ:',len(diff)); print(diff[:25])
