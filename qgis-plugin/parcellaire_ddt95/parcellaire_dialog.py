from qgis.PyQt.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
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
from .core.csv_import import CsvFormatError
from .core.db import DbError, list_postgres_connections
from .core.identifiers import InvalidIdentifierError
from .core.inspect_sources import diagnose
from .core.layers import load_results

MAX_ANOMALIES_AFFICHEES = 200


class ParcellaireDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle("État et plan parcellaire")
        self.resize(680, 580)
        self._build_ui()
        self._refresh_connections()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        csv_row = QHBoxLayout()
        self.csv_edit = QLineEdit()
        csv_btn = QPushButton("Parcourir...")
        csv_btn.clicked.connect(self._choose_csv)
        csv_row.addWidget(self.csv_edit)
        csv_row.addWidget(csv_btn)
        form.addRow("Fichier CSV des parcelles", csv_row)

        conn_row = QHBoxLayout()
        self.connection_combo = QComboBox()
        refresh_btn = QPushButton("Actualiser")
        refresh_btn.clicked.connect(self._refresh_connections)
        conn_row.addWidget(self.connection_combo)
        conn_row.addWidget(refresh_btn)
        form.addRow("Connexion PostgreSQL", conn_row)

        self.schema_edit = QLineEdit()
        self.schema_edit.setPlaceholderText("q_26_01_4825")
        form.addRow("Schéma de travail", self.schema_edit)

        self.commande_edit = QLineEdit()
        form.addRow("Nom court de la commande", self.commande_edit)

        self.millesime_spin = QSpinBox()
        self.millesime_spin.setRange(2000, 2100)
        self.millesime_spin.setValue(2024)
        form.addRow("Millésime des fichiers fonciers", self.millesime_spin)

        layout.addLayout(form)

        buttons_row = QHBoxLayout()
        self.generate_btn = QPushButton("Générer les données")
        self.generate_btn.clicked.connect(self._on_generate)
        self.verify_btn = QPushButton("Vérifier")
        self.verify_btn.clicked.connect(self._on_verify)
        self.diagnose_btn = QPushButton("Diagnostiquer les tables sources")
        self.diagnose_btn.clicked.connect(self._on_diagnose)
        buttons_row.addWidget(self.generate_btn)
        buttons_row.addWidget(self.verify_btn)
        buttons_row.addWidget(self.diagnose_btn)
        layout.addLayout(buttons_row)

        layout.addWidget(QLabel("Compte rendu"))
        self.report = QTextEdit()
        self.report.setReadOnly(True)
        layout.addWidget(self.report)

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
            schema=self.schema_edit.text().strip(),
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
            self._log(
                "Couches ajoutées au projet : etat_parcellaire_courant, "
                "plan_parcellaire_courant, comparaison_courante."
            )
        except Exception as exc:
            self._log("Avertissement : couches non ajoutées ({}).".format(exc))

    def _on_verify(self):
        params = self._current_params()
        if not params["connection_name"] or not params["schema"] or not params["commande"]:
            QMessageBox.warning(
                self, "Paramètre manquant", "Renseignez connexion, schéma et commande."
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
