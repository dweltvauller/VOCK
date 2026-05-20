"""
phonemes_czech_mfa.py  ─  IPA → kódy Fallout 2 LIP
                           Pro model MFA: czech_mfa

Založeno na tabulce fonémů Fallout 2 LIP od autorů Anchorite a Black_Electric.
Mapuje symboly IPA češtiny na 41 kódů tvarů úst.
Značky IPA (stres, délka) jsou před vyhledáváním odstraněny.
"""

PHONEME_TABLE: dict[str, int] = {
    # ── Samohlásky ─────────────────────────────────────────────────────────────
    "a":   0x06,  # a (auto)
    "aː":  0x06,  # á (dáma)
    "e":   0x04,  # e (les)
    "eː":  0x04,  # é (mléko)
    "i":   0x01,  # i (pivo)
    "iː":  0x01,  # í (dík)
    "o":   0x08,  # o (oko)
    "oː":  0x08,  # ó (kód)
    "u":   0x0A,  # u (ruka)
    "uː":  0x0A,  # ú/ů (dům)

    # ── Plosívy ────────────────────────────────────────────────────────────────
    "p":   0x11,  # p (pán)
    "b":   0x12,  # b (bota)
    "t":   0x13,  # t (tam)
    "d":   0x14,  # d (dám)
    "c":   0x15,  # ť (ťuk) - mapováno na k
    "ɟ":   0x16,  # ď (ďas) - mapováno na g
    "k":   0x15,  # k (kdo)
    "ɡ":   0x16,  # g (guma)

    # ── Frikativy ──────────────────────────────────────────────────────────────
    "f":   0x17,  # f (farář)
    "v":   0x18,  # v (voda)
    "s":   0x1B,  # s (les)
    "z":   0x1C,  # z (zub)
    "ʃ":   0x1D,  # š (šít)
    "ʒ":   0x1E,  # ž (žába)
    "x":   0x1F,  # ch (chlad)
    "h":   0x1F,  # h (hora)

    # ── Nazály a likvidy ───────────────────────────────────────────────────────
    "m":   0x20,  # m (máma)
    "n":   0x21,  # n (nos)
    "ɲ":   0x21,  # ň (laň)
    "l":   0x23,  # l (les)
    "r":   0x26,  # r (rak)
    "r̝":   0x26,  # ř (přítel) - mapováno na r

    # ── Afrikáty ───────────────────────────────────────────────────────────────
    "t͡s":  0x27,  # c (cesta)
    "t͡ʃ":  0x27,  # č (číst)

    # ── Ticho / jiné ───────────────────────────────────────────────────────────
    "sil": 0x00,
    "sp":  0x00,
    "spn": 0x00,
    "":    0x00,
}
