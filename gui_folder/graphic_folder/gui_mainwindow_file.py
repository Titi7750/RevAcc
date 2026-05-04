# Import Python packages
import os

# Import modules from Python packages
## None

# Import third party packages
## None

# Import modules from third party packages
from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtWidgets import QWidget
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QFrame
from PyQt6.QtWidgets import QStackedWidget
from PyQt6.QtWidgets import QTableWidget
from PyQt6.QtWidgets import QHeaderView
from PyQt6.QtWidgets import QProgressBar
from PyQt6.QtWidgets import QListWidget

# Import personnal functions
## None

# Custom variable type construction
## None

# -----

class GuiMainWindowClass(QMainWindow):
    """ GUI Main Window Class """

    def __init__(self) -> None:
        """ GUI Main Window Class: initialisation Method """

        super().__init__()

        self.theme_file_path: str = os.path.join(
            os.getcwd(),
            "gui_folder",
            "resources_folder",
            "qss_folder",
            "gui_theme_file.qss"
        )
        with open(self.theme_file_path, "r") as f:
            self.setStyleSheet(f.read())

        self.init_ui_method()

        return None

    # -----

    def init_ui_method(self) -> None:
        """ GUI Main Window Class: initialisation of the UI components and layout """

        self.setWindowTitle("RevAcc - Calcul des revenus")
        self.resize(1300, 800)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QHBoxLayout(self.central_widget)

        self.init_sidebar_method()
        self.init_pages_method()

        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.pages)

        return None

    # -----

    def init_sidebar_method(self) -> None:
        """ GUI Main Window Class: initialisation of the sidebar with navigation buttons """

        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(230)
        self.sidebar_layout = QVBoxLayout(self.sidebar)

        self.logo_label = QLabel("RevAcc")
        self.logo_label.setObjectName("logoLabel")

        self.button_dashboard = QPushButton("Tableau de bord")
        self.button_import = QPushButton("Import")
        self.button_mapping = QPushButton("Mapping")
        self.button_calculation = QPushButton("Calcul")
        self.button_result = QPushButton("Résultats")
        self.button_anomalies = QPushButton("Anomalies")

        self.sidebar_layout.addWidget(self.logo_label)
        self.sidebar_layout.addSpacing(30)

        for button in [
            self.button_dashboard,
            self.button_import,
            self.button_mapping,
            self.button_calculation,
            self.button_result,
            self.button_anomalies
        ]:
            button.setObjectName("menuButton")
            self.sidebar_layout.addWidget(button)

        self.sidebar_layout.addStretch()

        return None

    # -----

    def init_pages_method(self) -> None:
        """ GUI Main Window Class: initialisation of the main content area with different pages for each section """

        self.pages = QStackedWidget()

        self.page_dashboard = self.create_dashboard_page_method()
        self.page_import = self.create_import_page_method()
        self.page_mapping = self.create_mapping_page_method()
        self.page_calculation = self.create_calculation_page_method()
        self.page_result = self.create_result_page_method()
        self.page_anomalies = self.create_anomalie_page_method()

        self.pages.addWidget(self.page_dashboard)
        self.pages.addWidget(self.page_import)
        self.pages.addWidget(self.page_mapping)
        self.pages.addWidget(self.page_calculation)
        self.pages.addWidget(self.page_result)
        self.pages.addWidget(self.page_anomalies)

        return None

    # -----

    def create_dashboard_page_method(self) -> QWidget:
        """ GUI Main Window Class: creation of the dashboard page """

        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Tableau de bord")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Vue globale du calcul automatisé des revenus issus des accords industriels.")
        subtitle.setObjectName("subtitle")

        kpi_layout = QHBoxLayout()

        self.kpi_revenus = self.create_kpi_card_method("Revenus calculés", "0 €")
        self.kpi_accords = self.create_kpi_card_method("Accords actifs", "0")
        self.kpi_produits = self.create_kpi_card_method("Produits mappés", "0")
        self.kpi_anomalies = self.create_kpi_card_method("Anomalies", "0")

        kpi_layout.addWidget(self.kpi_revenus)
        kpi_layout.addWidget(self.kpi_accords)
        kpi_layout.addWidget(self.kpi_produits)
        kpi_layout.addWidget(self.kpi_anomalies)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(20)
        layout.addLayout(kpi_layout)
        layout.addStretch()

        return page

    # -----

    def create_kpi_card_method(self, param_title: str, param_value: str) -> QFrame:
        """ GUI Main Window Class: creation of a KPI card with a title and a value """

        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)

        title_label = QLabel(param_title)
        title_label.setObjectName("kpiTitle")

        value_label = QLabel(param_value)
        value_label.setObjectName("kpiValue")

        layout.addWidget(title_label)
        layout.addWidget(value_label)

        card.value_label = value_label

        return card

    # -----

    def create_import_page_method(self) -> QWidget:
        """ GUI Main Window Class: creation of the import page """

        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Import des données")
        title.setObjectName("pageTitle")

        button_layout = QHBoxLayout()

        self.button_import_transactions = QPushButton("Importer transactions")
        self.button_import_produits = QPushButton("Importer produits")
        self.button_import_accords = QPushButton("Importer accords")

        button_layout.addWidget(self.button_import_transactions)
        button_layout.addWidget(self.button_import_produits)
        button_layout.addWidget(self.button_import_accords)

        self.table_imports = QTableWidget()
        self.table_imports.setColumnCount(3)
        self.table_imports.setHorizontalHeaderLabels(["Type", "Fichier", "Statut"])
        self.table_imports.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addWidget(title)
        layout.addLayout(button_layout)
        layout.addWidget(self.table_imports)

        return page

    # -----

    def create_mapping_page_method(self) -> QWidget:
        """ GUI Main Window Class: creation of the mapping page """

        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Mapping produits")
        title.setObjectName("pageTitle")

        self.table_mapping = QTableWidget()
        self.table_mapping.setColumnCount(4)
        self.table_mapping.setHorizontalHeaderLabels([
            "Produit fournisseur",
            "Produit interne",
            "Unité",
            "Statut"
        ])
        self.table_mapping.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addWidget(title)
        layout.addWidget(self.table_mapping)

        return page

    # -----

    def create_calculation_page_method(self) -> QWidget:
        """ GUI Main Window Class: creation of the calculation page """

        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Calcul des revenus")
        title.setObjectName("pageTitle")

        self.button_start_calculation = QPushButton("Démarrer le calcul")
        self.button_start_calculation.setObjectName("primaryButton")

        self.progress_calcul = QProgressBar()
        self.progress_calcul.setValue(0)

        self.label_calcul_status = QLabel("Aucun calcul lancé.")
        self.label_calcul_status.setObjectName("subtitle")

        layout.addWidget(title)
        layout.addWidget(self.button_start_calculation)
        layout.addWidget(self.progress_calcul)
        layout.addWidget(self.label_calcul_status)
        layout.addStretch()

        return page

    # -----

    def create_result_page_method(self) -> QWidget:
        """ GUI Main Window Class: creation of the results page """

        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Résultats")
        title.setObjectName("pageTitle")

        self.button_export_results = QPushButton("Exporter les résultats")

        self.table_resultats = QTableWidget()
        self.table_resultats.setColumnCount(5)
        self.table_resultats.setHorizontalHeaderLabels([
            "Fournisseur",
            "Période",
            "CA déclaré",
            "Taux accord",
            "Revenu"
        ])
        self.table_resultats.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addWidget(title)
        layout.addWidget(self.button_export_results)
        layout.addWidget(self.table_resultats)

        return page

    # -----

    def create_anomalie_page_method(self) -> QWidget:
        """ GUI Main Window Class: creation of the anomalies page """

        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Anomalies")
        title.setObjectName("pageTitle")

        self.list_anomalies = QListWidget()

        layout.addWidget(title)
        layout.addWidget(self.list_anomalies)

        return page

    # -----
