#!/usr/bin/env python3
"""Build viewer.html: a local, searchable table of manifest/recordings.csv with an audio player per row.

Run from the dataset folder (no extra packages needed):
    python3 scripts/make_viewer.py
then double-click viewer.html (it must stay in the dataset folder so the audio paths resolve).
"""
import argparse, csv, json
from pathlib import Path

HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#f7f7f5;--panel:#fff;--ink:#1d1d1b;--mute:#6b6b66;--line:#e2e2dc;--accent:#0f6e56;--hl:#fde68a;--hlink:#7a4b00}
@media (prefers-color-scheme:dark){:root{--bg:#161615;--panel:#1f1f1d;--ink:#ecebe6;--mute:#9a9a93;--line:#33332f;--accent:#5dcaa5;--hl:#5a4a12;--hlink:#ffe9a8}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
header{padding:16px;border-bottom:1px solid var(--line);background:var(--panel)}
h1{font-size:17px;margin:0 0 10px;font-weight:600}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
input,select,button{font:inherit;color:inherit;background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:6px 9px}
input[type=search]{min-width:220px;flex:1}
button{cursor:pointer}button:disabled{opacity:.4;cursor:default}
.count{color:var(--mute);margin-left:auto}
.wrap{padding:16px;overflow-x:auto}
table{border-collapse:collapse;width:100%;min-width:900px;background:var(--panel);border:1px solid var(--line)}
th,td{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}
th{position:sticky;top:0;background:var(--panel);cursor:pointer;white-space:nowrap;font-weight:600;font-size:12px;color:var(--mute);user-select:none}
th.on{color:var(--accent)}
td.ar{direction:rtl;text-align:right;font:22px/1.9 "Geeza Pro","Amiri Quran","Scheherazade New","Noto Naskh Arabic",serif;min-width:300px;max-width:460px}
td.ph{font:12.5px/1.7 ui-monospace,SFMono-Regular,Menlo,monospace;min-width:280px;max-width:420px;word-spacing:2px}
td.meta{white-space:nowrap;color:var(--mute)}
.hl{background:var(--hl);color:var(--hlink);border-radius:3px;padding:0 2px;font-weight:600}
audio{height:34px;width:230px}
.pill{display:inline-block;padding:1px 8px;border-radius:99px;border:1px solid var(--line);font-size:12px}
.empty{padding:40px;text-align:center;color:var(--mute)}
</style></head><body>
<header>
  <h1>__TITLE__</h1>
  <div class="bar">
    <input id="q" type="search" placeholder="Search text, phonemes, id...">
    <select id="spk"><option value="">All reciters</option></select>
    <select id="sur"><option value="">All surahs</option></select>
    <select id="tgt"><option value="">All targets</option></select>
    <select id="ps"><option>25</option><option selected>50</option><option>100</option></select>
    <button id="prev">&larr;</button><span id="pg"></span><button id="next">&rarr;</button>
    <span class="count" id="cnt"></span>
  </div>
</header>
<div class="wrap"><table><thead><tr id="head"></tr></thead><tbody id="body"></tbody></table><div id="empty" class="empty" hidden>No rows match.</div></div>
<script>
const DATA = __DATA__;
const HL = new Set(__HL__);
const COLS = [
  ["audio","Audio",false],["surah","Surah:Ayah",true],["speaker_id","Reciter",true],["tajweed_target","Target",true],
  ["ayah_uthmani","Ayah (Uthmani)",true],["phoneme_ref","phoneme_ref",true],["phoneme_realized","phoneme_realized",true],["duration_s","Sec",true]
];
let sortKey="surah", sortDir=1, page=0;
const $=id=>document.getElementById(id);
const uniq=k=>[...new Set(DATA.map(r=>r[k]))].sort((a,b)=>String(a).localeCompare(String(b),undefined,{numeric:true}));
for (const [id,k] of [["spk","speaker_id"],["sur","surah"],["tgt","tajweed_target"]])
  uniq(k).forEach(v=>{const o=document.createElement("option");o.value=v;o.textContent=v;$(id).appendChild(o)});
$("head").innerHTML=COLS.map(([k,l,s])=>`<th data-k="${k}" class="${k===sortKey?'on':''}">${l}${k===sortKey?(sortDir>0?' ▲':' ▼'):''}</th>`).join("");
$("head").onclick=e=>{const k=e.target.dataset.k; if(!k||!COLS.find(c=>c[0]===k)[2])return; sortDir=(k===sortKey)?-sortDir:1; sortKey=k; page=0; draw()};
["q","spk","sur","tgt","ps"].forEach(id=>$(id).addEventListener("input",()=>{page=0;draw()}));
$("prev").onclick=()=>{page--;draw()}; $("next").onclick=()=>{page++;draw()};
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const hlPhon=s=>esc(s).split(" ").map(t=>HL.has(t)?`<span class="hl">${t}</span>`:t).join(" ");
function filtered(){
  const q=$("q").value.trim().toLowerCase(), sp=$("spk").value, su=$("sur").value, tg=$("tgt").value;
  let rows=DATA.filter(r=>(!sp||r.speaker_id===sp)&&(!su||String(r.surah)===su)&&(!tg||r.tajweed_target===tg)&&
    (!q||(r.id+" "+r.ayah_uthmani+" "+r.phoneme_ref+" "+r.speaker_id).toLowerCase().includes(q)));
  rows.sort((a,b)=>{let x=a[sortKey],y=b[sortKey];
    if(sortKey==="surah"){x=a.surah*1000+a.ayah;y=b.surah*1000+b.ayah}
    const c=(typeof x==="number"&&typeof y==="number")?x-y:String(x).localeCompare(String(y));
    return (c||a.speaker_id.localeCompare(b.speaker_id))*sortDir});
  return rows;
}
function draw(){
  const rows=filtered(), ps=+$("ps").value, pages=Math.max(1,Math.ceil(rows.length/ps));
  page=Math.min(Math.max(page,0),pages-1);
  const slice=rows.slice(page*ps,page*ps+ps);
  $("head").querySelectorAll("th").forEach(th=>{const on=th.dataset.k===sortKey;th.className=on?"on":"";
    const c=COLS.find(c=>c[0]===th.dataset.k);th.textContent=c[1]+(on?(sortDir>0?" ▲":" ▼"):"")});
  $("body").innerHTML=slice.map(r=>`<tr>
    <td><audio controls preload="none" src="${esc(r.audio)}"></audio></td>
    <td class="meta">${r.surah}:${r.ayah}</td><td><span class="pill">${esc(r.speaker_id)}</span></td>
    <td class="meta">${esc(r.tajweed_target)}</td>
    <td class="ar">${esc(r.ayah_uthmani)}</td><td class="ph">${hlPhon(r.phoneme_ref)}</td>
    <td class="ph">${r.phoneme_realized?hlPhon(r.phoneme_realized):'<span style="color:var(--mute)">—</span>'}</td>
    <td class="meta">${r.duration_s}</td></tr>`).join("");
  $("empty").hidden=rows.length>0;
  $("cnt").textContent=`${rows.length} of ${DATA.length} recordings`;
  $("pg").textContent=`${page+1} / ${pages}`; $("prev").disabled=page===0; $("next").disabled=page>=pages-1;
}
document.addEventListener("play",e=>{document.querySelectorAll("audio").forEach(a=>{if(a!==e.target)a.pause()})},true);
draw();
</script></body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--title", default="Quran tajweed dataset viewer")
    ap.add_argument("--highlight", nargs="*", default=["m̃", "ŋ", "ñ", "j̃", "w̃"],
                    help="phoneme tokens to highlight (default: the nasal / idgham tajweed phonemes)")
    a = ap.parse_args()
    root = Path(a.root)
    rows = list(csv.DictReader(open(root / "manifest" / "recordings.csv", encoding="utf-8-sig")))
    data = [{
        "id": f"{r['speaker_id']}_{int(r['surah']):03d}{int(r['ayah']):03d}",
        "surah": int(r["surah"]), "ayah": int(r["ayah"]), "speaker_id": r["speaker_id"],
        "tajweed_target": r["tajweed_target"], "audio": r["audio"],
        "ayah_uthmani": r["ayah_uthmani"], "phoneme_ref": r["phoneme_ref"],
        "phoneme_realized": r.get("phoneme_realized", ""), "duration_s": r.get("duration_s", ""),
    } for r in rows]
    page = (HTML.replace("__TITLE__", a.title)
                .replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
                .replace("__HL__", json.dumps(a.highlight, ensure_ascii=False)))
    out = root / "viewer.html"
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out} ({len(data)} rows). Open it in your browser.")


if __name__ == "__main__":
    main()
