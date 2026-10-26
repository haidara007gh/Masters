#!/usr/bin/env python3
"""Download ayah-level recitations, convert to 16 kHz mono WAV, build recordings.csv.

Usage (run from the Dataset folder):
    python scripts/fetch_audio.py --target iqlab --limit 10

Needs: Python 3.8+ and ffmpeg. ffmpeg is taken from PATH if present; otherwise from the
pip package imageio-ffmpeg (python -m pip install imageio-ffmpeg), which bundles a binary.

Layout produced:
    audio_raw/<reciter_folder>/SSSAAA.mp3     cached downloads (re-runs skip these)
    audio/SSS/AAA/<speaker_id>.wav            16 kHz, mono, 16-bit (grouped by surah, then ayah)
    manifest/recordings.csv                   one row per recording
"""
import argparse, csv, subprocess, sys, time, urllib.request, urllib.error, wave, shutil
from pathlib import Path

# speaker_id -> folder name on EveryAyah. Folder names must be checked against the
# reciter list on everyayah.com; a wrong name shows up as HTTP 404 in the report.
RECITERS = {
    "alafasy": "Alafasy_128kbps",
    "husary": "Husary_128kbps",
    "minshawy": "Minshawy_Murattal_128kbps",
    "hudhaify": "Hudhaify_128kbps",
}
DEFAULT_BASE = "https://everyayah.com/data"
FIELDS = ["tajweed_target", "surah", "ayah", "speaker_id", "audio", "ayah_uthmani",
          "phoneme_ref", "phoneme_realized", "source_url", "duration_s"]


def download(url, dest, tries=3):
    if dest.exists() and dest.stat().st_size > 0:
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    err = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (dataset-research)"})
            with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
                shutil.copyfileobj(r, f)
            if dest.stat().st_size == 0:
                raise IOError("empty file")
            return None
        except urllib.error.HTTPError as e:
            err = f"HTTP {e.code}"
            if e.code in (403, 404):
                break
        except Exception as e:  # network hiccup
            err = repr(e)
        time.sleep(2 * (i + 1))
    if dest.exists():
        dest.unlink()
    return err


def find_ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


FFMPEG = None


def to_wav(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-i", str(src),
           "-ac", "1", "-ar", "16000", "-sample_fmt", "s16", str(dst)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        return None, p.stderr.strip()[:200]
    with wave.open(str(dst), "rb") as w:
        return round(w.getnframes() / w.getframerate(), 2), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="iqlab", help="data/<target>_dataset.csv")
    ap.add_argument("--limit", type=int, default=10, help="first N ayahs in Quran order")
    ap.add_argument("--base-url", default=DEFAULT_BASE)
    ap.add_argument("--root", default=".")
    ap.add_argument("--reciters", nargs="*", default=list(RECITERS), help="speaker ids")
    a = ap.parse_args()

    global FFMPEG
    FFMPEG = find_ffmpeg()
    if FFMPEG is None:
        sys.exit("ffmpeg not found. Run:  python -m pip install imageio-ffmpeg")
    print("using ffmpeg:", FFMPEG)

    root = Path(a.root)
    src = root / "data" / f"{a.target}_dataset.csv"
    ayahs = list(csv.DictReader(open(src, encoding="utf-8-sig")))
    ayahs.sort(key=lambda r: (int(r["surah"]), int(r["ayah"])))
    ayahs = ayahs[: a.limit]
    print(f"{len(ayahs)} ayahs x {len(a.reciters)} reciters = {len(ayahs) * len(a.reciters)} recordings")

    rows, failures = [], []
    for spk in a.reciters:
        folder = RECITERS[spk]
        for r in ayahs:
            code = f"{int(r['surah']):03d}{int(r['ayah']):03d}"
            url = f"{a.base_url}/{folder}/{code}.mp3"
            raw = root / "audio_raw" / folder / f"{code}.mp3"
            wav = root / "audio" / f"{int(r['surah']):03d}" / f"{int(r['ayah']):03d}" / f"{spk}.wav"
            old_wav = root / "audio" / spk / f"{code}.wav"  # previous layout: audio/<speaker>/SSSAAA.wav
            err = download(url, raw)
            dur = None
            if err is None:
                if old_wav.exists() and not wav.exists():
                    wav.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(old_wav), str(wav))
                    with wave.open(str(wav), "rb") as w_:
                        dur = round(w_.getnframes() / w_.getframerate(), 2)
                else:
                    dur, err = to_wav(raw, wav)
            if err:
                failures.append((spk, code, err))
                print(f"  FAIL {spk} {code}: {err}")
                continue
            rows.append({
                "tajweed_target": r["tajweed_target"], "surah": r["surah"], "ayah": r["ayah"],
                "speaker_id": spk, "audio": str(wav.relative_to(root)),
                "ayah_uthmani": r["ayah_uthmani"], "phoneme_ref": r["phoneme_ref"],
                "phoneme_realized": "",  # not annotated; training uses phoneme_ref
                "source_url": url, "duration_s": dur,
            })
        print(f"{spk}: done")

    for spk in a.reciters:  # tidy up the old per-reciter folders if they are now empty
        try:
            (root / "audio" / spk).rmdir()
        except OSError:
            pass
    rows.sort(key=lambda x: (int(x["surah"]), int(x["ayah"]), x["speaker_id"]))
    out = root / "manifest" / "recordings.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {out}  ({len(rows)} rows, {len(failures)} failures)")
    if failures:
        print("Failures (check reciter folder names on everyayah.com):")
        for f_ in failures:
            print("  ", *f_)
        sys.exit(1)


if __name__ == "__main__":
    main()
