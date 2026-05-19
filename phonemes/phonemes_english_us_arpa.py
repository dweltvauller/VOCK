"""
phonemes_english_us_arpa.py  ─  ARPAbet → Fallout 2 LIP phoneme codes
                                For use with MFA model: english_us_arpa

Based on the Fallout 2 LIP phoneme table by Anchorite and Black_Electric.
The engine supports 41 distinct mouth-shape codes mapped to .FRM frames.
ARPAbet stress digits (0, 1, 2) are stripped before lookup.
"""

ARPA_TO_LIP: dict[str, int] = {
    # ── Vowels ────────────────────────────────────────────────────────────────
    "IY":  0x01,  # fleece  i:      bee, lady
    "IH":  0x02,  # kit     ɪ       busy, guild
    "EY":  0x03,  # face    eɪ      bay, they
    "EH":  0x04,  # dress   e       end, bread
    "AE":  0x05,  # trap    æ       cat, plaid
    "AA":  0x06,  # palm    ɑ:      arm
    "AO":  0x07,  # thought ɔ:      paw, ball
    "OW":  0x08,  # goat    oʊ      open, toe
    "UH":  0x09,  # foot    ʊ       wolf, bush
    "UW":  0x0A,  # goose   u:      dew, blue
    # 0x0B ʊəʳ — no direct ARPAbet equivalent; ER is the closest r-coloured slot
    "ER":  0x0B,  # nurse   ʊəʳ     closest available r-coloured vowel
    # 0x0C ɒ  — no ARPAbet equivalent; AA covers both palm and lot in US English
    "AH":  0x0D,  # strut   ʌ       lug, blood
    "AY":  0x0E,  # price   aɪ      sky, night
    "AW":  0x0F,  # mouth   aʊ      now, shout
    "OY":  0x10,  # choice  ɔɪ      join, boy

    # ── Stops ─────────────────────────────────────────────────────────────────
    "P":   0x11,  # pin, dippy
    "B":   0x12,  # bug, bubble
    "T":   0x13,  # tip, matter
    "D":   0x14,  # dad, add
    "K":   0x15,  # cat, folk
    "G":   0x16,  # gun, egg

    # ── Fricatives ────────────────────────────────────────────────────────────
    "F":   0x17,  # fat, cliff
    "V":   0x18,  # vine, five
    "TH":  0x19,  # thongs (voiceless dental)
    "DH":  0x1A,  # leather (voiced dental)
    "S":   0x1B,  # sit, less
    "Z":   0x1C,  # zed, buzz
    "SH":  0x1D,  # sham, ocean
    "ZH":  0x1E,  # treasure, azure
    "HH":  0x1F,  # hop, who

    # ── Nasals ────────────────────────────────────────────────────────────────
    "M":   0x20,  # man, palm
    "N":   0x21,  # net, funny
    "NG":  0x22,  # ring, pink

    # ── Approximants & liquids ────────────────────────────────────────────────
    "L":   0x23,  # live, well
    "W":   0x24,  # wit, why
    "Y":   0x25,  # you, onion
    "R":   0x26,  # run, carrot

    # ── Affricates ────────────────────────────────────────────────────────────
    "CH":  0x27,  # chip, watch
    "JH":  0x28,  # jam, wage

    # ── Silence / non-speech ─────────────────────────────────────────────────
    "SIL": 0x00,  # silence
    "SP":  0x00,  # short pause
    "SPN": 0x00,  # spoken noise
    "":    0x00,
}


def arpa_to_lip_code(phoneme: str) -> int:
    """
    Strip stress digit and return the Fallout 2 LIP code for an ARPAbet phoneme.
    Falls back to 0x0D (ʌ, open mouth shape) for unknown symbols.
    """
    import re
    p = re.sub(r"\d", "", phoneme.strip().upper())
    return ARPA_TO_LIP.get(p, 0x0D)