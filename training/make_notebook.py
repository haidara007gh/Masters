#!/usr/bin/env python3
"""Regenerate finetune_colab.ipynb so it embeds the current train_ctc.py and vocab.json."""
import json
from pathlib import Path

here = Path(__file__).parent
script = (here / "train_ctc.py").read_text(encoding="utf-8")
vocab = (here / "vocab.json").read_text(encoding="utf-8")


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(keepends=True)}


def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": text.strip("\n").splitlines(keepends=True)}


cells = [
    md("""
# Phoneme CTC fine-tuning (pilot): Hafs2Vec recipe

Fine-tunes XLS-R with CTC on `phoneme_ref`, following Hafs2Vec (Ibrahim, 2025). Run the cells top to bottom.

**Before you start:** Runtime → Change runtime type → **GPU** (T4 is fine for the 300m model).
"""),
    code("!nvidia-smi --query-gpu=name,memory.total --format=csv"),
    md("## 1. Install\nVersions are pinned to the ones the script was tested with."),
    code("!pip install -q transformers==5.21.0 datasets==5.1.0 accelerate==1.15.0 soundfile"),
    md("## 2. Save results to Google Drive (recommended)\nColab deletes `/content` when the session ends. "
       "Mount Drive so the trained model and predictions survive. Skip this cell to keep results in `/content` only."),
    code("from google.colab import drive\ndrive.mount('/content/drive')"),
    md("## 3. Write the training script and phoneme vocabulary\n"
       "Generated from `training/train_ctc.py` and `training/vocab.json` in the repo; no need to edit."),
    code("%%writefile train_ctc.py\n" + script),
    code("%%writefile vocab.json\n" + vocab),
    md("""
## 4. Settings
Set `DATASET` to your Hugging Face dataset. Model choice:
- `facebook/wav2vec2-xls-r-300m`: fits a free **T4** (default).
- `facebook/wav2vec2-xls-r-1b`: what Hafs2Vec used; needs an **A100** (Colab Pro) and smaller batches.
"""),
    code('''
import os
DATASET = "YOUR_HF_USERNAME/quran-tajweed-iqlab-pilot"   # <- change this
MODEL = "facebook/wav2vec2-xls-r-300m"
OUTPUT_DIR = "/content/drive/MyDrive/thesis_runs/iqlab_pilot_300m" if os.path.isdir("/content/drive") else "/content/iqlab_pilot_300m"
EPOCHS, LR, BATCH, ACCUM = 60, 1e-4, 2, 4
print(OUTPUT_DIR)
'''),
    md("## 5. Train\nPrints evaluation (PER, sub/del/ins, accuracy on `m̃`) after every epoch on the held-out reciter."),
    code('!python train_ctc.py --dataset "{DATASET}" --model "{MODEL}" --output_dir "{OUTPUT_DIR}" '
         '--epochs {EPOCHS} --lr {LR} --batch_size {BATCH} --grad_accum {ACCUM}'),
    md("## 6. Results"),
    code('''
import json, pandas as pd
print(json.dumps(json.load(open(f"{OUTPUT_DIR}/summary.json")), indent=1, ensure_ascii=False))
pd.set_option("display.max_colwidth", 120)
pd.read_csv(f"{OUTPUT_DIR}/predictions.csv")[["id", "per", "sub", "del", "ins", "phoneme_ref", "phoneme_pred"]]
'''),
    md("""
## If the test PER stays near 100%
With 30 training clips that is normal: CTC models first learn to output nothing. Check that the model *can*
learn by evaluating on the training reciters (it should overfit them):

`!python train_ctc.py --dataset "{DATASET}" --output_dir /content/overfit --eval_split train --epochs 100`
"""),
]

nb = {"cells": cells, "metadata": {"accelerator": "GPU", "colab": {"provenance": []},
      "kernelspec": {"display_name": "Python 3", "name": "python3"}, "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 0}
(here / "finetune_colab.ipynb").write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print("wrote", here / "finetune_colab.ipynb")
