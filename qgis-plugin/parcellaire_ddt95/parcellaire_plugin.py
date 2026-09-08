from qgis.PyQt.QtWidgets import QAction


class ParcellairePlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None

    def initGui(self):
        self.action = QAction("État et plan parcellaire...", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToDatabaseMenu("&Parcellaire DDT95", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.action is not None:
            self.iface.removePluginDatabaseMenu("&Parcellaire DDT95", self.action)
            self.iface.removeToolBarIcon(self.action)

    def run(self):
        if self.dialog is None:
            from .parcellaire_dialog import ParcellaireDialog

            self.dialog = ParcellaireDialog(self.iface)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
