# Setup & Requirements

## 1. Environment Setup (Windows)

WSL (Windows Subsystem for Linux) is recommended. Open PowerShell as Administrator:

```powershell
wsl --install
```

Follow the prompts in the new terminal window to create your Linux username and password.

## 2. System Dependencies (Linux / WSL)

```bash
sudo apt update && sudo apt upgrade -y
```

## 3. FFmpeg (required for `wav` and `lip` steps)

```bash
sudo apt install ffmpeg -y
```

## 4. snd2acm (required for `acm` step)

The only known ACM encoder for Fallout 2, by ABel/TeamX.

Download: https://fodev.net/files/mirrors/teamx-utils/snd2acm.rar

Extract and place `snd2acm.exe` next to `vock.py`. On Linux also install Wine:

```bash
sudo apt install wine -y
```

## 5. Montreal Forced Aligner — MFA (required for `mfa` step)

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
