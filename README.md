# Masters_Quran

Working repository for an MSc Data Science thesis at the Islamic University of Madinah: **automatic detection of Tajweed errors in Qur'anic recitation**. The aim, from the accepted proposal, is to evaluate how effectively AI can detect Tajweed errors and give feedback, using a prototype speech recognition model on recitations in Hafs 'an 'Asim.

## Research scope

The thesis covers all four rules of **noon sakinah and tanween**: Izhar, where the noon stays clear, and Idgham, Iqlab and Ikhfa, where it changes. Together they form one family; which rule applies is decided by the letter that follows the noon or tanween.

| Rule | What happens to the noon | Targets | Ayahs | Sites | Dataset |
|---|---|---:|---:|---:|---|
| **Izhar** | Stays clear before a throat letter (ء ه ع ح غ خ), and before و or ي inside four words | 8 | 2,114 | 3,136 | `data/izhar_dataset.csv` |
| **Idgham** | Merges into the next letter, with ghunnah (ي ن م و) or without (ل ر) | 6 | 2,888 | 4,970 | `data/idgham_dataset.csv` |
| **Iqlab** | Turns into a hummed meem before ب | 1 | 506 | 562 | `data/iqlab_dataset.csv` |
| **Ikhfa** | Hidden with ghunnah before one of 15 letters | 15 | 2,997 | 5,305 | `data/ikhfaa_dataset.csv` |
| **All four** | | 30 | **4,677** | **13,973** | |

The four rules together occur in 4,677 of the Quran's 6,236 ayahs (75.0%) and in 113 of its 114 surahs; 125 ayahs contain all four. Only Surah An-Nasr (110) contains none.

**Not in scope:** the meem sakinah rules (Idgham shafawi, Ikhfa shafawi), other kinds of Idgham (mutamathilayn, mutajanisayn, mutaqaribayn), and Madd and Qalqalah, which are planned as future work.

### Conventions shared by all four datasets

- **Ayah by ayah.** Each ayah is treated as recited on its own, with a stop at its end, so a noon or tanween at the very end of an ayah is not counted.
- **Hafs 'an 'Asim**, with reference phonemes from the Quranic Phonemizer 3.0.5 (Ahmed Ibrahim) and Iqlab written as the closed-lip nasal `m̃` (`iqlab_nasal="closed"`). The phonemizer writes every Ikhfa nasal as `ŋ`; an Izhar noon stays a plain `n`.
- **Target names** are the rule plus the following letter, using the phonemizer's own letter names (for example `izhar_ain`, `idgham_bi_ghunnah_ya`, `ikhfaa_qaf`).
- **The same 8 columns** in every `*_dataset.csv`: `tajweed_target`, `surah`, `ayah`, `speaker_id`, `audio`, `ayah_uthmani`, `phoneme_ref`, `phoneme_realized`. One row per (target, ayah). Each `*_sites.csv` locates every individual site at word level.
- **Validated, not yet expert-verified.** Every site list was checked against an independent second method (details in each section below). The labels are machine-generated and still need review by a Tajweed expert.
- **Word positions** count words the way the phonemizer does: pause signs (ۖ ۚ ۜ…) and the hizb mark (۞) are not words. All 13,973 sites were checked to land on their trigger word in `ayah_uthmani` under that rule.

## Project status

| Stage | Status |
|---|---|
| Text datasets for Izhar, Idgham, Iqlab and Ikhfa | Done |
| Audio pilot: Iqlab, 10 ayahs, 4 professional reciters | Done ([Hugging Face dataset](#uploading-to-hugging-face-private)) |
| Fine-tuning pipeline: XLS-R 300m with CTC on `phoneme_ref`, following Hafs2Vec | Validated on the pilot |
| Balanced sample of ayahs per rule for recording | Planned |
| Controlled error recordings: each ayah recited correctly and with a specified error, verified by a Tajweed expert | Planned (main contribution) |
| Rule-level error detection with accuracy and confidence, and a feedback demo | Planned |

## Repository layout

| Folder | Contents |
|---|---|
| `data/` | The four rule datasets and their site lists |
| `scripts/` | Building and checking the datasets, fetching audio, uploading to Hugging Face, the local viewer |
| `training/` | Fine-tuning, evaluation and prediction scripts, the Colab notebook and the phoneme vocabulary |

Audio files and model weights are not stored in git; audio is on Hugging Face and models are saved from Colab.

---

## Iqlab dataset (v0.1, text and reference phonemes only)

**Iqlab**: a noon sakinah or tanween followed by ب, pronounced as a hummed meem. Text and reference phonemes only; the audio pilot further down covers the first 10 of these ayahs.

### Files

| File | Contents |
|---|---|
| `data/iqlab_dataset.csv` | 506 ayahs (surahs 1–114), one row per ayah |
| `data/iqlab_sites.csv` | 562 individual Iqlab sites, in the same format as the other rules: word position, trigger word, next word, `cross_word` / `within_word`, `trigger` (`noon_sakinah` or `tanween`), `nasal_phoneme` and `following_phoneme`. Rebuilt from the phonemizer's `iqlab` labels (`scripts/iqlab_sites_phonemizer.py`); every ayah has the same number of sites as before. |

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

Scope: **Idgham bi-ghunnah and bila-ghunnah**, split by the letter that follows the noon sakinah / tanween. Target names use the Quranic Phonemizer's own letter names (`CanonLetter`: ya, noon, meem, waw, lam, ra), the same convention as the Ikhfa targets. Same format and rules as the Iqlab dataset: ayah-by-ayah, Hafs, closed-lip `m̃` Iqlab nasal, no recordings yet.

### Files

| File | Contents |
|---|---|
| `data/idgham_dataset.csv` | One row per (target, ayah). An ayah with several targets appears once per target. |
| `data/idgham_sites.csv` | Individual sites: word position, trigger word, next word, and `cross_word` / `within_word` scope |

### Targets

| `tajweed_target` | Following letter | Ayahs | Sites |
|---|---|---:|---:|
| `idgham_bi_ghunnah_ya` | ي | 798 | 970 |
| `idgham_bi_ghunnah_noon` | ن | 196 | 205 |
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

---

## Ikhfa dataset (v0.1, text and reference phonemes only)

Scope: **Ikhfa haqiqi**, a noon sakinah or tanween hidden before one of the 15 Ikhfa letters, split by the following letter. Same format and rules as the Iqlab and Idgham datasets: ayah by ayah (a trigger at the very end of an ayah does not count), Hafs, closed-lip `m̃` for Iqlab, no recordings yet. Ikhfa shafawi (meem sakinah before ب) is a separate rule and is not included.

### Files

| File | Contents |
|---|---|
| `data/ikhfaa_dataset.csv` | 4,642 rows, one per (target, ayah), covering 2,997 distinct ayahs. An ayah with several targets appears once per target. |
| `data/ikhfaa_sites.csv` | 5,305 sites: word position, trigger word, next word, `cross_word` / `within_word`, plus `nasal_phoneme` (the hidden nasal) and `following_phoneme` |

### Targets

Target names use the Quranic Phonemizer's own letter names (`CanonLetter`).

| `tajweed_target` | Following letter | Ayahs | Sites |
|---|---|---:|---:|
| `ikhfaa_ta` | ت | 880 | 1,093 |
| `ikhfaa_tha` | ث | 91 | 108 |
| `ikhfaa_jeem` | ج | 124 | 126 |
| `ikhfaa_dal` | د | 380 | 406 |
| `ikhfaa_thal` | ذ | 172 | 180 |
| `ikhfaa_zay` | ز | 220 | 248 |
| `ikhfaa_seen` | س | 249 | 263 |
| `ikhfaa_sheen` | ش | 207 | 215 |
| `ikhfaa_sad` | ص | 100 | 108 |
| `ikhfaa_dad` | ض | 30 | 32 |
| `ikhfaa_tah` | ط | 76 | 79 |
| `ikhfaa_zah` | ظ | 117 | 121 |
| `ikhfaa_fa` | ف | 886 | 1,081 |
| `ikhfaa_qaf` | ق | 493 | 539 |
| `ikhfaa_kaf` | ك | 617 | 706 |

### Method and validation

Sites come from the Quranic Phonemizer's `ikhfaa` labels (`quranic-phonemizer` 3.0.5). For each site, the phonemizer gives the hidden nasal sound, and the sound right after it gives the following letter, so no Arabic text parsing is needed (`scripts/ikhfaa_all.py`, `scripts/build_ikhfaa.py`).

An independent check reads the Uthmani text directly (`scripts/ikhfaa_check.py`). It agrees on all 5,300 written sites. The phonemizer finds 5 more that the written text cannot show: the noons inside spoken letter names in 19:1 (كٓهيعٓصٓ), 27:1 (طسٓ) and 42:2 (عٓسٓقٓ, two sites), and the second, unwritten noon of نُـۨجِى in 21:88. Where Ikhfa ayahs also appear in the Iqlab or Idgham datasets (2,922 rows), the text and reference phonemes are identical.

### Notes

- **Encoding:** in this Uthmani text the "open" tanween forms, written before Ikhfa and Idgham letters, use U+0657 (fathatan), U+0656 (kasratan) and U+065E (dammatan). A text-based tool that only knows the standard tanween characters misses about 1,500 sites.
- **Representation:** the phonemizer writes every Ikhfa nasal as the same symbol, `ŋ`, whatever the following letter. A phoneme model can therefore distinguish Ikhfa from a clear noon (`n`) or a merge, but not the exact place of the hidden nasal.
- **Letter names at surah openings:** the four sites in 19:1, 27:1 and 42:2 are inside huroof muqatta'at; decide whether to keep them for recording.
- Same caveat as the other datasets: machine-generated, not yet verified by a Tajweed expert.

---

## Izhar dataset (v0.1, text and reference phonemes only)

Scope: a noon sakinah or tanween **kept clear**, pronounced as a plain `n`, split by the reason it stays clear. Same format and rules as the other datasets: ayah by ayah, Hafs, closed-lip `m̃` for Iqlab, no recordings yet. A noon at the very end of an ayah, which is clear only because of the stop, is not counted (3,122 such noons are excluded).

### Files

| File | Contents |
|---|---|
| `data/izhar_dataset.csv` | 2,722 rows, one per (target, ayah), covering 2,114 distinct ayahs |
| `data/izhar_sites.csv` | 3,136 sites: word position, trigger word, next word, `cross_word` / `within_word`, `izhar_type` (`halqi`, `mutlaq` or `special`), `noon_phoneme` and `following_phoneme` |

### Targets

| `tajweed_target` | Why the noon stays clear | Ayahs | Sites |
|---|---|---:|---:|
| `izhar_hamza` | Before ء (halqi) | 1,017 | 1,253 |
| `izhar_heh` | Before ه (halqi) | 617 | 732 |
| `izhar_ain` | Before ع (halqi) | 552 | 593 |
| `izhar_ha` | Before ح (halqi) | 207 | 215 |
| `izhar_ghain` | Before غ (halqi) | 82 | 82 |
| `izhar_kha` | Before خ (halqi) | 126 | 134 |
| `izhar_mutlaq` | Before و or ي inside one word: ٱلدُّنْيَا، بُنْيَـٰن، قِنْوَان، صِنْوَان | 119 | 125 |
| `izhar_special` | نٓ ۚ وَٱلْقَلَمِ (68:1), kept clear in Hafs; مَنْ ۜ رَاقٍ (75:27), kept clear by the sakt | 2 | 2 |

The halqi targets follow the traditional order of the throat letters, ء ه ع ح غ خ, and use the phonemizer's own letter names.

### Method and validation

Sites come from the Quranic Phonemizer's `izhar` labels (`quranic-phonemizer` 3.0.5). For each site, the sound right after the noon gives the following letter (`scripts/izhar_all.py`, `scripts/build_izhar.py`). An independent check reads the Uthmani text directly (`scripts/izhar_check.py`) and agrees exactly: all 3,009 halqi sites and all 125 mutlaq sites, with no ayah differing. Where Izhar ayahs also appear in the other three datasets (2,275 rows), the text and reference phonemes are identical.

### Notes

- **Izhar mirrors Ikhfa.** A clear noon is the typical Ikhfa error, and a hidden or merged noon the typical Izhar error. With both rules, a detector is tested in both directions, not only on whether it hears a nasal.
- **Errors are visible to a phoneme model.** The correct Izhar noon is `n`; adding ghunnah, hiding it or merging it changes the phoneme string.
- **يسٓ وَٱلْقُرْءَانِ is not included.** Hafs also keeps that noon clear, but يسٓ is a whole ayah (36:1), so under the ayah-by-ayah rule its noon ends at a stop.
- Same caveat as the other datasets: machine-generated, not yet verified by a Tajweed expert.

---

## Audio pipeline (pilot: Iqlab, first 10 ayahs, 4 reciters)

`scripts/fetch_audio.py` downloads ayah-level recitations, converts them to 16 kHz mono WAV and writes `manifest/recordings.csv` (one row per recording). Run from the dataset folder:

```bash
python scripts/fetch_audio.py --target iqlab --limit 10
```

Needs Python 3.8+ and ffmpeg. If ffmpeg is not on PATH, run `python -m pip install imageio-ffmpeg` (the script uses its bundled binary). Downloads are cached in `audio_raw/`, so re-runs only fetch what is missing.

- **Ayahs:** 2:10, 2:18, 2:19, 2:27, 2:31, 2:33, 2:41, 2:51, 2:52, 2:56 (the first 10 Iqlab ayahs in Quran order).
- **Reciters** (speaker ids -> EveryAyah folders): `alafasy` (Alafasy_128kbps), `husary` (Husary_128kbps), `minshawy` (Minshawy_Murattal_128kbps), `hudhaify` (Hudhaify_128kbps). The folder names have **not** been verified against the live site; a wrong name shows up as an HTTP 404 in the end-of-run report.
- **Layout:** audio is grouped by surah, then ayah: `audio/SSS/AAA/<speaker_id>.wav` (e.g. `audio/002/010/hudhaify.wav`). Downloads are cached separately in `audio_raw/<EveryAyah folder>/SSSAAA.mp3`. Running the script on an older per-reciter layout (`audio/<speaker>/SSSAAA.wav`) moves the files into the new one.
- **Manifest columns:** the 8 dataset columns, then `source_url` and `duration_s`. `phoneme_realized` is left empty (not annotated); fine-tuning uses `phoneme_ref`.
- **Not yet done:** the audio licence has not been checked; do not redistribute the audio until it has.

## Uploading to Hugging Face (private)

`scripts/push_to_hf.py` packages `manifest/recordings.csv` and the WAVs as a Hugging Face dataset (columns: `id`, `tajweed_target`, `surah`, `ayah`, `speaker_id`, `audio`, `ayah_uthmani`, `phoneme_ref`, `phoneme_realized`, `duration_s`, `source_url`).

```bash
python -m pip install datasets huggingface_hub
hf auth login                      # token with WRITE access; never paste it in chat
python scripts/push_to_hf.py --dry-run   # build and verify locally, uploads nothing
python scripts/push_to_hf.py             # upload as a PRIVATE dataset: <username>/quran-tajweed-iqlab-pilot
```

- **Split:** speaker-disjoint. `--holdout hudhaify` (default) makes that reciter the `test` split, and the rest are `train`. With only 10 ayahs the split is not ayah-disjoint, so test scores will be optimistic.
- **Private by default** (`--public` to publish). The audio licence has **not** been checked. If the dataset is made public, the dataset card carries reciter attribution, source links, a statement that the maintainer claims no rights over the audio, and a takedown route (a Discussion on the dataset's Community tab). Refresh the card with `python scripts/push_to_hf.py --update-card`.
- Reading the audio back for training needs a decoder (`pip install torchcodec`, or load with `Audio(decode=False)` and decode the bytes with `soundfile`).

## Local viewer

```bash
python3 scripts/make_viewer.py     # writes viewer.html (stdlib only)
```

Open `viewer.html` in a browser (keep it in the dataset folder so the relative audio paths resolve). It shows one row per recording with an audio player, the Uthmani text, `phoneme_ref` / `phoneme_realized` (nasal tajweed phonemes highlighted; change with `--highlight`), and search, filters (reciter, surah, target) and sortable columns. Re-run it after `fetch_audio.py`.

---

## Fine-tuning (pilot)

See [`training/README.md`](training/README.md). Upload `training/finetune_colab.ipynb` to Google Colab, set your dataset name, and run it top to bottom. It fine-tunes XLS-R with CTC on `phoneme_ref`, following Hafs2Vec (Ibrahim, 2025).
