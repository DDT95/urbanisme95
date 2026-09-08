"""Accès aux connexions PostgreSQL déjà enregistrées dans QGIS.

Aucune information de connexion (hôte, utilisateur, mot de passe) n'est
stockée ou manipulée ici : on récupère un objet de connexion QGIS déjà
configuré par son nom, et QGIS se charge de l'authentification (gestionnaire
d'authentification QGIS / mot de passe demandé à la volée si besoin).
"""

from qgis.core import QgsDataSourceUri, QgsProviderRegistry

# Délai maximal (secondes) pour établir la connexion PostgreSQL. Sans cela,
# une base injoignable (mauvais réseau, VPN coupé, pare-feu qui ignore les
# paquets) fait attendre QGIS indéfiniment sans le moindre message, ce qui
# ressemble à un gel de l'application.
CONNECT_TIMEOUT_SECONDS = 15


class DbError(Exception):
    pass


def _postgres_metadata():
    metadata = QgsProviderRegistry.instance().providerMetadata("postgres")
    if metadata is None:
        raise DbError(
            "Le fournisseur PostgreSQL n'est pas disponible dans cette "
            "installation QGIS."
        )
    return metadata


def list_postgres_connections():
    """Liste les noms des connexions PostgreSQL enregistrées dans QGIS."""
    return sorted(_postgres_metadata().connections().keys())


def _with_connect_timeout(uri_string):
    uri = QgsDataSourceUri(uri_string)
    uri.setParam("connect_timeout", str(CONNECT_TIMEOUT_SECONDS))
    return uri.uri(False)


class PgConnection:
    """Enveloppe une connexion PostgreSQL déjà enregistrée dans QGIS."""

    def __init__(self, connection_name):
        self.connection_name = connection_name
        metadata = _postgres_metadata()
        stored = metadata.findConnection(connection_name)
        if stored is None:
            raise DbError(
                "La connexion PostgreSQL « {} » n'existe pas ou n'est pas "
                "enregistrée dans QGIS.".format(connection_name)
            )
        self._timeout_uri = _with_connect_timeout(stored.uri())
        try:
            self._conn = metadata.createConnection(self._timeout_uri, {})
        except Exception:
            # Repli sur la connexion enregistrée si la reconstruction avec
            # délai d'expiration échoue pour une raison quelconque.
            self._conn = stored

    def uri(self):
        """URI de connexion (avec connect_timeout) utilisée pour construire
        les couches QGIS (import CSV, chargement des résultats)."""
        return self._timeout_uri

    def execute(self, sql):
        try:
            return self._conn.executeSql(sql)
        except Exception as exc:
            raise DbError(_friendly_message(exc, self.connection_name)) from exc

    def table_exists(self, schema, table):
        try:
            tables = self._conn.tables(schema)
        except Exception as exc:
            raise DbError(_friendly_message(exc, self.connection_name)) from exc
        return any(t.tableName() == table for t in tables)

    def begin(self):
        self.execute("BEGIN")

    def commit(self):
        self.execute("COMMIT")

    def rollback(self):
        self.execute("ROLLBACK")

    def transaction(self):
        return _Transaction(self)


def _friendly_message(exc, connection_name):
    text = str(exc)
    lowered = text.lower()
    if "timeout" in lowered or "timed out" in lowered or "could not connect" in lowered:
        return (
            "Impossible de joindre le serveur PostgreSQL de la connexion "
            "« {} » (délai de {} s dépassé). Vérifiez que ce poste peut "
            "atteindre ce serveur sur le réseau (VPN, même réseau local...) "
            "avant de réessayer.\nDétail : {}".format(
                connection_name, CONNECT_TIMEOUT_SECONDS, text
            )
        )
    return text


class _Transaction:
    def __init__(self, conn):
        self._conn = conn

    def __enter__(self):
        self._conn.begin()
        return self._conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._conn.commit()
        else:
            try:
                self._conn.rollback()
            except DbError:
                pass
        return False
