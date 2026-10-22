import json, sys, re, collections
src, out = sys.argv[1], sys.argv[2]
d = json.load(open(src, encoding='utf-8'))

NOON='ن'; BA='ب'
SMALL_MEEMS=set('ۭۢ')
TANWEEN=set('ًٌٍ')
SUKUN=set('ْۡ')
SMALL_MEEM='ۢ'
# marks that can sit on a letter (harakat, shadda, quranic annotation signs)
def is_mark(c):
    import unicodedata
    return unicodedata.category(c) in ('Mn','Mc','Me') or c in 'ـ'

def letters(word):
    """list of (base_letter, set_of_marks)"""
    res=[]
    for c in word:
        if is_mark(c) and res:
            res[-1][1].add(c)
        elif not is_mark(c):
            res.append([c,set()])
    return res

# Method A: small meem sign
def method_a(verse):
    return verse.count('\u06E2')+verse.count('\u06ED')

# Method B: rule-based, within an ayah, across words and inside words
def method_b(verse):
    words=verse.split()
    L=[letters(w) for w in words]
    sites=[]
    for wi,w in enumerate(L):
        for li,(ch,marks) in enumerate(w):
            has_short = bool(marks & set('\u064E\u064F\u0650'))
            sakin_noon = ch==NOON and not has_short and not (marks & set('\u0651')) and ((marks & SUKUN) or (bool(marks & SMALL_MEEMS)))
            tanween = bool(marks & TANWEEN) or (ch!=NOON and bool(marks & SMALL_MEEMS)) or (ch==NOON and has_short and bool(marks & SMALL_MEEMS))
            if not (sakin_noon or tanween): continue
            j=li+1
            # skip carrier alif of fathatan if it is the word-final letter
            if tanween and j==len(w)-1 and w[j][0]=='\u0627': j+=1
            nxt=None; same=True
            if j<len(w): nxt=w[j][0]
            elif wi+1<len(L) and L[wi+1]: nxt=L[wi+1][0][0]; same=False
            if nxt==BA:
                sites.append((wi+1, words[wi], words[wi+1] if not same else words[wi], 'tanween' if tanween else 'noon_sakinah', 'same_word' if same else 'cross_word'))
    return sites

rows=[]; mism=[]
for ch in d:
    for v in ch['verses']:
        a=method_a(v['text']); b=method_b(v['text'])
        if a or b:
            rows.append(dict(surah=ch['id'],ayah=v['id'],text=v['text'],a=a,b=b))
        if a!=len(b): mism.append((ch['id'],v['id'],a,len(b)))
json.dump(rows,open(out,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
print('ayahs flagged:',len(rows))
print('total sites A:',sum(r['a'] for r in rows),' total sites B:',sum(len(r['b']) for r in rows))
print('mismatches:',len(mism)); print(mism[:40])
