# config.py

# Set your default language.
# Options: arpabet, english, spanish, russian, german, italian, french, hungarian, polish, portuguese
LANGUAGE = "arpabet"

# Set the paths to the file structure, relative to the script location.
PATHS = {
    "msg":       "./msg",
    "audio":     "./audio",
    "txt":       "./txt",
    "wav":       "./wav",
    "acm":       "./acm",
    "textgrid":  "./textgrid",
    "lip":       "./lip",
    "dat":       "./dat/vock.dat",
    "snd2acm":   "./snd2acm.exe",
}

SETTINGS = {
    "mfa_env": "aligner",  # Set the MFA environment
    "lufs":    -16.0,      # Set the LUFS for audio normalization
    "no_norm": False,      # Normalization enabled
}
