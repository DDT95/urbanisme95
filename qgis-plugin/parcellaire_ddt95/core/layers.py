"""Ajout des résultats dans le projet QGIS, dans un sous-groupe nommé
d'après la commande.

Les trois couches (état, plan, comparaison) sont rangées dans un groupe
"état parcelle - <commande>" du panneau Couches plutôt qu'à la racine.
Relancer la même commande remplace le groupe existant (couches et
groupe supprimés puis recréés) plutôt que d'empiler les anciens
résultats — même logique que les autres plugins DDT95 (ex. « parcelles
inondées - <scénario> »).
"""

from qgis.core import QgsDataSourceUri, QgsProject, QgsVectorLayer

from . import sql_templates as tpl

GROUP_PREFIX = "état parcelle"


def _group_name(commande):
    return "{} - {}".format(GROUP_PREFIX, commande)


def _replace_group(project, commande):
    root = project.layerTreeRoot()
    gname = _group_name(commande)
    old = root.findGroup(gname)
    if old is not None:
        for layer_node in old.findLayers():
            project.removeMapLayer(layer_node.layerId())
        old.parent().removeChildNode(old)
    return root.insertGroup(0, gname)


def _make_layer(base_uri, schema, table, key_column, geometry_column=""):
    uri = QgsDataSourceUri(base_uri)
    uri.setDataSource(schema, table, geometry_column, "", key_column)
    return QgsVectorLayer(uri.uri(False), table, "postgres")


def load_results(pg_connection, schema, commande, project=None):
    """Charge (ou recharge) les trois résultats dans un sous-groupe
    "état parcelle - <commande>". L'état parcellaire est chargé sans
    géométrie (table attributaire), le plan comme couche polygonale :
    aucune manipulation des propriétés de la connexion PostgreSQL n'est
    nécessaire côté utilisateur."""
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
    for key, layer in layers.items():
        if not layer.isValid():
            raise RuntimeError(
                "La couche {} n'a pas pu être chargée (source invalide).".format(
                    names[key]
                )
            )
        layer.setName(names[key])

    group = _replace_group(project, commande)
    # Inséré en dernier = affiché en premier (insertLayer(0, ...) place
    # toujours tout en haut) : plan (carte) au-dessus, puis état, puis
    # comparaison en bas.
    for key in ("comparaison", "etat", "plan"):
        layer = layers[key]
        project.addMapLayer(layer, False)
        group.insertLayer(0, layer)
    group.setExpanded(True)
    return layers
