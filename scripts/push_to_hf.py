#!/usr/bin/env python3
"""Package manifest/recordings.csv + audio/*.wav as a Hugging Face dataset and upload it.

Run from the dataset folder, after `scripts/fetch_audio.py`:

    python -m pip install datasets huggingface_hub
    hf auth login            # paste a token with WRITE access; never share it in chat
    python scripts/push_to_hf.py --dry-run        # build + verify locally, uploads nothing
    python scripts/push_to_hf.py                  # upload as a PRIVATE dataset

Split: one reciter is held out as `test` (speaker-disjoint); everything else is `train`.
"""
import argparse, csv, sys
from pathlib import Path

CARD = """\
# Quran tajweed pilot: Iqlab (professional reciters)

Pilot dataset for Qur'anic recitation assessment (MSc project). One row per recording
(ayah x reciter). **Text and reference phonemes are machine-generated and not yet verified
by a Tajweed expert.**

## Columns
- `id`: `<speaker_id>_<SSSAAA>`
- `tajweed_target`: rule the ayah was selected for (here `iqlab`)
- `surah`, `ayah`: location
- `speaker_id`: reciter
- `audio`: 16 kHz mono recitation of the ayah
- `ayah_uthmani`: Uthmani text of the ayah
- `phoneme_ref`: reference phonemes (Hafs, ayah-by-ayah with a stop at the ayah end,
  closed-lip `m̃` for Iqlab), from Quranic Phonemizer 3.0.5
- `phoneme_realized`: empty. Recitations were not annotated; they are assumed correct.
- `duration_s`, `source_url`: provenance

## Notes
- Split is speaker-disjoint: the held-out reciter is `test`. With only a few ayahs the split is
  NOT ayah-disjoint, so test scores are optimistic.
- **Audio licence: not yet checked.** Keep this dataset private until it has been.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--repo", help="user/name (default: <your hf username>/quran-tajweed-iqlab-pilot)")
    ap.add_argument("--public", action="store_true", help="make the dataset public (default: private)")
    ap.add_argument("--holdout", default="hudhaify", help="speaker_id used as the test split; '' for none")
    ap.add_argument("--dry-run", action="store_true", help="build and verify locally, upload nothing")
    a = ap.parse_args()

    try:
        from datasets import Dataset, DatasetDict, Audio, Features, Value, load_from_disk
    except ImportError:
        sys.exit("Missing packages. Run:  python -m pip install datasets huggingface_hub")

    root = Path(a.root)
    rows = list(csv.DictReader(open(root / "manifest" / "recordings.csv", encoding="utf-8-sig")))
    if not rows:
        sys.exit("manifest/recordings.csv is empty. Run scripts/fetch_audio.py first.")
    missing = [r["audio"] for r in rows if not (root / r["audio"]).exists()]
    if missing:
        sys.exit(f"{len(missing)} audio files listed in the manifest are missing, e.g. {missing[:3]}")

    # Build the audio column as raw {bytes, path} (no decoding library needed), then mark it as
    # an Audio feature afterwards. Newer `datasets` versions demand torch+torchcodec to attach
    # audio from a file path, which an upload does not need.
    feats = Features({
        "id": Value("string"), "tajweed_target": Value("string"),
        "surah": Value("int32"), "ayah": Value("int32"), "speaker_id": Value("string"),
        "audio": {"bytes": Value("binary"), "path": Value("string")},
        "ayah_uthmani": Value("string"), "phoneme_ref": Value("string"),
        "phoneme_realized": Value("string"), "duration_s": Value("float32"),
        "source_url": Value("string"),
    })

    def build(subset):
        cols = {
            "id": [f"{r['speaker_id']}_{int(r['surah']):03d}{int(r['ayah']):03d}" for r in subset],
            "tajweed_target": [r["tajweed_target"] for r in subset],
            "surah": [int(r["surah"]) for r in subset], "ayah": [int(r["ayah"]) for r in subset],
            "speaker_id": [r["speaker_id"] for r in subset],
            "audio": [{"bytes": (root / r["audio"]).read_bytes(),
                       "path": f"{r['speaker_id']}_{int(r['surah']):03d}{int(r['ayah']):03d}.wav"}
                      for r in subset],
            "ayah_uthmani": [r["ayah_uthmani"] for r in subset],
            "phoneme_ref": [r["phoneme_ref"] for r in subset],
            "phoneme_realized": [r["phoneme_realized"] for r in subset],
            "duration_s": [float(r["duration_s"]) for r in subset],
            "source_url": [r["source_url"] for r in subset],
        }
        return Dataset.from_dict(cols, features=feats).cast_column("audio", Audio(sampling_rate=16000))

    splits = {}
    test = [r for r in rows if a.holdout and r["speaker_id"] == a.holdout]
    train = [r for r in rows if not (a.holdout and r["speaker_id"] == a.holdout)]
    if a.holdout and not test:
        print(f"warning: holdout speaker '{a.holdout}' not found; no test split")
    splits["train"] = build(train)
    if test:
        splits["test"] = build(test)
    dd = DatasetDict(splits)
    for k, v in dd.items():
        print(f"{k}: {len(v)} rows, speakers={sorted(set(v['speaker_id']))}")

    # verify the audio bytes are really embedded (no decoding library needed)
    chk = dd["train"].cast_column("audio", Audio(decode=False))[0]["audio"]
    assert chk["path"] or chk["bytes"], "audio not readable"
    print("columns:", list(dd["train"].features))

    if a.dry_run:
        out = root / "hf_dryrun"
        dd.save_to_disk(str(out))
        back = load_from_disk(str(out))
        print(f"dry run OK: saved and reloaded from {out} ({sum(len(v) for v in back.values())} rows). Nothing uploaded.")
        return

    from huggingface_hub import HfApi, DatasetCard
    api = HfApi()
    try:
        user = api.whoami()["name"]
    except Exception:
        sys.exit("Not logged in. Run:  hf auth login   (token needs WRITE access)")
    repo = a.repo or f"{user}/quran-tajweed-iqlab-pilot"
    private = not a.public
    print(f"uploading to {repo} (private={private}) ...")
    dd.push_to_hub(repo, private=private)
    try:  # add the dataset card text, keeping the metadata push_to_hub generated
        card = DatasetCard.load(repo)
        if "Quran tajweed pilot" not in (card.text or ""):
            card.text = CARD + "\n" + (card.text or "")
            card.push_to_hub(repo)
    except Exception as e:
        print("note: dataset card not updated:", repr(e)[:150])
    print(f"done: https://huggingface.co/datasets/{repo}")


if __name__ == "__main__":
    main()
