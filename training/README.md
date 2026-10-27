# Phoneme CTC fine-tuning (pilot)

Fine-tunes XLS-R with CTC on `phoneme_ref`, following **Hafs2Vec** (Ahmed Ibrahim, ArabicNLP 2025), whose
author also wrote the Quranic Phonemizer used for our labels.

## Files
| File | Purpose |
|---|---|
| `finetune_colab.ipynb` | Colab notebook: upload it to Colab, set `DATASET`, run top to bottom |
| `train_ctc.py` | The training script (embedded in the notebook) |
| `vocab.json` | 68 Hafs phonemes + `<blank>` (id 0) + `<unk>`, built from all 6,236 ayahs |
| `evaluate_ctc.py` | Scores an already-trained model on any split (e.g. `--split train`), no training |
| `make_notebook.py` | Regenerates the notebook after editing `train_ctc.py`, `evaluate_ctc.py` or `vocab.json` |

## What follows the paper
- wav2vec2 XLS-R + CTC on Tajweed-aware phonemes from the Quranic Phonemizer
- AdamW, linear schedule with warm-up ratio 0.1, mixed precision, greedy CTC decoding
- PER reported with substitution / deletion / insertion rates, on speakers unseen in training

## What differs (and why)
| | Hafs2Vec | Pilot | Why |
|---|---|---|---|
| Model | xls-r-1b | xls-r-300m (`--model` to change) | 1b does not fit a free T4; paper reports 1b is ~1.3 PER points better |
| Data | ~170 h (28 reciters + IqraEval) | ~12 min train, 3 reciters, 10 ayahs | pilot to prove the pipeline |
| Max clip length | 10 s | 60 s | only 3 of our 40 clips are under 10 s |
| LR / epochs | 3e-5 / 15 | 1e-4 / 60 | tiny data needs more passes |
| Effective batch | 352 | 8 (2 x 4 accumulation) | one GPU, long clips |
| Extra metric | MDD (needs error annotations) | accuracy on the Iqlab nasal `m̃` | no `phoneme_realized` yet |

## Outputs (in `--output_dir`)
`summary.json` (PER, sub/del/ins, `acc[m̃]`), `predictions.csv` (per utterance: reference vs prediction),
and `final/` (model, feature extractor config, vocab).

## Expectations for the pilot
With ~30 training clips, expect a high test PER: CTC models first learn to output nothing. That is fine;
the goal is a working pipeline. Sanity check without retraining:
`python evaluate_ctc.py --model_dir <run>/final --dataset <dataset> --split train`. Training PER well below 100%
means the model learned the training voices.

The final model is chosen by `--select_best`: `loss` (default, lowest eval loss), `per`, or `last`. Selecting by
PER keeps the earliest epoch on ties, so a run stuck at PER 100 would keep the epoch-1 model. Scale up next by fetching more Iqlab ayahs (`fetch_audio.py --limit`).

## Tested
Locally on CPU with a tiny randomly-initialised wav2vec2 and stand-in audio (transformers 5.21, datasets 5.1,
accelerate 1.15): training, per-epoch evaluation, best-checkpoint selection, predictions, saving and reloading
all work. Not yet run on a GPU or with the real XLS-R weights.
