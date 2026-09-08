"""Validation et échappement des identifiants SQL fournis par l'utilisateur.

Aucun nom de schéma, de table ou de commande n'est jamais concaténé
directement dans une requête sans être passé par validate_identifier()
puis quote_ident() (ou qualified_table()).
"""

import re

_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


class InvalidIdentifierError(ValueError):
    pass


def validate_identifier(name, label="identifiant"):
    """Vérifie qu'un nom (schéma, table, commande...) est un identifiant
    PostgreSQL simple et sûr : minuscules, chiffres, underscore, commence
    par une lettre. Lève InvalidIdentifierError sinon. Renvoie le nom."""
    if not isinstance(name, str) or not _IDENTIFIER_RE.match(name):
        raise InvalidIdentifierError(
            "{} invalide : {!r}. Seuls les caractères a-z, 0-9 et _ sont "
            "autorisés, en commençant par une lettre minuscule "
            "(63 caractères maximum).".format(label, name)
        )
    return name


def quote_ident(name):
    """Échappe un identifiant déjà validé pour l'insérer entre guillemets
    doubles dans du SQL (protection contre les guillemets doubles internes,
    même si validate_identifier() les interdit déjà)."""
    return '"' + str(name).replace('"', '""') + '"'


def qualified_table(schema, table):
    return "{}.{}".format(quote_ident(schema), quote_ident(table))


def validate_millesime(value):
    try:
        year = int(value)
    except (TypeError, ValueError):
        raise InvalidIdentifierError("Millésime invalide : {!r}.".format(value))
    if not (2000 <= year <= 2100):
        raise InvalidIdentifierError(
            "Millésime hors plage plausible (2000-2100) : {}.".format(year)
        )
    return year
