import json, unicodedata, collections
D=json.load(open('code/idgham_all.json',encoding='utf-8'))
NOON='ن'; TAN=set('ًٌٍ'); SUK='ْ'; SHADDA='ّ'
HARAKAT=set('َُِ')
def is_mark(c): return unicodedata.category(c) in ('Mn','Mc','Me') or c=='ـ'
def letters(w):
    res=[]
    for c in w:
        if is_mark(c) and res: res[-1][1].add(c)
        elif not is_mark(c): res.append([c,set()])
    return res
BI=set('يومن'); BILA=set('لر')
def first_effective(w):
    L=letters(w)
    if not L: return None
    ch=L[0][0]
    if ch=='ٱ': return None  # hamza wasl: tanween/noon takes kasra -> izhar, not idgham
    if ch in ('ٱ',): return None
    return ch
def trigger(w):
    L=letters(w)
    if not L: return False
    # tanween on last letter, or last letter is carrier alif after fathatan letter
    last=L[-1]
    if last[1]&TAN: return True
    if len(L)>1 and last[0] in ('ا','ى') and (L[-2][1]&TAN): return True
    if last[0]=='ى' and (last[1]&TAN): return True
    if last[0]==NOON and not (last[1]&(HARAKAT|{SHADDA})): return True
    return False
mine=collections.defaultdict(set)
for k,a in D['ayahs'].items():
    ws=a['text'].split()
    ws=[w for w in ws if any(not is_mark(c) and c not in '۞' and '؀'<=c<='ۿ' for c in w) and not all(c in 'ۖۗۘۙۚۛۜ۝' for c in w)]
    for i in range(len(ws)-1):
        if trigger(ws[i]):
            f=first_effective(ws[i+1])
            if f in BI: mine['idgham_bi_ghunnah'].add((k,i+1))
            elif f in BILA: mine['idgham_bila_ghunnah'].add((k,i+1))
ph=collections.defaultdict(set)
for s in D['sites']:
    if s['rule'] in ('idgham_bi_ghunnah','idgham_bila_ghunnah') and len(s['words'])==2:
        k=f"{s['surah']}:{s['ayah']}"; pos=int(s['word_refs'][0].split(':')[2])
        ph[s['rule']].add((k,pos))
for t in ('idgham_bi_ghunnah','idgham_bila_ghunnah'):
    m,p=mine[t],ph[t]
    print(t,'mine',len(m),'phonemizer',len(p),'both',len(m&p),'only mine',len(m-p),'only phon',len(p-m))
    print('  only mine sample',sorted(m-p)[:8]); print('  only phon sample',sorted(p-m)[:8])


# ---- shafawi: meem sakinah (no vowel) + meem
sh=set()
for k,a in D['ayahs'].items():
    ws=[w for w in a['text'].split() if not all(c in 'ۖۗۘۙۚۛۜ۝' for c in w)]
    for i in range(len(ws)-1):
        L=letters(ws[i]); N=letters(ws[i+1])
        if L and N and L[-1][0]=='م' and not (L[-1][1]&(HARAKAT|{SHADDA}|TAN)) and N[0][0]=='م':
            sh.add((k,i+1))
phs={(f"{s['surah']}:{s['ayah']}",int(s['word_refs'][0].split(':')[2])) for s in D['sites'] if s['rule']=='idgham_shafawi' and len(s['words'])==2}
print('shafawi mine',len(sh),'phonemizer(2-word)',len(phs),'both',len(sh&phs),'only mine',sorted(sh-phs)[:6],'only phon',sorted(phs-sh)[:6])
