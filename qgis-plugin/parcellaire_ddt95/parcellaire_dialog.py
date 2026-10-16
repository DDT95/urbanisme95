import os

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFont, QIcon, QPixmap
from qgis.PyQt.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from .core import generator
from .core.column_mapping import REFERENTIELS_PAR_MILLESIME
from .core.csv_import import CsvFormatError
from .core.db import DbError, list_postgres_connections
from .core.identifiers import InvalidIdentifierError
from .core.inspect_sources import diagnose
from .core.layers import load_results

MAX_ANOMALIES_AFFICHEES = 200

# Schéma de travail unique : figé ici plutôt que saisi à chaque fois.
SCHEMA_DE_TRAVAIL = "q_26_01_4825"

ICON_PATH = os.path.join(os.path.dirname(__file__), "resources", "icon.png")

# Palette sobre inspirée de l'identité de l'État (bleu Marianne / rouge),
# en accents discrets seulement : aucune fonctionnalité ne doit dépendre
# du style, qui doit rester lisible si le thème QGIS de l'utilisateur
# le remplace.
_STYLE = """
QGroupBox {
    font-weight: 600;
    border: 1px solid #d0d0d0;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #000091;
}
QPushButton {
    padding: 5px 14px;
    border-radius: 4px;
    border: 1px solid #b0b0b0;
}
QPushButton#primary {
    background-color: #000091;
    color: white;
    border: 1px solid #000091;
    font-weight: 600;
}
QPushButton#primary:hover {
    background-color: #1212b0;
}
QPushButton#primary:pressed {
    background-color: #00006b;
}
QTextEdit#report {
    font-family: Consolas, "Courier New", monospace;
    font-size: 9.5pt;
}
"""


class ParcellaireDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle("État et plan parcellaire — DDT95")
        self.setWindowIcon(QIcon(ICON_PATH))
        self.resize(720, 620)
        self.setStyleSheet(_STYLE)
        self._build_ui()
        self._refresh_connections()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addLayout(self._build_header())

        source_group = QGroupBox("Parcelles à traiter")
        source_form = QFormLayout()
        source_form.setLabelAlignment(Qt.AlignRight)

        csv_row = QHBoxLayout()
        self.csv_edit = QLineEdit()
        csv_btn = QPushButton("Parcourir…")
        csv_btn.clicked.connect(self._choose_csv)
        csv_row.addWidget(self.csv_edit)
        csv_row.addWidget(csv_btn)
        source_form.addRow("Fichier CSV", csv_row)

        source_vbox = QVBoxLayout()
        source_vbox.addLayout(source_form)

        csv_info = QLabel(
            "Colonnes acceptées (au choix, mélangeables ligne par ligne) :\n"
            "• idpar — identifiant complet à 14 caractères, prioritaire s'il est rempli\n"
            "• commune (code INSEE) + numero — ex. « A327 », section incluse\n"
            "• commune + section + numero, en colonnes séparées"
        )
        csv_info.setWordWrap(True)
        csv_info.setStyleSheet("color: #666; font-style: italic; font-size: 9pt;")
        source_vbox.addWidget(csv_info)
        source_group.setLayout(source_vbox)
        layout.addWidget(source_group)

        params_group = QGroupBox("Base et commande")
        params_form = QFormLayout()
        params_form.setLabelAlignment(Qt.AlignRight)

        conn_row = QHBoxLayout()
        self.connection_combo = QComboBox()
        refresh_btn = QPushButton("Actualiser")
        refresh_btn.clicked.connect(self._refresh_connections)
        conn_row.addWidget(self.connection_combo)
        conn_row.addWidget(refresh_btn)
        params_form.addRow("Connexion PostgreSQL", conn_row)

        self.commande_edit = QLineEdit()
        params_form.addRow("Nom de sortie", self.commande_edit)

        self.millesime_spin = QSpinBox()
        self.millesime_spin.setRange(
            min(REFERENTIELS_PAR_MILLESIME), max(REFERENTIELS_PAR_MILLESIME)
        )
        self.millesime_spin.setValue(max(REFERENTIELS_PAR_MILLESIME))
        params_form.addRow("Millésime des fichiers fonciers", self.millesime_spin)

        params_group.setLayout(params_form)
        layout.addWidget(params_group)

        buttons_row = QHBoxLayout()
        self.generate_btn = QPushButton("Générer les données")
        self.generate_btn.setObjectName("primary")
        self.generate_btn.clicked.connect(self._on_generate)
        self.verify_btn = QPushButton("Vérifier")
        self.verify_btn.clicked.connect(self._on_verify)
        self.diagnose_btn = QPushButton("Diagnostiquer les tables sources")
        self.diagnose_btn.clicked.connect(self._on_diagnose)
        buttons_row.addWidget(self.generate_btn)
        buttons_row.addWidget(self.verify_btn)
        buttons_row.addWidget(self.diagnose_btn)
        layout.addLayout(buttons_row)

        report_group = QGroupBox("Compte rendu")
        report_layout = QVBoxLayout()
        self.report = QTextEdit()
        self.report.setObjectName("report")
        self.report.setReadOnly(True)
        report_layout.addWidget(self.report)
        report_group.setLayout(report_layout)
        layout.addWidget(report_group, stretch=1)

    def _build_header(self):
        header = QHBoxLayout()
        header.setSpacing(12)

        logo = QLabel()
        pixmap = QPixmap(ICON_PATH)
        if not pixmap.isNull():
            logo.setPixmap(
                pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        header.addWidget(logo)

        titles = QVBoxLayout()
        titles.setSpacing(0)
        title = QLabel("État et plan parcellaire")
        title_font = QFont()
        title_font.setPointSize(13)
        title_font.setBold(True)
        title.setFont(title_font)
        subtitle = QLabel("DDT95 — Fichiers Fonciers")
        subtitle.setStyleSheet("color: #666;")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        header.addLayout(titles)
        header.addStretch(1)

        separator_container = QVBoxLayout()
        separator_container.addLayout(header)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        separator_container.addWidget(line)
        return separator_container

    def _refresh_connections(self):
        self.connection_combo.clear()
        try:
            names = list_postgres_connections()
        except DbError as exc:
            self._log("Erreur : {}".format(exc))
            return
        if not names:
            self._log("Aucune connexion PostgreSQL enregistrée dans QGIS.")
        self.connection_combo.addItems(names)
        pg_index = self.connection_combo.findText("PG")
        if pg_index >= 0:
            self.connection_combo.setCurrentIndex(pg_index)

    def _choose_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choisir le CSV des parcelles", "", "CSV (*.csv)"
        )
        if path:
            self.csv_edit.setText(path)

    def _log(self, message):
        self.report.append(message)
        QApplication.processEvents()

    def _current_params(self):
        return dict(
            connection_name=self.connection_combo.currentText().strip(),
            schema=SCHEMA_DE_TRAVAIL,
            commande=self.commande_edit.text().strip(),
            millesime=self.millesime_spin.value(),
            csv_path=self.csv_edit.text().strip(),
        )

    def _on_generate(self):
        params = self._current_params()
        if not params["connection_name"]:
            QMessageBox.warning(self, "Paramètre manquant", "Choisissez une connexion PostgreSQL.")
            return
        if not params["csv_path"]:
            QMessageBox.warning(self, "Paramètre manquant", "Choisissez un fichier CSV.")
            return

        try:
            existing = generator.existing_result_tables(
                params["connection_name"], params["schema"], params["commande"]
            )
        except (DbError, InvalidIdentifierError) as exc:
            QMessageBox.critical(self, "Erreur", str(exc))
            return

        if existing:
            reply = QMessageBox.question(
                self,
                "Tables existantes",
                "Les tables suivantes existent déjà pour la commande « {} » "
                "et seront remplacées :\n{}\n\nContinuer ?".format(
                    params["commande"], "\n".join(existing)
                ),
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        self.report.clear()
        try:
            conn, result = generator.generate(
                params["connection_name"],
                params["schema"],
                params["commande"],
                params["millesime"],
                params["csv_path"],
                progress=self._log,
            )
        except (CsvFormatError, InvalidIdentifierError, DbError) as exc:
            self._log("ERREUR : {}".format(exc))
            QMessageBox.critical(self, "Échec de la génération", str(exc))
            return
        except Exception as exc:  # ne jamais planter QGIS silencieusement
            self._log("ERREUR INATTENDUE : {}".format(exc))
            QMessageBox.critical(self, "Échec de la génération", str(exc))
            return

        self._show_bilan(result)

        try:
            load_results(conn, params["schema"], params["commande"])
            c = params["commande"]
            self._log(
                "Couches ajoutées au projet : etat_p_{c}, "
                "plans_parcellaire_{c}, comparaison_parcelles_{c}.".format(c=c)
            )
        except Exception as exc:
            self._log("Avertissement : couches non ajoutées ({}).".format(exc))

    def _on_verify(self):
        params = self._current_params()
        if not params["connection_name"] or not params["schema"] or not params["commande"]:
            QMessageBox.warning(
                self, "Paramètre manquant", "Renseignez connexion et nom de sortie."
            )
            return
        try:
            result = generator.verify(
                params["connection_name"], params["schema"], params["commande"]
            )
        except (DbError, InvalidIdentifierError) as exc:
            self._log("ERREUR : {}".format(exc))
            return
        self._show_bilan(result)

    def _on_diagnose(self):
        params = self._current_params()
        if not params["connection_name"]:
            QMessageBox.warning(self, "Paramètre manquant", "Choisissez une connexion PostgreSQL.")
            return
        try:
            report = diagnose(params["connection_name"], params["millesime"])
        except (DbError, InvalidIdentifierError) as exc:
            self._log("ERREUR : {}".format(exc))
            return
        for key, table, _actual, missing in report:
            self._log("--- {} ({}) ---".format(key, table))
            if missing:
                self._log("Colonnes attendues absentes : " + ", ".join(missing))
            else:
                self._log("Toutes les colonnes attendues sont présentes.")

    def _show_bilan(self, result):
        self._log("")
        self._log("=== Bilan ===")
        self._log("Parcelles dans le CSV : {}".format(result.csv_count))
        self._log("Lignes dans l'état parcellaire : {}".format(result.etat_count))
        self._log("Parcelles dans le plan : {}".format(result.plan_count))
        self._log("Anomalies : {}".format(result.comparaison_count))
        if result.comparaison_count:
            self._log("Détail des anomalies :")
            for idpar, anomalie in result.comparaison_rows[:MAX_ANOMALIES_AFFICHEES]:
                self._log("  - {} ({})".format(idpar, anomalie))
            reste = result.comparaison_count - MAX_ANOMALIES_AFFICHEES
            if reste > 0:
                self._log("  ... et {} de plus.".format(reste))
