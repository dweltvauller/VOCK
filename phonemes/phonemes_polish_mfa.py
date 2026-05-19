"""
phonemes_polish_mfa.py  ─  IPA → kody Fallout 2 LIP
                           Dla modelu MFA: polish_mfa

Oparte na tabeli fonemów Fallout 2 LIP autorstwa Anchorite i Black_Electric.
Mapuje polskie symbole IPA na 41 kodów kształtu ust.
Znaczniki IPA (akcent, długość) są usuwane przed wyszukiwaniem.
"""

POLISH_IPA_TO_LIP: dict[str, int] = {
    # ── Samogłoski ─────────────────────────────────────────────────────────────
    "i":   0x01,  # i (iść)
    "ɨ":   0x09,  # y (syn)
    "ɛ":   0x04,  # e (ten)
    "a":   0x06,  # a (tak)
    "ɔ":   0x07,  # o (on)
    "u":   0x0A,  # u, ó (ucho)

    # ── Samogłoski nosowe ──────────────────────────────────────────────────────
    "ɛ̃":   0x21,  # ę (węże) - mapowanie na nosowe
    "ɔ̃":   0x22,  # ą (wąwóz) - mapowanie na nosowe

    # ── Spółgłoski zwarte ──────────────────────────────────────────────────────
    "p":   0x11,  # p (pan)
    "b":   0x12,  # b (baba)
    "t":   0x13,  # t (tam)
    "d":   0x14,  # d (dom)
    "k":   0x15,  # k (kot)
    "ɡ":   0x16,  # g (góra)
    "c":   0x15,  # ć (ćma) - mapowanie na k
    "ɟ":   0x16,  # dź (dźwig) - mapowanie na g

    # ── Spółgłoski szczelinowe ────────────────────────────────────────────────
    "f":   0x17,  # f (fala)
    "v":   0x18,  # w (woda)
    "s":   0x1B,  # s (ser)
    "z":   0x1C,  # z (zima)
    "ʂ":   0x1D,  # sz (szum)
    "ʐ":   0x1E,  # ż, rz (żaba)
    "ɕ":   0x1D,  # ś (śnieg)
    "ʑ":   0x1E,  # ź (źle)
    "x":   0x1F,  # ch, h (chleb)

    # ── Spółgłoski nosowe i płynne ─────────────────────────────────────────────
    "m":   0x20,  # m (mama)
    "n":   0x21,  # n (nos)
    "ɲ":   0x21,  # ń (koń)
    "ŋ":   0x22,  # ń (przed k, g - np. bank)
    "l":   0x23,  # l (las)
    "w":   0x24,  # ł (łódź)
    "r":   0x26,  # r (rak)

    # ── Afrykaty ──────────────────────────────────────────────────────────────
    "t͡s":  0x27,  # c (co)
    "d͡z":  0x28,  # dz (dzwon)
    "t͡ʂ":  0x27,  # cz (czas)
    "d͡ʐ":  0x28,  # dż (dżem)
    "t͡ɕ":  0x27,  # ć (ciocia)
    "d͡ʑ":  0x28,  # dź (dźwig)

    # ── Cisza / inne ──────────────────────────────────────────────────────────
    "sil": 0x00,
    "sp":  0x00,
    "spn": 0x00,
    "":    0x00,
}

def ipa_to_lip_code(phoneme: str) -> int:
    """
    Usuwa znaczniki IPA i zwraca kod Fallout 2 LIP.
    """
    import re
    # Usuwa znaczniki długości (ː), akcentu (ˈ, ˌ) i inne diakrytyki
    p = re.sub(r"[ːˈˌ]", "", phoneme.strip().lower())
    return POLISH_IPA_TO_LIP.get(p, 0x0D)