def classFactory(iface):
    from .parcellaire_plugin import ParcellairePlugin

    return ParcellairePlugin(iface)
