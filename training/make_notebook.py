#!/usr/bin/env python3
"""Regenerate finetune_colab.ipynb so it embeds the current train_ctc.py and vocab.json."""
import json
from pathlib import Path

here = Path(__file__).parent
script = (here / "train_ctc.py").read_text(encoding="utf-8")
evaluator = (here / "evaluate_ctc.py").read_text(encoding="utf-8")
predictor = (here / "predict_ctc.py").read_text(encoding="utf-8")
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
    md("## 2. Mount Google Drive (to keep the results)\nTraining writes to Colab's local disk, which is fast and is "
       "wiped when the session ends. After training, a cell copies only the final model and results to Drive "
       "(about 1.3 GB). Do not train straight into Drive: checkpoints pile up in Drive's cache and Trash and fill the disk."),
    code("from google.colab import drive\ndrive.mount('/content/drive')"),
    md("## 3. Write the training script and phoneme vocabulary\n"
       "Generated from `training/train_ctc.py` and `training/vocab.json` in the repo; no need to edit."),
    code("%%writefile train_ctc.py\n" + script),
    code("%%writefile vocab.json\n" + vocab),
    code("%%writefile evaluate_ctc.py\n" + evaluator),
    code("%%writefile predict_ctc.py\n" + predictor),
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
RUN_NAME = "iqlab_pilot_300m"
OUTPUT_DIR = f"/content/{RUN_NAME}"                       # local disk while training
DRIVE_DIR = f"/content/drive/MyDrive/thesis_runs/{RUN_NAME}"  # where the results are copied afterwards
EPOCHS, LR, BATCH, ACCUM = 60, 1e-4, 2, 4
print(OUTPUT_DIR, "->", DRIVE_DIR)
'''),
    code("!df -h /content | tail -1   # free disk before training"),
    md("## 5. Train\nPrints evaluation (PER, sub/del/ins, accuracy on `m̃`) after every epoch on the held-out reciter."),
    code('!python train_ctc.py --dataset "{DATASET}" --model "{MODEL}" --output_dir "{OUTPUT_DIR}" '
         '--epochs {EPOCHS} --lr {LR} --batch_size {BATCH} --grad_accum {ACCUM}'),
    md("## 6. Copy the results to Drive\nCopies `final/` (the model), `predictions.csv` and `summary.json`. Checkpoints are not copied."),
    code('''
import os, shutil
if os.path.isdir("/content/drive/MyDrive"):
    os.makedirs(DRIVE_DIR, exist_ok=True)
    for name in ["summary.json", "predictions.csv"]:
        shutil.copy(f"{OUTPUT_DIR}/{name}", DRIVE_DIR)
    shutil.copytree(f"{OUTPUT_DIR}/final", f"{DRIVE_DIR}/final", dirs_exist_ok=True)
    print("copied to", DRIVE_DIR)
else:
    print("Drive is not mounted; results are only in", OUTPUT_DIR)
'''),
    md("## 7. Results"),
    code('''
import json, pandas as pd
print(json.dumps(json.load(open(f"{OUTPUT_DIR}/summary.json")), indent=1, ensure_ascii=False))
pd.set_option("display.max_colwidth", 120)
pd.read_csv(f"{OUTPUT_DIR}/predictions.csv")[["id", "per", "sub", "del", "ins", "phoneme_ref", "phoneme_pred"]]
'''),
    md("""
## 8. Did the model learn anything? Evaluate on the training reciters
No retraining: this scores the model you just trained on the `train` split (Alafasy, Husary, Minshawy).
If training PER is well below 100% while test PER is near 100%, the model learned but does not yet
generalise to a new voice. If both are near 100%, it is still in the blank phase: train longer or add data.
**In a new session you can skip training:** run steps 1 to 4, then this cell. It loads `final/` from local disk or, if that is gone, from Drive.
"""),
    code('''
import os, pandas as pd   # self-contained: works without running step 7
MODEL_DIR = f"{OUTPUT_DIR}/final" if os.path.isdir(f"{OUTPUT_DIR}/final") else f"{DRIVE_DIR}/final"
!python evaluate_ctc.py --model_dir "{MODEL_DIR}" --dataset "{DATASET}" --split train --output_dir "{OUTPUT_DIR}"
pd.read_csv(f"{OUTPUT_DIR}/predictions_train.csv")[["id", "per", "sub", "del", "ins", "phoneme_ref", "phoneme_pred"]]
'''),
    md("""
## 9. Predict on your own recording
Upload any recording (wav, mp3, m4a...). The model writes the phonemes it hears. Set `AYAH` to the ayah that was
recited (e.g. `"2:18"`) to compare with its reference, built with the same phonemizer settings as the dataset, or
leave it empty for the prediction only. Results also go to `predictions_mine.csv`, which the Phoneme Alignment
Viewer opens. In a new session, run steps 1 to 4 first.
"""),
    code('''
!pip install -q quranic-phonemizer==3.0.5
import os
from google.colab import files
MODEL_DIR = f"{OUTPUT_DIR}/final" if os.path.isdir(f"{OUTPUT_DIR}/final") else f"{DRIVE_DIR}/final"
AYAH = "2:18"          # the ayah you recited, or "" for the prediction only
uploaded = files.upload()
AYAH_ARG = f"--ayah {AYAH}" if AYAH else ""
os.makedirs(OUTPUT_DIR, exist_ok=True)
for name in uploaded:
    !python predict_ctc.py "{name}" --model_dir "{MODEL_DIR}" {AYAH_ARG} --out "{OUTPUT_DIR}/predictions_mine.csv"
'''),
]

nb = {"cells": cells, "metadata": {"accelerator": "GPU", "colab": {"provenance": []},
      "kernelspec": {"display_name": "Python 3", "name": "python3"}, "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 0}
(here / "finetune_colab.ipynb").write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print("wrote", here / "finetune_colab.ipynb")
