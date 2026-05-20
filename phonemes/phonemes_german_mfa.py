"""
phonemes_german_mfa.py  ─  IPA → Fallout 2 LIP Phonem-Codes
                            Für MFA-Modell: german_mfa

Basierend auf der Fallout 2 LIP Phonem-Tabelle von Anchorite und Black_Electric.
Ordnet deutsche IPA-Symbole den 41 Mundform-Codes zu.
IPA-Marker (Betonung, Länge) werden vor der Suche entfernt.
"""

PHONEME_TABLE: dict[str, int] = {
    # ── Vokale ────────────────────────────────────────────────────────────────
    "iː":  0x01,  # i (Riese)
    "ɪ":   0x02,  # i (mit)
    "eː":  0x04,  # e (Beet)
    "ɛ":   0x04,  # e (Bett)
    "aː":  0x06,  # a (Bahn)
    "a":   0x06,  # a (hat)
    "oː":  0x08,  # o (Boot)
    "ɔ":   0x07,  # o (Gott)
    "uː":  0x0A,  # u (Fuß)
    "ʊ":   0x09,  # u (Fluss)
    "yː":  0x0A,  # ü (kühl) - gerundet, wie u
    "ʏ":   0x09,  # ü (muss) - gerundet, wie u
    "øː":  0x08,  # ö (hören) - gerundet, wie o
    "œ":   0x07,  # ö (können) - gerundet, wie o
    "ə":   0x0D,  # e (bitte)

    # ── Plosive ───────────────────────────────────────────────────────────────
    "p":   0x11,  # p (Post)
    "b":   0x12,  # b (Ball)
    "t":   0x13,  # t (Tag)
    "d":   0x14,  # d (Dach)
    "k":   0x15,  # k (kalt)
    "ɡ":   0x16,  # g (gut)

    # ── Frikative ─────────────────────────────────────────────────────────────
    "f":   0x17,  # f (falsch)
    "v":   0x18,  # w (Wasser)
    "s":   0x1B,  # s (das)
    "z":   0x1C,  # s (sagen)
    "ʃ":   0x1D,  # sch (Schiff)
    "ʒ":   0x1E,  # g (Genie)
    "x":   0x1F,  # ch (Bach)
    "ç":   0x1F,  # ch (ich) - palatal, ähnelt h
    "h":   0x1F,  # h (Hand)

    # ── Nasale und Liquide ────────────────────────────────────────────────────
    "m":   0x20,  # m (Mann)
    "n":   0x21,  # n (Nase)
    "ŋ":   0x22,  # ng (Ding)
    "l":   0x23,  # l (Licht)
    "ʁ":   0x26,  # r (rot) - uvularer Approximant

    # ── Affrikaten ────────────────────────────────────────────────────────────
    "t͡s":  0x27,  # z (Zeit)
    "t͡ʃ":  0x27,  # tsch (Tisch)

    # ── Stille / Nicht-Sprache ────────────────────────────────────────────────
    "sil": 0x00,
    "sp":  0x00,
    "spn": 0x00,
    "":    0x00,
}
