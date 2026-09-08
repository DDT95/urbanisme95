"""Accès aux connexions PostgreSQL déjà enregistrées dans QGIS.

Aucune information de connexion (hôte, utilisateur, mot de passe) n'est
stockée ou manipulée ici : on récupère un objet de connexion QGIS déjà
configuré par son nom, et QGIS se charge de l'authentification (gestionnaire
d'authentification QGIS / mot de passe demandé à la volée si besoin).
"""

from qgis.core import QgsProviderRegistry


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


class PgConnection:
    """Enveloppe une connexion PostgreSQL déjà enregistrée dans QGIS.

    Utilise directement l'objet de connexion tel que géré par QGIS
    (metadata.findConnection), sans le reconstruire à partir de son URI :
    une reconstruction perd les réglages qui ne sont pas représentables
    dans une simple chaîne de connexion (authcfg, SSL, service PostgreSQL...),
    ce qui empêchait certaines connexions de production de fonctionner
    alors qu'une connexion simple (sans ces réglages) fonctionnait."""

    def __init__(self, connection_name):
        self.connection_name = connection_name
        self._conn = _postgres_metadata().findConnection(connection_name)
        if self._conn is None:
            raise DbError(
                "La connexion PostgreSQL « {} » n'existe pas ou n'est pas "
                "enregistrée dans QGIS.".format(connection_name)
            )

    def uri(self):
        return self._conn.uri()

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
            "« {} ». Vérifiez que ce poste peut atteindre ce serveur sur le "
            "réseau (VPN, même réseau local...) avant de réessayer.\n"
            "Détail : {}".format(connection_name, text)
        )
    if "asgard" in lowered and "create schema" in lowered:
        return (
            "Le schéma demandé n'existe pas encore, et cette base utilise "
            "Asgard pour gérer les schémas : il ne peut pas être créé "
            "automatiquement par une simple requête. Faites créer ce "
            "schéma via le mécanisme habituel (Asgard) avant de relancer, "
            "ou utilisez un schéma déjà existant.\nDétail : {}".format(text)
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
