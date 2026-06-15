# Import Python packages
## None

# Import modules from Python packages
from pathlib import Path

# Import third party packages
## None

# Import modules from third party packages
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

# Import personal functions
## None

# Custom variable type construction
## None

# -----

# Chemin absolu vers le dossier resources (indépendant du répertoire de lancement)
_RESOURCES_DIR = Path(__file__).parent.parent / "resources_folder"

# -----

class GuiMainWindowClass(QMainWindow):
    """
    Fenêtre principale de l'application.
    Contient la sidebar de navigation et la zone de contenu en pages empilées.
    Les pages fonctionnelles sont injectées par CmdMainWindowClass.
    """

    def __init__(self) -> None:
        super().__init__()

        # Chargement du thème QSS depuis le dossier resources
        qss_path = _RESOURCES_DIR / "qss_folder" / "gui_theme_file.qss"
        with open(qss_path, "r") as qss_file:
            self.setStyleSheet(qss_file.read())

        self.init_ui_method()

        return None

    # -----

    def init_ui_method(self) -> None:
        """ Initialisation de la fenêtre : titre, taille, layout principal """

        self.setWindowTitle("RevAcc - Calcul des revenus")
        self.resize(1300, 800)

        # Widget central avec layout horizontal : sidebar | pages
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.init_sidebar_method()

        # Zone de contenu : QStackedWidget vide ici, pages ajoutées par CmdMainWindowClass
        self.pages = QStackedWidget()

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.pages)

        # Création de la page dashboard (sera ajoutée au stacked par CmdMainWindowClass)
        self.dashboard_page = self.create_dashboard_page_method()

        return None

    # -----

    def init_sidebar_method(self) -> None:
        """ Création de la barre latérale : logo, boutons de navigation, logo image """

        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(230)
        sidebar_layout = QVBoxLayout(self.sidebar)

        # Logo texte de l'application
        logo_label = QLabel("RevAcc")
        logo_label.setObjectName("logoLabel")

        # Logo Entegra (image redimensionnée)
        logo_image = QLabel()
        logo_image.setPixmap(
            QPixmap(str(_RESOURCES_DIR / "icons_folder" / "logo-entegra.png")).scaled(
                140, 60,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        logo_image.setObjectName("logoEntegra")
        logo_image.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Boutons de navigation (4 pages dans ce prototype)
        self.button_dashboard    = QPushButton("Tableau de bord")
        self.button_import       = QPushButton("Import")
        self.button_calculation  = QPushButton("Calcul")
        self.button_consultation = QPushButton("Consultation")

        # Assemblage du layout sidebar
        sidebar_layout.addWidget(logo_label)
        sidebar_layout.addSpacing(30)
        for nav_button in [
            self.button_dashboard,
            self.button_import,
            self.button_calculation,
            self.button_consultation,
        ]:
            nav_button.setObjectName("menuButton")
            sidebar_layout.addWidget(nav_button)
        sidebar_layout.addStretch()
        sidebar_layout.addWidget(logo_image)

        return None

    # -----

    def create_dashboard_page_method(self) -> QWidget:
        """ Création de la page tableau de bord avec les 4 cartes KPI """

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        # En-tête de la page
        title_label = QLabel("Tableau de bord")
        title_label.setObjectName("pageTitle")
        subtitle_label = QLabel(
            "Vue globale du calcul automatisé des revenus issus des accords industriels."
        )
        subtitle_label.setObjectName("subtitle")

        # Ligne de 4 cartes KPI côte à côte
        kpi_row = QHBoxLayout()
        self.kpi_revenus    = self.create_kpi_card_method("Revenus calculés",   "—")
        self.kpi_accords    = self.create_kpi_card_method("Accords actifs",     "0")
        self.kpi_produits   = self.create_kpi_card_method("Produits mappés",    "0")
        self.kpi_a_verifier = self.create_kpi_card_method("Données à vérifier", "0")
        kpi_row.addWidget(self.kpi_revenus)
        kpi_row.addWidget(self.kpi_accords)
        kpi_row.addWidget(self.kpi_produits)
        kpi_row.addWidget(self.kpi_a_verifier)

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addSpacing(20)
        layout.addLayout(kpi_row)
        layout.addStretch()

        return page

    # -----

    def create_kpi_card_method(self, param_title: str, param_initial_value: str) -> QFrame:
        """ Crée une carte KPI (cadre blanc) avec un titre gris et une valeur en grand """

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)

        title_label = QLabel(param_title)
        title_label.setObjectName("kpiTitle")

        value_label = QLabel(param_initial_value)
        value_label.setObjectName("kpiValue")

        card_layout.addWidget(title_label)
        card_layout.addWidget(value_label)

        # Attribut direct pour que CmdMainWindowClass puisse mettre à jour la valeur
        card.value_label = value_label

        return card
