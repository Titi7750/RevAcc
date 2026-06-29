# Import Python packages
## None

# Import modules from Python packages
## None

# Import third party packages
## None

# Import modules from third party packages
from PyQt6.QtWidgets import (
    QHeaderView,
    QLabel,
    QTabWidget,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

# Import personal functions
## None

# Custom variable type construction
## None

# -----

class GuiConsultationPageClass(QWidget):
    """
    Page Consultation (vue uniquement).
    Affiche toutes les tables de la base en lecture seule via des onglets.
    La logique de chargement est dans CmdConsultationPageClass.
    """

    def __init__(self) -> None:
        super().__init__()
        self.init_ui_method()
        return None

    # -----

    def init_ui_method(self) -> None:
        """ Création de la mise en page de la page Consultation """

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        # ── En-tête ──────────────────────────────────────────────────────────
        title_label = QLabel("Consultation des données")
        title_label.setObjectName("pageTitle")
        subtitle_label = QLabel(
            "Parcourez toutes les tables de la base de données (lecture seule). "
            "La modification sera disponible dans une version future."
        )
        subtitle_label.setObjectName("subtitle")
        subtitle_label.setWordWrap(True)

        # ── Onglets par table ─────────────────────────────────────────────────
        self.consultation_tabs = QTabWidget()

        # Onglets principaux
        self.table_consult_products = self.make_table_method(
            ["Produit", "Marque - Catégorie", "Unité", "Statut"]
        )
        self.table_consult_accords = self.make_table_method(
            ["Industriel", "Marque - Catégorie", "Taux"]
        )
        self.table_consult_transactions = self.make_table_method(
            ["Date", "Distributeur", "Produit", "Quantité", "Prix unit.", "Total"]
        )

        # Onglets référentiels
        self.table_consult_brands       = self.make_table_method(["Marque"])
        self.table_consult_categories   = self.make_table_method(["Catégorie"])
        self.table_consult_distributors = self.make_table_method(["Distributeur"])
        self.table_consult_industrials  = self.make_table_method(["Industriel"])
        self.table_consult_units        = self.make_table_method(["Unité"])
        self.table_consult_conversions  = self.make_table_method(
            ["Distributeur", "Code produit", "Unité transaction", "Unité accord", "Facteur de conversion"]
        )

        # Ajout des onglets dans le TabWidget
        self.consultation_tabs.addTab(self.table_consult_products,     "Produits")
        self.consultation_tabs.addTab(self.table_consult_accords,      "Accords")
        self.consultation_tabs.addTab(self.table_consult_transactions, "Transactions")
        self.consultation_tabs.addTab(self.table_consult_conversions,  "Correspondances")
        self.consultation_tabs.addTab(self.table_consult_brands,       "Marques")
        self.consultation_tabs.addTab(self.table_consult_categories,   "Catégories")
        self.consultation_tabs.addTab(self.table_consult_distributors, "Distributeurs")
        self.consultation_tabs.addTab(self.table_consult_industrials,  "Industriels")
        self.consultation_tabs.addTab(self.table_consult_units,        "Unités")

        # Assemblage final
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addWidget(self.consultation_tabs)

        return None

    # -----

    def make_table_method(self, param_headers: list) -> QTableWidget:
        """ Crée un QTableWidget en lecture seule avec les en-têtes données """

        table = QTableWidget(0, len(param_headers))
        table.setHorizontalHeaderLabels(param_headers)
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        return table
