"""Ajout des résultats dans le projet QGIS sous des noms de couches fixes.

Les noms restent identiques d'une commande à l'autre (etat_parcellaire_courant,
plan_parcellaire_courant, comparaison_courante) afin que les mises en page
(Phase 3) n'aient jamais besoin d'être modifiées : seule la source de la
couche change à chaque nouvelle commande, pas son nom.
"""

from qgis.core import QgsDataSourceUri, QgsProject, QgsVectorLayer

from . import sql_templates as tpl

FIXED_LAYER_NAMES = {
    "etat": "etat_parcellaire_courant",
    "plan": "plan_parcellaire_courant",
    "comparaison": "comparaison_courante",
}


def _replace_layer(project, name, layer):
    for existing in project.mapLayersByName(name):
        project.removeMapLayer(existing.id())
    layer.setName(name)
    project.addMapLayer(layer)
    return layer


def _make_layer(base_uri, schema, table, key_column, geometry_column=""):
    uri = QgsDataSourceUri(base_uri)
    uri.setDataSource(schema, table, geometry_column, "", key_column)
    return QgsVectorLayer(uri.uri(False), table, "postgres")


def load_results(pg_connection, schema, commande, project=None):
    """Charge (ou recharge) les trois résultats sous leurs noms fixes, à
    partir des vues stables (tpl.ETAT_VUE_COURANTE, etc.) que generate()
    vient de repointer vers la commande courante — pas des tables
    suffixées par la commande, pour que ces couches restent stables même
    si generator.create_vues_courantes_sql() change un jour de stratégie.
    L'état parcellaire est chargé sans géométrie (table attributaire),
    le plan est chargé comme couche polygonale : aucune manipulation des
    propriétés de la connexion PostgreSQL n'est nécessaire côté utilisateur."""
    project = project or QgsProject.instance()
    base_uri = pg_connection.uri()

    layers = {
        "etat": _make_layer(base_uri, schema, tpl.ETAT_VUE_COURANTE, "etat_id"),
        "plan": _make_layer(
            base_uri,
            schema,
            tpl.PLAN_VUE_COURANTE,
            "plan_id",
            geometry_column="geompar",
        ),
        "comparaison": _make_layer(
            base_uri,
            schema,
            tpl.COMPARAISON_VUE_COURANTE,
            "comparaison_id",
        ),
    }

    loaded = {}
    for key, layer in layers.items():
        if not layer.isValid():
            raise RuntimeError(
                "La couche {} n'a pas pu être chargée (source invalide).".format(
                    FIXED_LAYER_NAMES[key]
                )
            )
        loaded[key] = _replace_layer(project, FIXED_LAYER_NAMES[key], layer)
    return loaded
