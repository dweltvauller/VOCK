"""
phonemes_spanish_mfa.py  ─  IPA → Fallout 2 LIP phoneme codes
                            Para el modelo MFA: spanish_mfa

Basado en la tabla de fonemas LIP de Fallout 2 por Anchorite y Black_Electric.
Mapea símbolos IPA estándar del español a los 41 códigos de forma de boca.
Los marcadores de estrés (ˈ, ˌ) y longitud (ː) del MFA se eliminan antes de la búsqueda.
"""

SPANISH_IPA_TO_LIP: dict[str, int] = {
    # ── Vocales ────────────────────────────────────────────────────────────────
    "i":   0x01,  # i:      sí
    "e":   0x04,  # e       mes
    "a":   0x06,  # ɑ:      la
    "o":   0x08,  # oʊ      no
    "u":   0x0A,  # u:      tu

    # ── Oclusivas y Aproximantes ──────────────────────────────────────────────
    "p":   0x11,  # oclusiva bilabial sorda (papa)
    "b":   0x12,  # oclusiva bilabial sonora (banco)
    "β":   0x12,  # aproximante bilabial (lavar)
    "t":   0x13,  # oclusiva dental sorda (todo)
    "d":   0x14,  # oclusiva dental sonora (dado)
    "ð":   0x1A,  # aproximante dental (lado)
    "k":   0x15,  # oclusiva velar sorda (casa)
    "ɡ":   0x16,  # oclusiva velar sonora (gato)
    "g":   0x16,  # variante ASCII
    "ɣ":   0x16,  # aproximante velar (lago)

    # ── Fricativas ────────────────────────────────────────────────────────────
    "f":   0x17,  # fricativa labiodental sorda (foca)
    "θ":   0x19,  # fricativa interdental sorda (zapato - peninsular)
    "s":   0x1B,  # fricativa alveolar sorda (sol)
    "z":   0x1C,  # fricativa alveolar sonora (mismo)
    "x":   0x1F,  # fricativa velar sorda (caja)
    "h":   0x1F,  # aspiración dialectal

    # ── Nasales ────────────────────────────────────────────────────────────────
    "m":   0x20,  # nasal bilabial (mamá)
    "n":   0x21,  # nasal alveolar (nene)
    "ɲ":   0x21,  # nasal palatal (año)
    "ŋ":   0x22,  # nasal velar (cinco)

    # ── Aproximantes y Líquidas ────────────────────────────────────────────────
    "l":   0x23,  # lateral alveolar (luna)
    "ʎ":   0x25,  # lateral palatal (calle)
    "w":   0x24,  # aproximante labiovelar (hueso)
    "j":   0x25,  # aproximante palatal (ya)
    "ʝ":   0x25,  # fricativa palatal (yo)
    "ɾ":   0x26,  # vibrante simple (pero)
    "r":   0x26,  # vibrante múltiple (perro)

    # ── Africadas ────────────────────────────────────────────────────────────
    "tʃ":  0x27,  # africada palatal sorda (chico)
    "t͡ʃ":  0x27,  # con barra de unión

    # ── Silencio / no habla ──────────────────────────────────────────────────
    "sil": 0x00,  # silencio
    "sp":  0x00,  # pausa corta
    "spn": 0x00,  # ruido hablado
    "":    0x00,
}

def ipa_to_lip_code(phoneme: str) -> int:
    """
    Elimina marcadores de IPA y devuelve el código LIP de Fallout 2.
    Usa 0x0D como valor predeterminado si el símbolo es desconocido.
    """
    import re
    # Elimina estrés primario (ˈ), secundario (ˌ) y marcas de longitud (ː)
    p = re.sub(r"[ˈˌː]", "", phoneme.strip().lower())
    return SPANISH_IPA_TO_LIP.get(p, 0x0D)