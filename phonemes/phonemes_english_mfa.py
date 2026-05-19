"""
phonemes_english_mfa.py  ─  IPA → Fallout 2 LIP phoneme codes
                            For use with MFA model: english_mfa

Based on the Fallout 2 LIP phoneme table by Anchorite and Black_Electric.
Maps standard English IPA symbols to the 41 distinct mouth-shape codes.
MFA IPA stress markers (ˈ, ˌ) and length marks (ː) are stripped before lookup.
"""

ENGLISH_IPA_TO_LIP: dict[str, int] = {
    # ── Vowels ────────────────────────────────────────────────────────────────
    "i":   0x01,  # fleece  i:      bee, lady
    "ɪ":   0x02,  # kit     ɪ       busy, guild
    "eɪ":  0x03,  # face    eɪ      bay, they
    "e":   0x03,  # face (alt)
    "ɛ":   0x04,  # dress   e       end, bread
    "æ":   0x05,  # trap    æ       cat, plaid
    "ɑ":   0x06,  # palm    ɑ:      arm
    "ɔ":   0x07,  # thought ɔ:      paw, ball
    "oʊ":  0x08,  # goat    oʊ      open, toe
    "o":   0x08,  # goat (alt)
    "ʊ":   0x09,  # foot    ʊ       wolf, bush
    "u":   0x0A,  # goose   u:      dew, blue
    "ɚ":   0x0B,  # nurse   ʊəʳ     r-coloured vowel
    "ɝ":   0x0B,  # nurse   ʊəʳ     r-coloured vowel
    "ɒ":   0x0C,  # lot     ɒ       slaw, fought
    "ʌ":   0x0D,  # strut   ʌ       lug, blood
    "ə":   0x0D,  # schwa   ʌ       (mapped to similar open shape)
    "aɪ":  0x0E,  # price   aɪ      sky, night
    "aʊ":  0x0F,  # mouth   aʊ      now, shout
    "ɔɪ":  0x10,  # choice  ɔɪ      join, boy

    # ── Stops ─────────────────────────────────────────────────────────────────
    "p":   0x11,  # pin, dippy
    "b":   0x12,  # bug, bubble
    "t":   0x13,  # tip, matter
    "ɾ":   0x13,  # alveolar tap (matter)
    "d":   0x14,  # dad, add
    "k":   0x15,  # cat, folk
    "ɡ":   0x16,  # gun, egg (IPA standard g)
    "g":   0x16,  # gun, egg (ASCII fallback)

    # ── Fricatives ────────────────────────────────────────────────────────────
    "f":   0x17,  # fat, cliff
    "v":   0x18,  # vine, five
    "θ":   0x19,  # thongs (voiceless dental)
    "ð":   0x1A,  # leather (voiced dental)
    "s":   0x1B,  # sit, less
    "z":   0x1C,  # zed, buzz
    "ʃ":   0x1D,  # sham, ocean
    "ʒ":   0x1E,  # treasure, azure
    "h":   0x1F,  # hop, who

    # ── Nasals ────────────────────────────────────────────────────────────────
    "m":   0x20,  # man, palm
    "n":   0x21,  # net, funny
    "ŋ":   0x22,  # ring, pink

    # ── Approximants & liquids ────────────────────────────────────────────────
    "l":   0x23,  # live, well
    "ɫ":   0x23,  # dark l
    "w":   0x24,  # wit, why
    "j":   0x25,  # you, onion
    "ɹ":   0x26,  # run, carrot (MFA english typical 'r')
    "r":   0x26,  # run, carrot (fallback)

    # ── Affricates ────────────────────────────────────────────────────────────
    "tʃ":  0x27,  # chip, watch
    "dʒ":  0x28,  # jam, wage
    "t͡ʃ":  0x27,  # chip, watch (with tie bar)
    "d͡ʒ":  0x28,  # jam, wage (with tie bar)

    # ── Silence / non-speech ─────────────────────────────────────────────────
    "sil": 0x00,  # silence
    "sp":  0x00,  # short pause
    "spn": 0x00,  # spoken noise
    "":    0x00,
}

def ipa_to_lip_code(phoneme: str) -> int:
    """
    Strip IPA stress/length markers and return the Fallout 2 LIP code.
    Falls back to 0x0D (ʌ, open mouth shape) for unknown symbols.
    """
    import re
    # Remove primary stress (ˈ), secondary stress (ˌ), and length marks (ː)
    p = re.sub(r"[ˈˌː]", "", phoneme.strip().lower())
    return ENGLISH_IPA_TO_LIP.get(p, 0x0D)