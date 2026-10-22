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

## Idgham dataset (v0.3, text and reference phonemes only)

Scope: **Idgham bi-ghunnah and bila-ghunnah**, split by the letter that follows the noon sakinah / tanween. Same format and rules as the Iqlab dataset: ayah-by-ayah, Hafs, closed-lip `m̃` Iqlab nasal, no recordings yet.

### Files

| File | Contents |
|---|---|
| `data/idgham_dataset.csv` | One row per (target, ayah). An ayah with several targets appears once per target. |
| `data/idgham_sites.csv` | Individual sites: word position, trigger word, next word, and `cross_word` / `within_word` scope |

### Targets

| `tajweed_target` | Following letter | Ayahs | Sites |
|---|---|---:|---:|
| `idgham_bi_ghunnah_ya` | ي | 798 | 970 |
| `idgham_bi_ghunnah_nun` | ن | 196 | 205 |
| `idgham_bi_ghunnah_meem` | م | 1,114 | 1,300 |
| `idgham_bi_ghunnah_waw` | و | 1,130 | 1,460 |
| `idgham_bila_ghunnah_lam` | ل | 675 | 748 |
| `idgham_bila_ghunnah_ra` | ر | 277 | 287 |

Totals: 3,935 bi-ghunnah sites and 1,035 bila-ghunnah sites (4,190 rows).

### Method and validation

Occurrences come from the Qur'anic Phonemizer's explicit rule labels (`quranic-phonemizer` 3.0.5). An independent rule-based check on the text (`scripts/idgham_check.py`) reproduces the phonemizer's counts apart from explained cases: the letter name `نٓ` (68:1), the sakt reading of `مَنْ رَاقٍ` (75:27), and word-index offsets in the checker. The following letter is taken from the first letter of the next word.

### Notes

- Tanween or noon before the article ٱل is not Idgham (hamza wasl drops, so it is izhar); the phonemizer follows this.
- Two `within_word` sites are the huroof muqatta'at `طسٓمٓ` (26:1, 28:1), counted under `idgham_bi_ghunnah_meem`; decide whether to keep them for recording.
- Same caveat as Iqlab: machine-generated, not yet verified by a Tajweed expert.
