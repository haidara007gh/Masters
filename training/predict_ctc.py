#!/usr/bin/env python3
"""Predict phonemes for your own recordings with a trained model, optionally compared with an ayah's reference.

    python predict_ctc.py recording.m4a --model_dir run/final
    python predict_ctc.py recording.wav --model_dir run/final --ayah 2:18
    python predict_ctc.py audio/002/018/*.wav --model_dir run/final --ayah auto --out predictions_mine.csv

--ayah S:A   builds the reference with the Quranic Phonemizer, using the dataset's settings (Hafs, closed-lip m̃
             for Iqlab, the ayah recited on its own with a stop at its end). Needs: pip install quranic-phonemizer==3.0.5
--ayah auto  reads the ayah from the file path: audio/SSS/AAA/<name>.wav or a SSSAAA number in the file name.
--ref "..."  gives the reference phonemes directly instead (space-separated).
--out f.csv  writes the results in predictions.csv format, so the Phoneme Alignment Viewer can open them.

Any audio format ffmpeg can read works (wav, mp3, m4a, ogg, flac...). Audio is converted to 16 kHz mono.
"""
import argparse, csv, json, re, shutil, subprocess, sys, unicodedata
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from train_ctc import align, ctc_greedy, per_report  # noqa: E402


# --------------------------------------------------------------------------- audio
def find_ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def load_audio(path, ffmpeg):
    """Return float32 mono samples at 16 kHz."""
    if ffmpeg:
        cmd = [ffmpeg, "-nostdin", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"]
        p = subprocess.run(cmd, capture_output=True)
        if p.returncode != 0:
            raise ValueError(f"ffmpeg could not read {path}: {p.stderr.decode(errors='replace').strip()[:200]}")
        return np.frombuffer(p.stdout, dtype=np.float32)
    import soundfile as sf                      # fallback without ffmpeg: wav / flac / ogg
    wav, sr = sf.read(str(path), dtype="float32")
    if wav.ndim > 1:
        wav = wav.mean(axis=1)
    if sr != 16000:
        from math import gcd
        from scipy.signal import resample_poly
        g = gcd(sr, 16000)
        wav = resample_poly(wav, 16000 // g, sr // g).astype(np.float32)
    return wav


# --------------------------------------------------------------------------- reference
_phonemizer = None


def reference_for(ayah):
    """Phonemes of one ayah with the same settings the dataset was built with."""
    global _phonemizer
    if _phonemizer is None:
        try:
            from quranic_phonemizer import Phonemizer
        except ImportError:
            sys.exit("--ayah needs the phonemizer:  pip install quranic-phonemizer==3.0.5   (or pass --ref)")
        _phonemizer = Phonemizer(variants={"iqlab_nasal": "closed"})
    return " ".join(_phonemizer.analyse(ayah).phonemes())


def ayah_from_path(path):
    parts = Path(path).parts
    if len(parts) >= 3 and re.fullmatch(r"\d{3}", parts[-3]) and re.fullmatch(r"\d{3}", parts[-2]):
        return f"{int(parts[-3])}:{int(parts[-2])}"           # audio/SSS/AAA/<reciter>.wav
    m = re.search(r"(?<!\d)(\d{3})(\d{3})(?!\d)", Path(path).stem)
    return f"{int(m.group(1))}:{int(m.group(2))}" if m else None  # ..._002018.wav


# --------------------------------------------------------------------------- display
def width(s):
    return sum(0 if unicodedata.combining(c) else 1 for c in s)


def pad(s, w):
    return s + " " * (w - width(s))


def side_by_side(ops, line=96):
    """Three text rows per block: reference, prediction, and a marker row (S, D, I)."""
    blocks, cur, used = [], [[], [], []], 0
    for op, r, h in ops:
        top, bot = (r if r is not None else "+"), (h if h is not None else "-")
        mark = {"=": "", "S": "S", "D": "D", "I": "I"}[op]
        w = max(width(top), width(bot), 1)
        if used + w + 1 > line and cur[0]:
            blocks.append(cur); cur, used = [[], [], []], 0
        cur[0].append(pad(top, w)); cur[1].append(pad(bot, w)); cur[2].append(pad(mark, w)); used += w + 1
    if cur[0]:
        blocks.append(cur)
    out = []
    for b in blocks:
        out += ["  ref  " + " ".join(b[0]), "  pred " + " ".join(b[1]), "       " + " ".join(b[2]).rstrip(), ""]
    return "\n".join(out)


# --------------------------------------------------------------------------- reusable steps (also used by notebook step 10)
def load_model(model_dir):
    """Load model, feature extractor and vocabulary once; returns a dict passed to transcribe()."""
    import torch
    from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2ForCTC
    md = Path(model_dir)
    vocab = json.load(open(md / "vocab.json", encoding="utf-8"))
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    return {"model": Wav2Vec2ForCTC.from_pretrained(str(md)).to(dev).eval(),
            "fe": Wav2Vec2FeatureExtractor.from_pretrained(str(md)),
            "inv": {i: t for t, i in vocab.items()}, "dev": dev}


def transcribe(wav, m):
    """16 kHz mono samples -> list of predicted phonemes (greedy CTC)."""
    import torch
    x = m["fe"](wav, sampling_rate=16000, return_attention_mask=True, return_tensors="pt")
    with torch.no_grad():
        ids = m["model"](input_values=x["input_values"].to(m["dev"]),
                         attention_mask=x["attention_mask"].to(m["dev"])).logits.argmax(-1)[0]
    return ctc_greedy(ids.cpu().tolist(), m["inv"])


def report(name, wav, ayah, ref, hyp):
    """Print the prediction, and the aligned comparison when there is a reference."""
    print(f"\n=== {name}  ({len(wav) / 16000:.1f} s{', ayah ' + ayah if ayah else ''})")
    if ref is None:
        print("predicted:", " ".join(hyp) if hyp else "(nothing: the model output only blanks)")
        return
    ops, s, d, i = align(ref, hyp)
    per = 100 * (s + d + i) / max(len(ref), 1)
    print(f"PER {per:.1f}%   {s} substitutions, {d} deletions, {i} insertions, {len(ref)} reference phonemes")
    print(side_by_side(ops))


def result_row(name, speaker, ayah, ref, hyp):
    sa = (ayah or "0:0").split(":")
    return {"id": Path(name).stem, "speaker_id": speaker or Path(name).stem, "surah": sa[0], "ayah": sa[1],
            "ref": ref, "hyp": hyp}


def write_csv(results, path):
    """Write results in predictions.csv format (opens in the Phoneme Alignment Viewer)."""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "speaker_id", "surah", "ayah", "per", "sub", "del", "ins", "phoneme_ref", "phoneme_pred"])
        for r in results:
            if r["ref"] is None:
                w.writerow([r["id"], r["speaker_id"], r["surah"], r["ayah"], "", "", "", "", "", " ".join(r["hyp"])])
            else:
                _, s, d, i = align(r["ref"], r["hyp"])
                w.writerow([r["id"], r["speaker_id"], r["surah"], r["ayah"], round(100 * (s + d + i) / max(len(r["ref"]), 1), 2),
                            s, d, i, " ".join(r["ref"]), " ".join(r["hyp"])])


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio", nargs="+", help="one or more audio files")
    ap.add_argument("--model_dir", required=True, help="the final/ folder written by train_ctc.py")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--ayah", help="S:A (e.g. 2:18), or 'auto' to read it from each file path")
    g.add_argument("--ref", help="reference phonemes, space-separated")
    ap.add_argument("--speaker", default="", help="speaker id to write in --out (default: the file name)")
    ap.add_argument("--focus", nargs="*", default=["m̃"], help="phonemes to report accuracy for")
    ap.add_argument("--out", help="write results to this CSV (predictions.csv format)")
    a = ap.parse_args()

    m = load_model(a.model_dir)
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("note: ffmpeg not found; only wav/flac/ogg can be read (pip install imageio-ffmpeg for other formats)")

    results, refs, hyps = [], [], []
    for path in a.audio:
        wav = load_audio(path, ffmpeg)
        hyp = transcribe(wav, m)
        ayah = ayah_from_path(path) if a.ayah == "auto" else a.ayah
        if a.ayah == "auto" and not ayah:
            print(f"warning: could not read an ayah from '{path}'; showing the prediction only")
        ref = a.ref.split() if a.ref else (reference_for(ayah).split() if ayah else None)
        report(path, wav, ayah, ref, hyp)
        if ref is not None:
            refs.append(ref); hyps.append(hyp)
        results.append(result_row(path, a.speaker, ayah, ref, hyp))

    if len(refs) > 1:
        print("OVERALL", json.dumps(per_report(refs, hyps, a.focus), ensure_ascii=False))
    if a.out:
        write_csv(results, a.out)
        print(f"wrote {a.out} (open it in the Phoneme Alignment Viewer)")


if __name__ == "__main__":
    main()
