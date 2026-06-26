# Import Python packages
## None

# Import modules from Python packages
## None

# Import third party packages
## None

# Import modules from third party packages
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

# Import personal functions
## None

# Custom variable type construction
## None

# -----

class GuiImportPageClass(QWidget):
    """
    Page Import (vue uniquement).
    Contient les boutons d'import, le bouton d'export modèle,
    et un tableau d'historique des imports de la session.
    La logique est dans CmdImportPageClass.
    """

    def __init__(self) -> None:
        super().__init__()
        self.init_ui_method()
        return None

    # -----

    def init_ui_method(self) -> None:
        """ Création de la mise en page de la page Import """

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        # ── En-tête ──────────────────────────────────────────────────────────
        title_label = QLabel("Import des données")
        title_label.setObjectName("pageTitle")
        subtitle_label = QLabel(
            "Importez les transactions (fichier Excel brut) et les accords commerciaux. "
            "Les tables de référence (marques, catégories, distributeurs…) "
            "sont mises à jour automatiquement lors de l'import."
        )
        subtitle_label.setObjectName("subtitle")
        subtitle_label.setWordWrap(True)

        # ── Boutons d'action ─────────────────────────────────────────────────
        buttons_layout = QHBoxLayout()

        self.button_import_transactions = QPushButton("Importer transactions")
        self.button_import_accords      = QPushButton("Importer accords")
        self.button_import_correspondances = QPushButton("Importer correspondances")
        self.button_export_template     = QPushButton("Exporter modèle accords")
        self.button_export_template.setObjectName("primaryButton")

        buttons_layout.addWidget(self.button_import_transactions)
        buttons_layout.addWidget(self.button_import_accords)
        buttons_layout.addWidget(self.button_import_correspondances)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.button_export_template)

        # ── Historique des imports ────────────────────────────────────────────
        history_label = QLabel("Historique des imports (session en cours)")

        self.table_imports = QTableWidget(0, 4)
        self.table_imports.setHorizontalHeaderLabels(["Type", "Fichier", "Statut", "Détail"])
        imports_header = self.table_imports.horizontalHeader()
        imports_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        imports_header.setStretchLastSection(True)
        # Le tableau d'historique est toujours en lecture seule
        self.table_imports.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Assemblage final
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addSpacing(10)
        layout.addLayout(buttons_layout)
        layout.addWidget(history_label)
        layout.addWidget(self.table_imports)

        return None
