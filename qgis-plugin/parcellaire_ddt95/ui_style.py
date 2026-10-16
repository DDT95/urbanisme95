"""Habillage visuel du plugin : bannière en dégradé, pied de page, police
Marianne — même recette que les autres plugins DDT95 (ex. Parcelles
inondées), pour une identité visuelle cohérente d'un plugin à l'autre.
"""

import os

from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

HERE = os.path.dirname(__file__)
ICON_PATH = os.path.join(HERE, "resources", "icon.png")

AUTEUR = "Wilfried Koba"
NOM = "État et plan parcellaire by {}".format(AUTEUR)

# Mêmes couleurs que les autres plugins DDT95 du même auteur.
C1, C2, ACC, ACCD = "#3a1252", "#8e2d8e", "#8e2d8e", "#6e2270"


def version():
    try:
        with open(os.path.join(HERE, "..", "metadata.txt"), encoding="utf-8") as f:
            for line in f:
                if line.startswith("version="):
                    return line.strip().split("=", 1)[1]
    except Exception:
        pass
    return ""


def qss():
    return """
* {{ font-family: "Marianne", "Segoe UI", "Helvetica Neue", Arial, sans-serif; }}
QDialog {{ background: #f7f3f8; }}
QLabel {{ color: #2a1d30; font-size: 13px; }}
QLabel#muted {{ color: #7c6b85; font-size: 11px; font-style: italic; }}
QGroupBox {{
    font-weight: 600; border: 1px solid #d3c5d9; border-radius: 8px;
    margin-top: 10px; padding-top: 12px; background: white;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {acc}; }}
QLineEdit, QComboBox, QSpinBox {{
    background: white; border: 1px solid #d3c5d9; border-radius: 8px;
    padding: 6px 9px; min-height: 22px; font-size: 13px;
    selection-background-color: {acc};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border: 1.5px solid {acc}; }}
QPushButton {{
    background: white; border: 1px solid #d3c5d9; border-radius: 8px;
    padding: 7px 16px; color: #3a1252; font-size: 13px;
}}
QPushButton:hover {{ background: #f3e8f6; border-color: {acc}; }}
QPushButton:pressed {{ background: #e6d4ec; }}
QPushButton#primary {{
    background: {acc}; border: none; color: white; font-weight: 700; padding: 8px 22px;
}}
QPushButton#primary:hover {{ background: {accd}; }}
QTextEdit#report {{
    background: white; border: 1px solid #d3c5d9; border-radius: 8px;
    font-family: Consolas, "Courier New", monospace; font-size: 9.5pt; color: #2a1d30;
}}
QFrame#banner {{ background: white; border-bottom: 3px solid {acc}; }}
QLabel#bTitle {{ color: {c1}; font-size: 18px; font-weight: 800; background: transparent; }}
QLabel#bBy {{ color: #b8860b; font-size: 12px; font-weight: 700; background: transparent; letter-spacing: 0.5px; }}
QLabel#bSub {{ color: #7c6b85; font-size: 12px; background: transparent; }}
QLabel#bVer {{
    color: {acc}; background: #f3e8f6; border-radius: 9px;
    padding: 3px 10px; font-size: 11px; font-weight: 600;
}}
QFrame#footer {{ background: #ece3ef; }}
QFrame#footer QLabel {{ color: #6e5d78; font-size: 11px; background: transparent; }}
QLabel#busy {{ color: {acc}; font-size: 12px; font-weight: 700; background: transparent; }}
""".format(acc=ACC, accd=ACCD, c1=C1, c2=C2)


def banner(titre, sous_titre=""):
    f = QFrame()
    f.setObjectName("banner")
    f.setMinimumHeight(84)
    lay = QHBoxLayout(f)
    lay.setContentsMargins(22, 14, 22, 14)
    lay.setSpacing(14)

    icon_label = QLabel()
    icon_label.setStyleSheet("background: transparent;")
    icon_pixmap = QIcon(ICON_PATH).pixmap(QSize(160, 160))
    icon_label.setPixmap(
        icon_pixmap.scaledToHeight(48, Qt.SmoothTransformation)
    )
    lay.addWidget(icon_label)

    col = QVBoxLayout()
    col.setSpacing(1)
    title = QLabel(titre)
    title.setObjectName("bTitle")
    col.addWidget(title)
    by = QLabel("by {}".format(AUTEUR))
    by.setObjectName("bBy")
    col.addWidget(by)
    if sous_titre:
        sub = QLabel(sous_titre)
        sub.setObjectName("bSub")
        sub.setWordWrap(True)
        col.addWidget(sub)
    lay.addLayout(col, 1)

    v = version()
    if v:
        ver_label = QLabel("v" + v)
        ver_label.setObjectName("bVer")
        lay.addWidget(ver_label, 0, Qt.AlignTop)
    return f


def footer():
    f = QFrame()
    f.setObjectName("footer")
    lay = QHBoxLayout(f)
    lay.setContentsMargins(22, 6, 22, 6)
    lay.addWidget(
        QLabel("{}  -  Fichiers fonciers (DGFiP)  -  (c) 2026 {}".format(NOM, AUTEUR))
    )
    return f


def wrap(dlg, inner, titre, sous_titre=""):
    """Habille dlg (un QDialog) avec bannière + contenu (inner, un layout
    déjà rempli) + pied de page, et applique la feuille de style."""
    dlg.setStyleSheet(qss())
    body = QWidget()
    body.setLayout(inner)
    root = QVBoxLayout(dlg)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)
    root.addWidget(banner(titre, sous_titre))
    root.addWidget(body, 1)
    root.addWidget(footer())
    dlg.setWindowTitle("{} - {}".format(NOM, titre))
