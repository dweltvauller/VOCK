# config.py

# Set your default language.
# Options: arpabet, english, spanish, russian, german, italian, french, hungarian, polish, portuguese, czech
LANGUAGE = "arpabet"

# Set the paths to the file structure, relative to the script location.
PATHS = {
    "msg":        "./msg",
    "audio":      "./audio",
    "txt":        "./txt",
    "wav":        "./wav",
    "acm":        "./acm",
    "textgrid":   "./textgrid",
    "lip":        "./lip",
    "dat":        "./dat/vock.dat",
    "float_dat":  "./dat/vock_floats.dat",
    "int":        "./int",
    "snd2acm":    "./snd2acm.exe",
    "npc_chars":   "./npc.py",
    "float_chars": "./float.py",
}

SETTINGS = {
    "mfa_env": "aligner",  # Set the MFA environment
    "lufs":    -16.0,      # Set the LUFS for audio normalization
    "no_norm": False,      # Normalization enabled
}
