# V.O.C.K. — Vocal Output Creation Kit

A Python script that automates the complete voice modding pipeline for Fallout 2. Give it `.msg` dialogue file(s) and a folder of audio files — it produces a ready-to-install `vock.dat` containing ACM audio, LIP sync, and dialogue files.

## What it does

```
  msg ────────[parse CP1252]────────────────► txt (one per dialog line)
                                              ↕ optional: edit manually here
  audio ──────[ffmpeg normalize + encode]───► wav  (22050 Hz mono 16-bit)
  wav ────────[snd2acm / wine]──────────────► acm
  wav + txt ──[MFA]─────────────────────────► textgrid
  textgrid (or txt fallback) ───────────────► lip
  msg + acm + lip + txt ────────────────────► dat/vock.dat
```

## Folder structure

All folders are created automatically or configured via `config.py`.

```
vock/
├── vock.py
├── config.py             ← Global settings and paths
├── dictionaries/         ← custom.<language>.dict files
├── phonemes/             ← Phoneme mapping tables
├── msg/                  ← put your .MSG file(s) here
├── audio/                ← put your audio files here (MP3, WAV, FLAC, M4A, …)
├── txt/                  ← generated/editable: one .txt per audio line
├── wav/                  ← generated: 22050 Hz mono 16-bit PCM
├── acm/                  ← generated: Fallout 2 ACM audio files
├── textgrid/             ← generated: MFA alignment TextGrid files
├── lip/                  ← generated: Fallout 2 LIP files
├── unknown.txt           ← generated: words not recognized by dictionary
└── dat/
    └── vock.dat          ← generated: ready-to-install Fallout 2 DAT archive
```

## Supported Languages

V.O.C.K. supports multiple languages configured via config.py or by using the `--language` flag. If an NPC speaks multiple languages (e.g., Spanglish), the recommendation is to use the dominant language and add any non-dominant words to the custom dictionary.

- arpabet
- english
- spanish
- russian
- french
- german
- czech
- hungarian
- italian
- polish
- portuguese

Note: [ARPAbet](https://en.wikipedia.org/wiki/ARPABET) is a unique, English-specific set of phonetic transcription codes and currently features the largest dictionary. All other language options provided (english, spanish, russian, etc.) utilize the standard [International Phonetic Alphabet](https://en.wikipedia.org/wiki/International_Phonetic_Alphabet) models via MFA.

## Pipeline steps

| Step  | Input              | Output         | Description                                      |
|-------|--------------------|----------------|--------------------------------------------------|
| `msg` | `msg/*.msg`        | `txt/*.txt`    | Extract dialogue lines (one `.txt` per tag)      |
| `wav` | `audio/*`          | `wav/*.wav`    | Normalise + encode to 22050 Hz mono 16-bit PCM   |
| `acm` | `wav/*.wav`        | `acm/*.acm`    | Convert to Fallout 2 ACM via `snd2acm.exe`       |
| `mfa` | `wav/` + `txt/`    | `textgrid/`    | MFA forced alignment → phoneme timing            |
| `lip` | `textgrid/`+`txt/` | `lip/*.lip`    | Generate Fallout 2 LIP binary files              |
| `dat` | `msg/`+`acm/`+…    | `dat/vock.dat` | Pack everything into a Fallout 2 DAT2 archive    |

## Output DAT structure

```
text\english\dialog\*.msg
sound\speech\<npc>\*.acm
sound\speech\<npc>\*.lip
sound\speech\<npc>\*.txt
```

Where `<npc>` is derived automatically from the audio tag, e.g.:

```
text\english\dialog\acmorlis.msg
sound\speech\mor\mor1.acm
sound\speech\mor\mor1.lip
sound\speech\mor\mor1.txt
```

## Requirements

### 1. Environment Setup (Windows)

WSL (Windows Subsystem for Linux) is recommended. Open PowerShell as Administrator:

```powershell
wsl --install
```

Follow the prompts in the new terminal window to create your Linux username and password.

### 2. System Dependencies (Linux / WSL)

```bash
sudo apt update && sudo apt upgrade -y
```

### 3. FFmpeg (required for `wav` and `lip` steps)

```bash
sudo apt install ffmpeg -y
```

### 4. snd2acm (required for `acm` step)

The only known ACM encoder for Fallout 2, by ABel/TeamX.

Download: https://fodev.net/files/mirrors/teamx-utils/snd2acm.rar

Extract and place `snd2acm.exe` next to `vock.py`. On Linux also install Wine:

```bash
sudo apt install wine -y
```

### 5. Montreal Forced Aligner — MFA (required for `mfa` step)

```bash
# Install Miniconda
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b
~/miniconda3/bin/conda init bash && exec bash

# Accept the ToS
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r

# Create the MFA environment
conda create -n aligner -c conda-forge montreal-forced-aligner python=3.10 -y
conda activate aligner

# Download models for ARPAbet
mfa model download acoustic   english_us_arpa
mfa model download dictionary english_us_arpa

# Download models for other languages, where <language> = spanish, english, etc.
mfa model download acoustic   <language>_mfa
mfa model download dictionary <language>_mfa
```

## Usage

### Full pipeline (with MFA alignment)

```bash
# Activate your MFA environment
conda activate aligner

# Run the full pipeline
python3 vock.py
```

### Run only specific steps

Use `--steps` to run exactly the steps you name and skip the rest.

```bash
# Rebuild just the DAT from existing files
python3 vock.py --steps dat

# Re-run MFA alignment and regenerate LIP + DAT
python3 vock.py --steps mfa lip dat

# Re-encode audio and rebuild ACM only (e.g. after swapping audio files)
python3 vock.py --steps wav acm

# Run everything from the encoding step onward
python3 vock.py --steps wav acm mfa lip dat
```

### Skip specific steps from the full pipeline

Use `--skip` to run everything except the named step(s).

```bash
# Full pipeline but skip MFA (text approximation used for LIP)
python3 vock.py --skip mfa

# Full pipeline but skip ACM generation (no snd2acm.exe needed)
python3 vock.py --skip acm

# Skip both MFA and ACM (minimal dependencies: only ffmpeg required)
python3 vock.py --skip mfa acm
```

## Manual text-correction workflow (human-in-the-loop)

Fallout 2 dialogue sometimes contains placeholders, numbers, jokes, or names that MFA
cannot align correctly (e.g. `[Player Name]`, `$25`, `Vault 13`).
The recommended workflow is:

**1 — Extract the TXT files**

```bash
python3 vock.py --steps msg
```

This writes one `.txt` per audio-tagged line into `txt/`.  
For example, `txt/MOR1.txt` might contain:

```
What is it? You know I have a lot to do, [Player Name]!
That’ll cost you $70.
Vault 13.
```

**2 — Edit the TXT files**

Open any `.txt` file in `txt/` and correct the text so MFA can align it:

```
What is it? You know I have a lot to do, Chosen One!
That’ll cost you seventy dollars.
Vault thirteen.
```

Save the file. `vock.py` will **never overwrite a manually-edited file** once it
exists — it detects the change and preserves your correction.

**3 — Resume the pipeline from audio**

```bash
conda activate aligner
python3 vock.py --steps wav acm mfa lip dat
```

The `mfa` and `lip` steps will read your corrected text from `txt/`.

**Re-running the full pipeline later**

If you run `python3 vock.py` again after editing a `.txt` file, the `msg` step
will notice the existing file differs from the MSG source and print
`[kept manual edit]` — your correction is safe.

## Dictionary Lookup

`dict_lookup.py` is a standalone interactive tool that lets you check whether a word is known to MFA before committing it to a `.txt` file. It also loads the custom dictionary if available. The custom words are flagged with `[custom]`.

```bash
python3 dict_lookup.py english_us_arpa
```

Type words at the prompt to see their pronunciation(s):

```
> geck
  'geck'  →  G EH1 K  [custom]

> hello
  hello  →  HH AH0 L OW1
  hello  →  HH EH0 L OW1

> customword
  'customword' not found — MFA will assign 'spn' (spoken noise)
```

Words not found need either a manual text edit or a custom dictionary entry.

## Custom Dictionary

If MFA fails to align specific game nouns (e.g., `GECK`, `Arroyo`), add them to the dictionary file corresponding to your language (e.g., `dictionaries/custom.english_us_arpa.dict`).

The format is one word per line, followed by its phoneme pronunciation:

```
# ARPAbet
geck G EH1 K
mynoc M IH1 N AH0 K
tribals T R AY1 B AH0 L Z
hassleful HH AE1 S AH0 L F AH0 L

# IPA
geck ɡ ɛ k
mynoc m ɪ n ə k
tribals t ɹ aj b ə l z
hassleful h æ s ə l f ə l
```

`vock.py` automatically detects the custom dictionary and merges it with the main MFA dictionary before running alignment.

After running the `mfa` step, check `unknown.txt` for a list of words that were assigned as "spoken noise" (`spn`). Use this file to identify missing custom dictionary entries:

```
Unknown words (MFA assigned 'spn')
23 occurrence(s) in 14 file(s).
Add pronunciations for these words to your custom dictionary
(dictionaries/custom.<mfa_name>.dict) and re-run --steps mfa lip dat

SALLY1.txt
  dunton        1.98s – 2.54s
  hmm           2.70s – 3.10s

SALLY2.txt
  idjit         2.82s – 3.35s
  shoo          8.36s – 8.97s
  shoo          8.97s – 9.17s
```

Typical causes of unknown words:

- **Game-specific nouns** — `geck`, `mynoc`, `brahmin`, `arroyo` → add to the custom dictionary.
- **Non-standard words** — `hassleful`, `tribals` → add to the custom dictionary. 
- **Numbers** — `$55`, `125` → edit the `.txt` file to the spoken form (`fifty five dollars`, `one hundred twenty five`)
- **Stage directions** — `(chuckle)`, `[Player Name]` → remove or replace in the `.txt` file.

## Custom Configuration
All global settings, file paths, and environment configurations are managed in `config.py`. You can adjust these values to suit your specific project setup or system environment:
- PATHS: Defines the location of your input/output folders and the path to your snd2acm.exe executable.
- SETTINGS:
  - mfa_env: The name of the conda environment where MFA is installed (default: aligner).
  - lufs: The target loudness for audio normalization (default: -16).
  - no_norm: Set to True to disable automatic audio loudness normalization.
- LANGUAGE: Sets the default language/phoneme set used by the pipeline if no --language flag is provided.

## Notes

- **Universal audio input.** The `wav` step accepts MP3, WAV, FLAC, M4A, AAC, OGG, Opus, WMA — any format FFmpeg can decode. Duration is always read via `ffprobe` for accuracy across all containers.
- **TXT validation.** During the `wav` step, audio files without a matching `.txt` file are skipped with a clear warning. This prevents untagged or misnamed audio from silently entering the pipeline.
- **Loudness normalisation.** Audio is normalised to −16 LUFS (EBU R128) during the `wav` step to match original Fallout 2 game files. Can be configured via `config.py`.
- **Dependency fast-fail.** The script checks for `ffmpeg`, `ffprobe`, `conda`, and `snd2acm.exe` before starting and exits with a clear install message if anything required for the chosen steps is missing.

## LIP file format

The LIP binary format was reverse-engineered from Black_Electric's LIPS.py and validated against LIP Editor. Key constants:

- Version: `0x00000002`
- Unknown constant at `0x04`: `0x00005800`
- Sample offset formula: `round(seconds × 2 × 22050)`
- ACM filename field: 8 bytes, uppercase, null-padded, followed by `VOC\0`

Format documented at https://fodev.net/files/fo2/lip.html

## DAT file format

Format documented at https://fodev.net/files/fo2/dat.html

## How to obtain the MSG file

You must own a legal copy of Fallout 2.

**fo2dat** unpacks Fallout 2 DAT files. Build from source:

```bash
sudo apt install rustc cargo -y
git clone https://github.com/adamkewley/fo2dat
cd fo2dat
cargo build --release
sudo cp target/release/fo2dat /usr/local/bin/
```

Extract dialogue files from your `master.dat`:

```bash
mkdir master
fo2dat -xf master.dat -C master
```

Copy the specific `.MSG` file you want to edit into `vock/msg/`.

## How to edit the MSG file

1. Open your `.MSG` file (e.g. `ACMORLIS.MSG`) in a text editor.
2. Locate the line you want to add voice to. The format is:
   `{103}{}{What is it? You know I have a lot to do!}`
3. Add your audio tag in the middle bracket:
   `{103}{MOR1}{What is it? You know I have a lot to do!}`
4. Save your audio file as `MOR1.mp3` (or `.wav`, `.flac`, etc.) in `audio/`.
   The script matches the audio file to the MSG tag automatically.

## Other useful tools

- LIP Editor: https://fodev.net/files/mirrors/teamx-utils/LIPEditor0.96b.rar
