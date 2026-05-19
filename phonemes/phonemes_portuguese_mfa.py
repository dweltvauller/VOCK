"""
phonemes_portuguese_mfa.py  ─  IPA → códigos Fallout 2 LIP
                               Para o modelo MFA: portuguese_mfa

Baseado na tabela de fonemas LIP de Fallout 2 por Anchorite e Black_Electric.
Associa os símbolos IPA do português aos 41 códigos de forma da boca.
Os marcadores IPA (acento, comprimento) são removidos antes da busca.
"""

PORTUGUESE_IPA_TO_LIP: dict[str, int] = {
    # ── Vogais Orais ───────────────────────────────────────────────────────────
    "i":   0x01,  # i (vida)
    "e":   0x04,  # ê (você)
    "ɛ":   0x04,  # é (pé)
    "a":   0x06,  # a (casa)
    "ɔ":   0x07,  # ó (avó)
    "o":   0x08,  # ô (avô)
    "u":   0x0A,  # u (lua)
    "ɐ":   0x06,  # a (átomo) - map to open 'a'

    # ── Vogais Nasais ──────────────────────────────────────────────────────────
    "ɐ̃":   0x21,  # ã (lã) - map to nasal n
    "ẽ":   0x21,  # en (tempo)
    "ĩ":   0x21,  # in (lindo)
    "õ":   0x22,  # õ (põe) - map to nasal ng
    "ũ":   0x22,  # un (mundo)

    # ── Oclusivas ──────────────────────────────────────────────────────────────
    "p":   0x11,  # p (pato)
    "b":   0x12,  # b (bola)
    "t":   0x13,  # t (tatu)
    "d":   0x14,  # d (dedo)
    "k":   0x15,  # c (casa)
    "ɡ":   0x16,  # g (gato)

    # ── Fricativas ─────────────────────────────────────────────────────────────
    "f":   0x17,  # f (faca)
    "v":   0x18,  # v (uva)
    "s":   0x1B,  # s (sapo)
    "z":   0x1C,  # z (zebra)
    "ʃ":   0x1D,  # ch (chave)
    "ʒ":   0x1E,  # j (janela)

    # ── Nasais e Líquidas ──────────────────────────────────────────────────────
    "m":   0x20,  # m (mapa)
    "n":   0x21,  # n (navio)
    "ɲ":   0x21,  # nh (ninho)
    "l":   0x23,  # l (lata)
    "ʎ":   0x25,  # lh (filho)
    "ɾ":   0x26,  # r (arara)
    "ʁ":   0x26,  # r (rato) - R forte/aspirado

    # ── Africadas ─────────────────────────────────────────────────────────────
    "tʃ":  0x27,  # t (tchau) - comum em certos dialetos
    "dʒ":  0x28,  # d (dia)   - comum em certos dialetos

    # ── Silêncio / não-falado ──────────────────────────────────────────────────
    "sil": 0x00,
    "sp":  0x00,
    "spn": 0x00,
    "":    0x00,
}

def ipa_to_lip_code(phoneme: str) -> int:
    """
    Remove marcadores IPA e retorna o código LIP de Fallout 2.
    """
    import re
    # Remove marcadores de comprimento (ː), estresse (ˈ, ˌ) e ligaduras
    p = re.sub(r"[ːˈˌ]", "", phoneme.strip().lower())
    return PORTUGUESE_IPA_TO_LIP.get(p, 0x0D)