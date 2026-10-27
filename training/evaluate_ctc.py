#!/usr/bin/env python3
"""Evaluate an already-trained CTC model on any split, without training.

    python evaluate_ctc.py --model_dir run/final --dataset <user>/quran-tajweed-iqlab-pilot --split train

Writes predictions_<split>.csv and summary_<split>.json next to the model folder (or in --output_dir).
Uses the same decoding and scoring as train_ctc.py, so the numbers are directly comparable.
"""
import argparse, csv, json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from train_ctc import Collator, align, ctc_greedy, per_report  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model_dir", required=True, help="the final/ folder written by train_ctc.py")
    ap.add_argument("--dataset", required=True, help="HF dataset id, or a folder saved with save_to_disk")
    ap.add_argument("--split", default="train", help="split to score, e.g. train or test")
    ap.add_argument("--output_dir", default=None, help="default: the folder that contains --model_dir")
    ap.add_argument("--batch_size", type=int, default=4)
    ap.add_argument("--focus", nargs="*", default=["m̃"])
    a = ap.parse_args()

    import torch
    from datasets import load_dataset, load_from_disk, Audio
    from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2ForCTC

    md = Path(a.model_dir)
    vocab = json.load(open(md / "vocab.json", encoding="utf-8"))
    inv = {i: t for t, i in vocab.items()}
    fe = Wav2Vec2FeatureExtractor.from_pretrained(str(md))
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = Wav2Vec2ForCTC.from_pretrained(str(md)).to(dev).eval()

    dd = load_from_disk(a.dataset) if os.path.isdir(a.dataset) else load_dataset(a.dataset)
    if a.split not in dd:
        sys.exit(f"split '{a.split}' not in dataset (have: {list(dd)})")
    ds = dd[a.split].cast_column("audio", Audio(decode=False))
    collate = Collator(fe, vocab)
    print(f"scoring {len(ds)} clips from '{a.split}' with {md} on {dev}")

    refs, hyps, rows = [], [], []
    for start in range(0, len(ds), a.batch_size):
        chunk = [ds[k] for k in range(start, min(start + a.batch_size, len(ds)))]
        batch = collate(chunk)
        with torch.no_grad():
            logits = model(input_values=batch["input_values"].to(dev),
                           attention_mask=batch["attention_mask"].to(dev)).logits
        for r, ids in zip(chunk, logits.argmax(-1).cpu().tolist()):
            ref, hyp = r["phoneme_ref"].split(), ctc_greedy(ids, inv)
            refs.append(ref); hyps.append(hyp); rows.append(r)

    summary = per_report(refs, hyps, a.focus)
    summary.update({"model_dir": str(md), "split": a.split, "clips": len(rows)})
    out = Path(a.output_dir) if a.output_dir else md.parent
    out.mkdir(parents=True, exist_ok=True)
    with open(out / f"predictions_{a.split}.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "speaker_id", "surah", "ayah", "per", "sub", "del", "ins", "phoneme_ref", "phoneme_pred"])
        for r, ref, hyp in zip(rows, refs, hyps):
            _, s, d, i = align(ref, hyp)
            w.writerow([r["id"], r["speaker_id"], r["surah"], r["ayah"], round(100 * (s + d + i) / max(len(ref), 1), 2),
                        s, d, i, " ".join(ref), " ".join(hyp)])
    json.dump(summary, open(out / f"summary_{a.split}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("RESULT", json.dumps(summary, ensure_ascii=False))
    print(f"wrote {out / f'predictions_{a.split}.csv'} and {out / f'summary_{a.split}.json'}")


if __name__ == "__main__":
    main()
