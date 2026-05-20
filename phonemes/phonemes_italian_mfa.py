"""
phonemes_italian_mfa.py  ─  IPA → codici Fallout 2 LIP
                            Per modello MFA: italian_mfa

Basato sulla tabella dei fonemi LIP di Fallout 2 di Anchorite e Black_Electric.
Associa i simboli IPA dell'italiano ai 41 codici di forma della bocca.
I marcatori IPA (accento, lunghezza) vengono rimossi prima della ricerca.
"""

PHONEME_TABLE: dict[str, int] = {
    # ── Vocali ────────────────────────────────────────────────────────────────
    "i":   0x01,  # i (vino)
    "e":   0x04,  # é (pesca)
    "ɛ":   0x04,  # è (pèsca)
    "a":   0x06,  # a (casa)
    "ɔ":   0x07,  # ò (còlto)
    "o":   0x08,  # ó (cólto)
    "u":   0x0A,  # u (luna)

    # ── Occlusive ─────────────────────────────────────────────────────────────
    "p":   0x11,  # p (palla)
    "b":   0x12,  # b (bello)
    "t":   0x13,  # t (tutto)
    "d":   0x14,  # d (dito)
    "k":   0x15,  # c (cane), ch (chi)
    "ɡ":   0x16,  # g (gatto), gh (ghi)

    # ── Fricative ─────────────────────────────────────────────────────────────
    "f":   0x17,  # f (faro)
    "v":   0x18,  # v (vino)
    "s":   0x1B,  # s (sole)
    "z":   0x1C,  # s (sbaglio)
    "ʃ":   0x1D,  # sc (scena)

    # ── Nasali e Liquide ──────────────────────────────────────────────────────
    "m":   0x20,  # m (mano)
    "n":   0x21,  # n (nave)
    "ɲ":   0x21,  # gn (gnocco)
    "ŋ":   0x22,  # n (ancora)
    "l":   0x23,  # l (luna)
    "ʎ":   0x25,  # gl (gli) - map to j
    "r":   0x26,  # r (rana)

    # ── Affricate ─────────────────────────────────────────────────────────────
    "t͡s":  0x27,  # z (pazzo)
    "d͡z":  0x28,  # z (zaino)
    "t͡ʃ":  0x27,  # c (ciao)
    "d͡ʒ":  0x28,  # g (gelo)

    # ── Silenzio / non-parlato ────────────────────────────────────────────────
    "sil": 0x00,
    "sp":  0x00,
    "spn": 0x00,
    "":    0x00,
}
