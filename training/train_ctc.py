#!/usr/bin/env python3
"""Fine-tune wav2vec2 / XLS-R with CTC on phoneme sequences (`phoneme_ref`).

Follows the recipe of Hafs2Vec (Ibrahim, 2025, ArabicNLP): XLS-R + CTC on Tajweed-aware phonemes from the
Quranic Phonemizer, AdamW, linear warm-up (ratio 0.1), mixed precision, greedy decoding, evaluated with PER
broken into substitutions / deletions / insertions. Differences for this pilot are listed in the README.

Typical Colab run:
    python train_ctc.py --dataset <user>/quran-tajweed-iqlab-pilot --output_dir /content/run1

Audio is decoded with soundfile from the stored WAV bytes, so torchcodec is not needed.
"""
import argparse, csv, io, json, os, random, sys
from pathlib import Path

import numpy as np

BLANK, UNK = "<blank>", "<unk>"


# --------------------------------------------------------------------------- PER with S/D/I
def align(ref, hyp):
    """Levenshtein alignment of two token lists. Returns (ops, S, D, I) where ops is a list of
    (op, ref_token, hyp_token) with op in {'=', 'S', 'D', 'I'}."""
    n, m = len(ref), len(hyp)
    d = np.zeros((n + 1, m + 1), dtype=np.int32)
    d[:, 0] = np.arange(n + 1)
    d[0, :] = np.arange(m + 1)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i, j] = min(d[i - 1, j] + 1, d[i, j - 1] + 1, d[i - 1, j - 1] + (ref[i - 1] != hyp[j - 1]))
    ops, i, j = [], n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and d[i, j] == d[i - 1, j - 1] + (ref[i - 1] != hyp[j - 1]):
            ops.append(("=" if ref[i - 1] == hyp[j - 1] else "S", ref[i - 1], hyp[j - 1])); i -= 1; j -= 1
        elif i > 0 and d[i, j] == d[i - 1, j] + 1:
            ops.append(("D", ref[i - 1], None)); i -= 1
        else:
            ops.append(("I", None, hyp[j - 1])); j -= 1
    ops.reverse()
    S = sum(o[0] == "S" for o in ops); D = sum(o[0] == "D" for o in ops); I = sum(o[0] == "I" for o in ops)
    return ops, S, D, I


def per_report(refs, hyps, focus=()):
    """Corpus-level PER (%) with substitution / deletion / insertion rates, plus per-token accuracy for
    `focus` tokens (how often a reference focus phoneme was recognised as itself)."""
    N = S = D = I = 0
    hit = {t: 0 for t in focus}; tot = {t: 0 for t in focus}
    for r, h in zip(refs, hyps):
        ops, s, dl, ins = align(r, h)
        N += len(r); S += s; D += dl; I += ins
        for op, rt, ht in ops:
            if rt in tot:
                tot[rt] += 1
                hit[rt] += (op == "=")
    pct = lambda x: round(100.0 * x / max(N, 1), 2)
    out = {"per": pct(S + D + I), "sub": pct(S), "del": pct(D), "ins": pct(I), "ref_phonemes": N}
    for t in focus:
        out[f"acc[{t}]"] = round(100.0 * hit[t] / tot[t], 2) if tot[t] else None
        out[f"count[{t}]"] = tot[t]
    return out


# --------------------------------------------------------------------------- vocab
def load_or_build_vocab(path, texts):
    if path and Path(path).exists():
        vocab = json.load(open(path, encoding="utf-8"))
    else:
        vocab = {BLANK: 0, UNK: 1}
        for t in sorted({t for s in texts for t in s.split()}):
            vocab[t] = len(vocab)
    assert vocab.get(BLANK) == 0, "blank must have id 0"
    unseen = sorted({t for s in texts for t in s.split()} - set(vocab))
    if unseen:
        print(f"warning: {len(unseen)} phoneme(s) not in vocab, mapped to {UNK}: {unseen[:10]}")
    return vocab


def encode(text, vocab):
    unk = vocab[UNK]
    return [vocab.get(t, unk) for t in text.split()]


def ctc_greedy(ids, inv, blank=0):
    """Collapse repeats, drop blanks. `ids` may contain -100 padding (treated as blank)."""
    out, prev = [], None
    for i in ids:
        i = int(i)
        if i < 0:
            i = blank
        if i != prev and i != blank:
            out.append(inv.get(i, UNK))
        prev = i
    return out


# --------------------------------------------------------------------------- audio
def decode_audio(a):
    import soundfile as sf
    if a.get("bytes"):
        wav, sr = sf.read(io.BytesIO(a["bytes"]), dtype="float32")
    else:
        wav, sr = sf.read(a["path"], dtype="float32")
    if wav.ndim > 1:
        wav = wav.mean(axis=1)
    if sr != 16000:
        raise ValueError(f"expected 16 kHz audio, got {sr} Hz")
    return wav


class Collator:
    def __init__(self, fe, vocab):
        self.fe, self.vocab = fe, vocab

    def __call__(self, rows):
        import torch
        audio = [decode_audio(r["audio"]) for r in rows]
        batch = self.fe(audio, sampling_rate=16000, padding=True, return_attention_mask=True, return_tensors="pt")
        labs = [encode(r["phoneme_ref"], self.vocab) for r in rows]
        L = max(len(x) for x in labs)
        lab = torch.full((len(labs), L), -100, dtype=torch.long)
        for k, x in enumerate(labs):
            lab[k, : len(x)] = torch.tensor(x, dtype=torch.long)
        batch["labels"] = lab
        return batch


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", required=True, help="HF dataset id, or a folder saved with save_to_disk")
    ap.add_argument("--model", default="facebook/wav2vec2-xls-r-300m",
                    help="pretrained checkpoint. Hafs2Vec used facebook/wav2vec2-xls-r-1b (needs an A100-class GPU)")
    ap.add_argument("--vocab", default=str(Path(__file__).with_name("vocab.json")))
    ap.add_argument("--output_dir", default="run")
    ap.add_argument("--train_split", default="train")
    ap.add_argument("--eval_split", default="test")
    ap.add_argument("--epochs", type=float, default=60, help="Hafs2Vec: 15 (on ~170 h of data)")
    ap.add_argument("--max_steps", type=int, default=-1, help="overrides --epochs when > 0 (for smoke tests)")
    ap.add_argument("--lr", type=float, default=1e-4, help="Hafs2Vec: 3e-5 (much more data than this pilot)")
    ap.add_argument("--warmup_ratio", type=float, default=0.1)
    ap.add_argument("--batch_size", type=int, default=2, help="per device; long ayahs (up to ~50 s) need small batches on a T4")
    ap.add_argument("--grad_accum", type=int, default=4, help="effective batch = batch_size x grad_accum (Hafs2Vec: 352)")
    ap.add_argument("--max_duration", type=float, default=60.0,
                    help="drop clips longer than this many seconds (Hafs2Vec: 10)")
    ap.add_argument("--focus", nargs="*", default=["m̃"], help="phonemes to report recognition accuracy for")
    ap.add_argument("--no_gradient_checkpointing", action="store_true")
    ap.add_argument("--hub_model_id", default=None, help="push the final model to this HF repo (optional)")
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()

    import torch
    from datasets import load_dataset, load_from_disk, Audio
    from transformers import (Wav2Vec2FeatureExtractor, Wav2Vec2ForCTC, Trainer, TrainingArguments,
                              set_seed)
    set_seed(a.seed); random.seed(a.seed)

    dd = load_from_disk(a.dataset) if os.path.isdir(a.dataset) else load_dataset(a.dataset)
    for s in (a.train_split, a.eval_split):
        if s not in dd:
            sys.exit(f"split '{s}' not in dataset (have: {list(dd)})")
    dd = dd.cast_column("audio", Audio(decode=False))

    def keep(ex):
        return ex["duration_s"] is None or ex["duration_s"] <= a.max_duration
    for s in (a.train_split, a.eval_split):
        before = len(dd[s]); dd[s] = dd[s].filter(keep)
        print(f"{s}: {len(dd[s])}/{before} clips <= {a.max_duration}s, "
              f"{sum(list(dd[s]['duration_s'])) / 60:.1f} min, speakers={sorted(set(list(dd[s]['speaker_id'])))}")
        if len(dd[s]) == 0:
            sys.exit(f"no clips left in '{s}'; raise --max_duration")

    vocab = load_or_build_vocab(a.vocab, list(dd[a.train_split]["phoneme_ref"]) + list(dd[a.eval_split]["phoneme_ref"]))
    inv = {i: t for t, i in vocab.items()}
    print(f"vocab: {len(vocab)} symbols")

    fe = Wav2Vec2FeatureExtractor(feature_size=1, sampling_rate=16000, padding_value=0.0,
                                  do_normalize=True, return_attention_mask=True)
    model = Wav2Vec2ForCTC.from_pretrained(
        a.model, vocab_size=len(vocab), pad_token_id=vocab[BLANK],
        ctc_loss_reduction="mean", ctc_zero_infinity=True, ignore_mismatched_sizes=True)
    model.freeze_feature_encoder()
    if not a.no_gradient_checkpointing:
        model.gradient_checkpointing_enable()

    def argmax_logits(logits, labels):
        return logits.argmax(-1)

    def metrics(p):
        pred_ids, label_ids = p.predictions, p.label_ids
        hyps = [ctc_greedy(x, inv) for x in pred_ids]
        refs = [[inv[int(i)] for i in row if i != -100] for row in label_ids]
        return per_report(refs, hyps, a.focus)

    cuda = torch.cuda.is_available()
    # bf16 only on GPUs with native support (compute capability 8+: A100, L4, H100). On a T4 (7.5),
    # torch.cuda.is_bf16_supported() can report emulated support, which is slower than fp16.
    bf16 = cuda and torch.cuda.get_device_capability()[0] >= 8
    import inspect
    accepted = inspect.signature(TrainingArguments.__init__).parameters
    kw = dict(
        output_dir=a.output_dir, per_device_train_batch_size=a.batch_size, per_device_eval_batch_size=a.batch_size,
        gradient_accumulation_steps=a.grad_accum, learning_rate=a.lr,
        num_train_epochs=a.epochs, max_steps=a.max_steps, optim="adamw_torch", lr_scheduler_type="linear",
        fp16=cuda and not bf16, bf16=bf16, save_strategy="epoch", save_total_limit=1,
        load_best_model_at_end=True, metric_for_best_model="per", greater_is_better=False,
        logging_steps=5, report_to="none", remove_unused_columns=False, dataloader_num_workers=2 if cuda else 0,
        seed=a.seed)
    # keyword names differ across transformers versions
    kw["eval_strategy" if "eval_strategy" in accepted else "evaluation_strategy"] = "epoch"
    if "warmup_ratio" in accepted:
        kw["warmup_ratio"] = a.warmup_ratio          # transformers 4.x
    else:
        kw["warmup_steps"] = a.warmup_ratio          # 5.x: a float in [0, 1) is a ratio
    args = TrainingArguments(**kw)
    trainer = Trainer(model=model, args=args, train_dataset=dd[a.train_split], eval_dataset=dd[a.eval_split],
                      data_collator=Collator(fe, vocab), compute_metrics=metrics,
                      preprocess_logits_for_metrics=argmax_logits)
    print(f"device: {torch.cuda.get_device_name(0) if cuda else 'cpu'}, precision: {'bf16' if bf16 else 'fp16' if cuda else 'fp32'}")
    trainer.train()

    # final evaluation with per-utterance predictions
    out = Path(a.output_dir); out.mkdir(parents=True, exist_ok=True)
    pred = trainer.predict(dd[a.eval_split])
    hyps = [ctc_greedy(x, inv) for x in pred.predictions]
    ev = dd[a.eval_split]
    refs = [r.split() for r in list(ev["phoneme_ref"])]
    summary = per_report(refs, hyps, a.focus)
    summary.update({"model": a.model, "train_clips": len(dd[a.train_split]), "eval_clips": len(ev),
                    "eval_split": a.eval_split})
    with open(out / "predictions.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "speaker_id", "surah", "ayah", "per", "sub", "del", "ins", "phoneme_ref", "phoneme_pred"])
        for k in range(len(ev)):
            _, s, d_, i_ = align(refs[k], hyps[k])
            w.writerow([ev[k]["id"], ev[k]["speaker_id"], ev[k]["surah"], ev[k]["ayah"],
                        round(100 * (s + d_ + i_) / max(len(refs[k]), 1), 2), s, d_, i_,
                        " ".join(refs[k]), " ".join(hyps[k])])
    json.dump(summary, open(out / "summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\nFINAL", json.dumps(summary, ensure_ascii=False))

    final = out / "final"
    trainer.save_model(str(final)); fe.save_pretrained(str(final))
    json.dump(vocab, open(final / "vocab.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"model, vocab, predictions.csv and summary.json saved in {out}")
    if a.hub_model_id:
        model.push_to_hub(a.hub_model_id, private=True); fe.push_to_hub(a.hub_model_id, private=True)
        from huggingface_hub import upload_file
        upload_file(path_or_fileobj=str(final / "vocab.json"), path_in_repo="vocab.json", repo_id=a.hub_model_id)
        print(f"pushed to https://huggingface.co/{a.hub_model_id}")


if __name__ == "__main__":
    main()
