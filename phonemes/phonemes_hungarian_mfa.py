"""
phonemes_hungarian_mfa.py  ─  IPA → kódok Fallout 2 LIP
                              MFA modellhez: hungarian_mfa

A Fallout 2 LIP fonématáblázat alapján (Anchorite és Black_Electric).
A magyar IPA szimbólumokat a 41 szájforma-kódhoz rendeli.
Az IPA jelölések (hangsúly, hosszúság) a keresés előtt eltávolításra kerülnek.
"""

PHONEME_TABLE: dict[str, int] = {
    # ── Magánhangzók ──────────────────────────────────────────────────────────
    "i":   0x01,  # i (ír)
    "iː":  0x01,  # í (díj)
    "ɛ":   0x04,  # e (ejt)
    "eː":  0x04,  # é (kér)
    "ɒ":   0x06,  # a (alap)
    "aː":  0x06,  # á (ház)
    "o":   0x08,  # o (ott)
    "oː":  0x08,  # ó (hód)
    "ø":   0x08,  # ö (öt) - kerekített, mint az o
    "øː":  0x08,  # ő (hő) - kerekített, mint az o
    "u":   0x0A,  # u (ura)
    "uː":  0x0A,  # ú (húr)
    "y":   0x0A,  # ü (üt) - kerekített, mint az u
    "yː":  0x0A,  # ű (hű) - kerekített, mint az u

    # ── Zárhangok ─────────────────────────────────────────────────────────────
    "p":   0x11,  # p (apa)
    "b":   0x12,  # b (baba)
    "t":   0x13,  # t (tó)
    "d":   0x14,  # d (duda)
    "c":   0x15,  # ty (tyúk) - map to k
    "ɟ":   0x16,  # gy (gyár) - map to g
    "k":   0x15,  # k (kő)
    "ɡ":   0x16,  # g (gép)

    # ── Réshangok ─────────────────────────────────────────────────────────────
    "f":   0x17,  # f (fa)
    "v":   0x18,  # v (víz)
    "s":   0x1B,  # sz (szép)
    "z":   0x1C,  # z (zene)
    "ʃ":   0x1D,  # s (só)
    "ʒ":   0x1E,  # zs (zsír)
    "h":   0x1F,  # h (ház)

    # ── Orrhangok és oldalhangok ──────────────────────────────────────────────
    "m":   0x20,  # m (mama)
    "n":   0x21,  # n (nap)
    "ɲ":   0x21,  # ny (anya)
    "ŋ":   0x22,  # n (przed k, g - mint "hang")
    "l":   0x23,  # l (ló)
    "r":   0x26,  # r (róka)

    # ── Zár-réshangok ─────────────────────────────────────────────────────────
    "t͡s":  0x27,  # c (cél)
    "d͡z":  0x28,  # dz (edz)
    "t͡ʃ":  0x27,  # cs (cső)
    "d͡ʒ":  0x28,  # dzs (dzsungel)

    # ── Csend / egyéb ─────────────────────────────────────────────────────────
    "sil": 0x00,
    "sp":  0x00,
    "spn": 0x00,
    "":    0x00,
}
