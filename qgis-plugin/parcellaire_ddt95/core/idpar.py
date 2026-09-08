"""Construction de l'identifiant parcellaire complet (idpar) à partir des
champs structurés commune (INSEE), préfixe, section et numéro.

La plupart des CSV fournis par les utilisateurs ne contiennent que le
code INSEE de la commune et le numéro de parcelle (parfois la section) —
pas un identifiant déjà concaténé et correctement formé. Le plugin
reconstruit donc toujours lui-même l'idpar plutôt que de faire confiance
à une éventuelle colonne 'id' du CSV, pour garantir un format cohérent
avec le référentiel Fichiers Fonciers : commune (5 car.) + préfixe
(3 car.) + section (2 car.) + numéro (4 car.), soit 14 caractères.
"""

import re

_COMMUNE_RE = re.compile(r"^\d{1,5}$")
_NUMERO_RE = re.compile(r"^\d{1,4}$")
_SECTION_RE = re.compile(r"^[A-Za-z0-9]{1,2}$")


class IdparFormatError(ValueError):
    pass


def build_idpar(commune, prefixe, section, numero):
    """Construit l'idpar (14 caractères) à partir des champs structurés.
    Lève IdparFormatError avec un message explicite si l'un des champs
    ne peut pas être mis en forme correctement."""
    commune = (commune or "").strip()
    prefixe = (prefixe or "").strip()
    section = (section or "").strip().upper()
    numero = (numero or "").strip()

    if not _COMMUNE_RE.match(commune):
        raise IdparFormatError(
            "Code commune (INSEE) invalide : {!r} (jusqu'à 5 chiffres "
            "attendus).".format(commune)
        )
    if prefixe and not prefixe.isdigit():
        raise IdparFormatError(
            "Préfixe invalide : {!r} (chiffres attendus, ou vide).".format(prefixe)
        )
    if not _SECTION_RE.match(section):
        raise IdparFormatError(
            "Section invalide : {!r} (1 ou 2 lettres/chiffres attendus).".format(section)
        )
    if not _NUMERO_RE.match(numero):
        raise IdparFormatError(
            "Numéro de parcelle invalide : {!r} (jusqu'à 4 chiffres "
            "attendus).".format(numero)
        )

    return "{}{}{}{}".format(
        commune.zfill(5),
        prefixe.zfill(3) if prefixe else "000",
        section.zfill(2),
        numero.zfill(4),
    )
