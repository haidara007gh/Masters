# Masters_Quran

Working repository for an MSc Data Science project on automatic assessment of Qur'anic recitation (Tajweed-aware pronunciation assessment / mispronunciation detection and diagnosis).

## Iqlab dataset (v0.1, text and reference phonemes only)

The first target rule is **Iqlab** (noon sakinah or tanween followed by ba). This version lists the ayahs that contain it. **No recordings yet.**

### Files

| File | Contents |
|---|---|
| `data/iqlab_dataset.csv` | 506 ayahs (surahs 1–114), one row per ayah |
| `data/iqlab_sites.csv` | 562 individual Iqlab sites: word position, trigger word, next word, trigger type, within-word vs across-word |

### Columns of `iqlab_dataset.csv`

`tajweed_target`, `surah`, `ayah`, `speaker_id`, `audio`, `ayah_uthmani`, `phoneme_ref`, `phoneme_realized`

`speaker_id`, `audio` and `phoneme_realized` are intentionally empty until recordings are collected.

### Scope rules

- **Ayah-by-ayah only.** Each ayah is treated as recited on its own, with a stop at its end. A noon sakinah or tanween at the very end of an ayah is **not** counted as Iqlab, even if the next ayah begins with ba.
- Hafs 'an Asim reading.
- `phoneme_ref` uses the **closed-lip Iqlab nasal `m̃`** (phonemizer option `iqlab_nasal="closed"`). All other options are the phonemizer defaults (so, for example, ikhfaa shafawi still uses `ŋ`).

### Method

Iqlab sites were detected three independent ways, which agree exactly (506 ayahs, 562 sites):

1. the small-meem sign (ۢ / ۭ) in the Uthmani script,
2. a rule-based check (noon sakinah or tanween followed by ba),
3. the explicit Iqlab labels of the Qur'anic Phonemizer.

Sources: Uthmani text from the `quran-json` npm package (detection); `ayah_uthmani` and `phoneme_ref` from `quranic-phonemizer` 3.0.5 (Ahmed Ibrahim), so that text and phonemes are aligned.

### Reproducing

Python 3.11+, `pip install quranic-phonemizer`, and `npm install quran-json`. Run in order: `scripts/detect.py`, `scripts/phon_all.py`, `scripts/build.py`, `scripts/closed.py`. Paths inside the scripts are relative to the working folder they were developed in; adjust as needed.

### Caveats

Machine-generated and **not yet verified by a Tajweed expert**. A sample should be reviewed before use as training or evaluation data.

---

## Idgham dataset (v0.1, text and reference phonemes only)

Same format and scope rules as the Iqlab dataset (ayah-by-ayah, Hafs, closed-lip `m̃` Iqlab nasal, no recordings yet).

### Files

| File | Contents |
|---|---|
| `data/idgham_dataset.csv` | 5,192 rows, one per (Idgham type, ayah), 3,223 distinct ayahs. `tajweed_target` holds the type. |
| `data/idgham_sites.csv` | 7,070 individual sites with word position, trigger word, next word, and `cross_word` / `within_word` scope |

### Types and counts

| `tajweed_target` | Ayahs | Sites |
|---|---:|---:|
| `idgham_bi_ghunnah` (noon/tanween + ي ن م و) | 2,512 | 3,935 |
| `idgham_bila_ghunnah` (noon/tanween + ل ر) | 905 | 1,035 |
| `idgham_shafawi` (meem sakinah + meem) | 726 | 840 |
| `idgham_mutamathilayn` (identical letters) | 976 | 1,185 |
| `idgham_mutajanisayn_kamil` | 56 | 58 |
| `idgham_mutajanisayn_naqis` | 4 | 4 |
| `idgham_mutaqaribayn` | 13 | 13 |

An ayah can appear under several types (one row each).

### Method and validation

Occurrences come from the Qur'anic Phonemizer's explicit rule labels (`quranic-phonemizer` 3.0.5). For the noon/tanween types and Idgham shafawi, an independent rule-based check on the text was run (`scripts/idgham_check.py`). It reproduces the phonemizer's counts apart from explained cases: the letter name `نٓ` (68:1), the sakt reading of `مَنْ رَاقٍ` (75:27), and word-index offsets in my checker. Mutamathilayn, mutajanisayn and mutaqaribayn rely on the phonemizer's labels only (not independently checked).

### Notes

- Tanween or noon before the article ٱل is not Idgham (hamza wasl drops, so it is izhar); the phonemizer follows this.
- `within_word` sites include the huroof muqatta'at (e.g. الٓمٓ, طسٓمٓ) and a few ordinary words (e.g. يُدْرِككُّمُ, 4:78). Decide whether to keep muqatta'at ayahs for recording.
- Same caveat as Iqlab: machine-generated, not yet verified by a Tajweed expert.
