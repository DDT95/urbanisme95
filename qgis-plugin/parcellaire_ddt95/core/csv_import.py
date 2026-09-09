"""Lecture du CSV de parcelles et import dans la table de staging PostgreSQL.

read_csv_rows() est pur Python (aucune dépendance QGIS) et donc testable
sans QGIS installé. insert_rows() insère les lignes via des instructions
INSERT (valeurs échappées par sql_string_literal, jamais d'identifiant
utilisateur concaténé) exécutées sur la MÊME connexion PostgreSQL que le
reste du traitement (core.db.PgConnection.execute) — pas de connexion
séparée : une connexion distincte ouverte pendant que la connexion
principale tient encore un verrou sur la table de staging (créée dans la
même transaction, pas encore validée) resterait bloquée indéfiniment en
attente de ce verrou. C'est exactement ce qui provoquait un blocage
silencieux de QGIS à cette étape.

IMPORTANT : quand des colonnes commune/section/numéro sont disponibles,
l'idpar utilisé pour la jointure avec le référentiel est TOUJOURS
reconstruit à partir d'elles (jamais pris tel quel dans une colonne 'id'
générique, souvent absente ou héritée d'un ancien export qui ne
correspond plus au millésime courant). Il arrive aussi qu'on nous donne
directement l'idpar complet (14 caractères) sans commune/numéro
séparés — une colonne explicitement nommée 'idpar' est alors acceptée et
utilisée directement (après validation de son format), en plus des
formats à 2-3 colonnes (commune + numéro, ou commune + section + numéro).
"""

import csv
import re

from .identifiers import qualified_table, sql_string_literal
from .idpar import IdparFormatError, build_idpar

REQUIRED_FIELDS = ("commune", "section", "numero")
OPTIONAL_FIELDS = ("id", "prefixe", "contenance", "created", "updated", "layer")
ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS

# En-têtes acceptés pour une colonne "section"+"numero" fusionnée en une
# seule colonne, séparés par un espace (ex. en-tête "section numero" sans
# virgule -> une seule colonne CSV, valeur "A 327").
_COMBINED_HEADER_ALIASES = {"sectionnumero", "numerosection"}

# En-têtes acceptés pour une colonne "numéro de parcelle" qui contient à
# elle seule la référence complète section+numéro (ex. "A327"), quand il
# n'y a ni colonne "section" séparée ni en-tête combiné explicite.
_NUMERO_COLUMN_ALIASES = {
    "numero",
    "numeroparcelle",
    "parcelle",
    "numparcelle",
    "numparc",
    "referenceparcelle",
    "refparcelle",
    "referencecadastrale",
    "refcadastrale",
}

# Lettre(s) de section (1 ou 2, avec un éventuel "0" de bourrage devant)
# suivies du numéro, avec ou sans séparateur entre les deux.
_COMBINED_REFERENCE_RE = re.compile(r"^0?([A-Za-z]{1,2})[\s\-/_.]*?(\d+)$")

# En-tête accepté pour une colonne idpar complet, déjà mis en forme
# (14 caractères). Volontairement distinct de "id" (trop générique, et
# c'est justement une colonne 'id' non fiable qui a causé des faux
# négatifs par le passé) : seul un en-tête explicite 'idpar' est reconnu.
_IDPAR_COLUMN_ALIASES = {"idpar"}

# commune (5 chiffres) + préfixe (3 chiffres) + section (2 car.) + numéro
# (4 chiffres) = 14 caractères, format idpar standard Fichiers Fonciers.
_IDPAR_RE = re.compile(r"^(\d{5})(\d{3})([A-Za-z0-9]{2})(\d{4})$")


def _parse_idpar(value):
    """Décompose un idpar complet (14 caractères) en (commune, prefixe,
    section, numero). Renvoie None si la valeur ne correspond pas au
    format attendu."""
    value = (value or "").strip()
    match = _IDPAR_RE.match(value)
    if not match:
        return None
    return match.groups()

# Nombre de lignes par instruction INSERT (évite une requête unique
# démesurée sur un très gros CSV, sans multiplier les allers-retours réseau).
BATCH_SIZE = 500


class CsvFormatError(ValueError):
    pass


def _normalize_header(name):
    return re.sub(r"[\s_]+", "", name).strip().lower()


def _split_combined_reference(value):
    """Découpe une référence cadastrale combinée ('A327', 'A 327',
    'AA0028'...) en (section, numero). Renvoie (None, None) si la valeur
    ne peut pas être décomposée (ex. vide, ou sans lettre de section)."""
    value = (value or "").strip()
    if not value:
        return "", ""
    match = _COMBINED_REFERENCE_RE.match(value)
    if not match:
        return None, None
    return match.group(1).upper(), match.group(2)


def read_csv_rows(path, encoding="utf-8-sig"):
    """Lit le CSV et renvoie une liste de dict avec les colonnes ALL_FIELDS.
    Accepte indifféremment : une colonne 'idpar' complète (14 caractères,
    prioritaire quand aucune colonne 'section' n'est présente), des
    colonnes 'section' et 'numero' séparées, une colonne combinée
    ('section numero' -> 'A 327'), ou une simple colonne 'numero' (ou
    alias : parcelle, numero_parcelle...) contenant la référence complète
    ('A327'). Ignore les lignes incomplètes. Lève CsvFormatError si le
    fichier est vide, si des colonnes obligatoires manquent, ou si un
    idpar ne peut pas être construit/lu."""
    with open(path, newline="", encoding=encoding) as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if fieldnames is None:
            raise CsvFormatError("Le fichier CSV est vide.")

        normalized = {_normalize_header(name): name for name in fieldnames}
        has_section_col = "section" in fieldnames
        has_numero_col = "numero" in fieldnames

        combined_header = None
        if not (has_section_col and has_numero_col):
            for alias in _COMBINED_HEADER_ALIASES:
                if alias in normalized:
                    combined_header = normalized[alias]
                    break

        idpar_source = None
        for alias in _IDPAR_COLUMN_ALIASES:
            if alias in normalized:
                idpar_source = normalized[alias]
                break

        combined_numero_source = None
        if not has_section_col and combined_header is None:
            for alias in _NUMERO_COLUMN_ALIASES:
                if alias in normalized:
                    combined_numero_source = normalized[alias]
                    break

        has_commune_route = (
            (has_section_col and has_numero_col)
            or combined_header is not None
            or combined_numero_source is not None
        )
        if idpar_source is None and "commune" not in fieldnames:
            raise CsvFormatError("Colonne manquante dans le CSV : commune")
        if idpar_source is None and not has_commune_route:
            raise CsvFormatError(
                "Colonnes manquantes dans le CSV : il faut au minimum "
                "'commune' et 'numero' (le numéro de parcelle peut inclure "
                "la section, ex. 'A327'), ou une colonne 'idpar' complète."
            )

        rows = []
        for line_no, raw_row in enumerate(reader, start=2):  # 1 = en-tête
            # 'idpar', quand rempli sur la ligne, est prioritaire (source la
            # plus directe) ; sinon on retombe sur commune/section/numero,
            # que ces colonnes soient présentes en plus ou à la place.
            raw_idpar = (raw_row.get(idpar_source) or "").strip() if idpar_source else ""
            if raw_idpar:
                parsed = _parse_idpar(raw_idpar)
                if parsed is None:
                    raise CsvFormatError(
                        "Ligne {} du CSV : idpar {!r} illisible (14 "
                        "caractères attendus : commune 5 chiffres + préfixe "
                        "3 chiffres + section 2 caractères + numéro 4 "
                        "chiffres).".format(line_no, raw_idpar)
                    )
                commune, prefixe, section, numero = parsed
            elif has_commune_route:
                commune = (raw_row.get("commune") or "").strip()
                prefixe = (raw_row.get("prefixe") or "").strip()

                if has_section_col and has_numero_col:
                    section = (raw_row.get("section") or "").strip()
                    numero = (raw_row.get("numero") or "").strip()
                elif combined_header is not None:
                    parts = (raw_row.get(combined_header) or "").split(None, 1)
                    section = parts[0] if parts else ""
                    numero = parts[1].strip() if len(parts) > 1 else ""
                else:
                    raw_value = raw_row.get(combined_numero_source) or ""
                    section, numero = _split_combined_reference(raw_value)
                    if section is None:
                        raise CsvFormatError(
                            "Ligne {} du CSV : numéro de parcelle {!r} "
                            "illisible (format attendu : lettre(s) de "
                            "section suivie(s) du numéro, ex. « A327 » ou "
                            "« A 327 »).".format(line_no, raw_value.strip())
                        )

                if not (commune and section and numero):
                    continue
            else:
                # Colonne idpar présente mais vide sur cette ligne, et pas
                # d'autre source disponible : ligne ignorée.
                continue

            try:
                idpar = build_idpar(commune, prefixe, section, numero)
            except IdparFormatError as exc:
                raise CsvFormatError("Ligne {} du CSV : {}".format(line_no, exc)) from exc

            rows.append(
                {
                    "id": idpar,
                    "commune": commune,
                    "prefixe": prefixe,
                    "section": section,
                    "numero": numero,
                    "contenance": (raw_row.get("contenance") or "").strip(),
                    "created": (raw_row.get("created") or "").strip(),
                    "updated": (raw_row.get("updated") or "").strip(),
                    "layer": (raw_row.get("layer") or "").strip(),
                }
            )

    if not rows:
        raise CsvFormatError(
            "Aucune ligne exploitable (commune / numéro de parcelle, ou "
            "idpar) n'a été trouvée."
        )
    return rows


def insert_rows(conn, schema, table, rows, progress=None):
    """Insère les lignes lues du CSV dans la table de staging, par lots,
    sur `conn` (core.db.PgConnection) déjà utilisée pour le reste du
    traitement — dans la même transaction, sans connexion séparée."""
    target = qualified_table(schema, table)
    columns = ", ".join(ALL_FIELDS)
    total = 0
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start : start + BATCH_SIZE]
        values_sql = ",\n".join(
            "({})".format(
                ", ".join(
                    sql_string_literal(row[field]) if row[field] else "NULL"
                    for field in ALL_FIELDS
                )
            )
            for row in batch
        )
        conn.execute(
            "INSERT INTO {table} ({columns}) VALUES\n{values};".format(
                table=target, columns=columns, values=values_sql
            )
        )
        total += len(batch)
        if progress:
            progress(total, len(rows))
    return total
