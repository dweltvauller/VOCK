"""
phonemes_french_mfa.py  ─  IPA → codes Fallout 2 LIP
                           Pour le modèle MFA : french_mfa

Basé sur la table des phonèmes Fallout 2 LIP par Anchorite et Black_Electric.
Associe les symboles IPA du français aux 41 codes de forme de bouche.
Les marqueurs IPA (accent, longueur) sont supprimés avant la recherche.
"""

PHONEME_TABLE: dict[str, int] = {
    # ── Voyelles orales ────────────────────────────────────────────────────────
    "i":   0x01,  # i (rire)
    "e":   0x04,  # é (été)
    "ɛ":   0x04,  # è (fête)
    "a":   0x06,  # a (patte)
    "ɑ":   0x06,  # â (pâte)
    "o":   0x08,  # o (rose)
    "ɔ":   0x07,  # o (port)
    "u":   0x0A,  # ou (vous)
    "y":   0x0A,  # u (rue) - map to u
    "ø":   0x08,  # eu (peu) - map to o
    "ə":   0x0D,  # e (le)

    # ── Voyelles nasales ───────────────────────────────────────────────────────
    "ɛ̃":   0x21,  # in (vin) - map to nasal n
    "ɑ̃":   0x22,  # an (temps) - map to nasal ng
    "ɔ̃":   0x22,  # on (bon) - map to nasal ng

    # ── Occlusives ─────────────────────────────────────────────────────────────
    "p":   0x11,  # p (papa)
    "b":   0x12,  # b (bébé)
    "t":   0x13,  # t (tout)
    "d":   0x14,  # d (dada)
    "k":   0x15,  # k (kilo)
    "ɡ":   0x16,  # g (gare)

    # ── Fricatives ─────────────────────────────────────────────────────────────
    "f":   0x17,  # f (face)
    "v":   0x18,  # v (vent)
    "s":   0x1B,  # s (sel)
    "z":   0x1C,  # z (zéro)
    "ʃ":   0x1D,  # ch (chat)
    "ʒ":   0x1E,  # j (jour)

    # ── Nasales et Liquides ─────────────────────────────────────────────────────
    "m":   0x20,  # m (maman)
    "n":   0x21,  # n (non)
    "ɲ":   0x21,  # gn (gagner)
    "l":   0x23,  # l (loup)
    "ʁ":   0x26,  # r (rouge) - r grasseyé

    # ── Semi-voyelles ──────────────────────────────────────────────────────────
    "j":   0x25,  # y (yeux)
    "w":   0x24,  # ou (oui)
    "ɥ":   0x25,  # u (lui)

    # ── Silence / non-parlé ────────────────────────────────────────────────────
    "sil": 0x00,
    "sp":  0x00,
    "spn": 0x00,
    "":    0x00,
}
