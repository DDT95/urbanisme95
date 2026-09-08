"""Ajout des résultats dans le projet QGIS, nommés d'après la commande.

Les couches portent le nom réel de la commande (etat_p_<commande>,
plans_parcellaire_<commande>, comparaison_parcelles_<commande>), pour
qu'on puisse les distinguer clairement pendant les tests. Les vues
PostgreSQL à nom fixe (tpl.ETAT_VUE_COURANTE, etc., maintenues par
generate()) restent disponibles en base pour une future mise en page
qui aurait besoin d'un nom stable indépendant de la commande.
"""

from qgis.core import QgsDataSourceUri, QgsProject, QgsVectorLayer

from . import sql_templates as tpl


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
    """Charge (ou recharge) les trois résultats sous des noms reprenant la
    commande. L'état parcellaire est chargé sans géométrie (table
    attributaire), le plan comme couche polygonale : aucune manipulation
    des propriétés de la connexion PostgreSQL n'est nécessaire côté
    utilisateur."""
    project = project or QgsProject.instance()
    base_uri = pg_connection.uri()

    names = {
        "etat": tpl.etat_table_name(commande),
        "plan": tpl.plan_table_name(commande),
        "comparaison": tpl.comparaison_table_name(commande),
    }

    layers = {
        "etat": _make_layer(base_uri, schema, names["etat"], "etat_id"),
        "plan": _make_layer(
            base_uri, schema, names["plan"], "plan_id", geometry_column="geompar"
        ),
        "comparaison": _make_layer(base_uri, schema, names["comparaison"], "comparaison_id"),
    }

    loaded = {}
    for key, layer in layers.items():
        if not layer.isValid():
            raise RuntimeError(
                "La couche {} n'a pas pu être chargée (source invalide).".format(
                    names[key]
                )
            )
        loaded[key] = _replace_layer(project, names[key], layer)
    return loaded
