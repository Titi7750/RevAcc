# Import Python packages
import os

# Import modules from Python packages
## None

# Import third party packages
## None

# Import modules from third party packages
from PyQt6.QtCore import Qt
from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QWidget
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QFrame
from PyQt6.QtWidgets import QTabBar
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtWidgets import QTabWidget
from PyQt6.QtWidgets import QHeaderView
from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QProgressBar
from PyQt6.QtWidgets import QTableWidget
from PyQt6.QtWidgets import QStackedWidget

# Import personnal functions
## None

# Custom variable type construction
## None

# -----

class TearOffTabBar(QTabBar):
    """ Tab bar that emits a signal when a tab is dragged far enough to tear off. """

    tearOffRequested = pyqtSignal(int, QPoint)

    # -----

    def __init__(self, parent=None) -> None:
        """ TearOffTabBar: initialisation method """

        super().__init__(parent)
        self._press_pos = None
        self._press_index = -1

        return None

    # -----

    def mousePressEvent(self, event) -> None:
        """ TearOffTabBar: mouse press event handler to start tracking for tear-off """

        self._press_pos = event.pos() # Store the position where the mouse was pressed
        self._press_index = self.tabAt(event.pos()) # Store the index of the tab that was pressed
        super().mousePressEvent(event)

        return None

    # -----

    def mouseMoveEvent(self, event) -> None:
        """ TearOffTabBar: mouse move event handler to check if the mouse has moved far enough to trigger a tear-off """

        # If the left mouse button is pressed and we have a valid press index and position, check the distance moved
        if self._press_index >= 0 and self._press_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            distance = (event.pos() - self._press_pos).manhattanLength() # Calculate the distance moved from the original press position
            # If the distance is greater than or equal to 32 pixels, emit the tearOffRequested signal with the index of the tab and the global position of the mouse
            if distance >= 32:
                self.tearOffRequested.emit(self._press_index, self.mapToGlobal(event.pos()))
                # Reset state to prevent multiple emissions
                self._press_index = -1
                self._press_pos = None
                return

        super().mouseMoveEvent(event)

        return None

# -----

class FloatingConsultationWindow(QMainWindow):
    """ Floating window used when a consultation tab is torn off """

    closed = pyqtSignal()

    # -----

    def __init__(self, title: str, widget: QWidget, parent=None) -> None:
        """ FloatingConsultationWindow: initialisation method to create a floating window with the given title and widget """

        super().__init__(parent)
        self.setObjectName("floatingConsultationWindow")
        self.setWindowTitle(title)
        self.setCentralWidget(widget)
        widget.setVisible(True)
        self.resize(900, 650)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

    # -----

    def closeEvent(self, event) -> None:
        """ FloatingConsultationWindow: close the floating window to restore the torn-off tab back to the main window """

        self.closed.emit()
        super().closeEvent(event)

        return None

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
        self._detached_consultation_tabs = {}

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

        self.logo_entegra = QLabel()
        self.logo_entegra.setPixmap(
            QPixmap(
                os.path.join(
                    os.getcwd(),
                    "gui_folder",
                    "resources_folder",
                    "icons_folder",
                    "logo-entegra.png"
                )
            ).scaled(
                140,
                60,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        )
        self.logo_entegra.setObjectName("logoEntegra")
        self.logo_entegra.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.button_dashboard = QPushButton("Tableau de bord")
        self.button_import = QPushButton("Import")
        self.button_mapping = QPushButton("Mapping")
        self.button_calculation = QPushButton("Calcul")
        self.button_result = QPushButton("Export calcul")
        self.button_consultation = QPushButton("Consultation")

        self.sidebar_layout.addWidget(self.logo_label)
        self.sidebar_layout.addSpacing(30)

        for button in [
            self.button_dashboard,
            self.button_import,
            self.button_mapping,
            self.button_calculation,
            self.button_result,
            self.button_consultation
        ]:
            button.setObjectName("menuButton")
            self.sidebar_layout.addWidget(button)

        self.sidebar_layout.addStretch()
        self.sidebar_layout.addWidget(self.logo_entegra)

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
        self.page_consultation = self.create_consultation_page_method()

        self.pages.addWidget(self.page_dashboard)
        self.pages.addWidget(self.page_import)
        self.pages.addWidget(self.page_mapping)
        self.pages.addWidget(self.page_calculation)
        self.pages.addWidget(self.page_result)
        self.pages.addWidget(self.page_consultation)

        return None

    # -----

    def detach_consultation_tab_method(self, param_tab_index: int, param_global_pos: QPoint) -> None:
        """ GUI Main Window Class: detach a consultation tab into a floating window """

        # Check if the tab index is valid
        if param_tab_index < 0 or param_tab_index >= self.consultation_tabs.count():
            return None

        # Get the widget and title of the tab to be detached, then remove it from the tab widget
        page_widget = self.consultation_tabs.widget(param_tab_index)
        tab_title = self.consultation_tabs.tabText(param_tab_index)
        self.consultation_tabs.removeTab(param_tab_index)

        # Create a floating window with the tab's widget and title, move it to the position of the mouse,
        # and connect its closed signal to restore the tab when the window is closed
        floating_window = FloatingConsultationWindow(tab_title, page_widget, self)
        floating_window.move(param_global_pos)
        floating_window.closed.connect(
            lambda widget=page_widget, index=param_tab_index, title=tab_title: self.restore_consultation_tab_method(widget, index, title)
        )

        # Store the floating window in a dictionary to keep it alive while detached for later reference when restoring
        self._detached_consultation_tabs[page_widget] = floating_window
        floating_window.show()

        return None

    # -----

    def restore_consultation_tab_method(self, param_widget: QWidget, param_tab_index: int, param_tab_title: str) -> None:
        """ GUI Main Window Class: restore a torn-off consultation tab into the tab widget """

        # Check if the widget is already in the tab widget
        if self.consultation_tabs.indexOf(param_widget) == -1:
            # Get index to insert the tab (use the original index if possible, otherwise append at the end)
            insert_index = min(param_tab_index, self.consultation_tabs.count())
            self.consultation_tabs.insertTab(insert_index, param_widget, param_tab_title)
            self.consultation_tabs.setCurrentWidget(param_widget)

        self._detached_consultation_tabs.pop(param_widget, None)

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
        self.kpi_consultations = self.create_kpi_card_method("Données à vérifier", "0")

        kpi_layout.addWidget(self.kpi_revenus)
        kpi_layout.addWidget(self.kpi_accords)
        kpi_layout.addWidget(self.kpi_produits)
        kpi_layout.addWidget(self.kpi_consultations)

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

        subtitle = QLabel("Importer les produits et les accords, puis utiliser les accords comme modèle pour préparer les imports.")
        subtitle.setObjectName("subtitle")

        button_layout = QHBoxLayout()

        self.button_import_produits = QPushButton("Importer produits")
        self.button_import_accords = QPushButton("Importer accords")
        self.button_export_accords_template = QPushButton("Exporter accords")
        self.button_export_accords_template.setObjectName("primaryButton")

        button_layout.addWidget(self.button_import_produits)
        button_layout.addWidget(self.button_import_accords)
        button_layout.addWidget(self.button_export_accords_template)

        self.table_imports = QTableWidget()
        self.table_imports.setColumnCount(4)
        self.table_imports.setHorizontalHeaderLabels(["Type", "Fichier", "Statut", "Commentaire"])
        self.table_imports.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addWidget(title)
        layout.addWidget(subtitle)
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

        details_title = QLabel("Détails du calcul")
        details_title.setObjectName("pageTitle")

        self.calculation_details = QTextEdit()
        self.calculation_details.setReadOnly(True)
        self.calculation_details.setPlaceholderText(
            "Les étapes, résultats intermédiaires et sorties détaillées du calcul apparaîtront ici."
        )

        layout.addWidget(title)
        layout.addWidget(self.button_start_calculation)
        layout.addWidget(self.progress_calcul)
        layout.addWidget(self.label_calcul_status)
        layout.addWidget(details_title)
        layout.addWidget(self.calculation_details)
        layout.addStretch()

        return page

    # -----

    def create_result_page_method(self) -> QWidget:
        """ GUI Main Window Class: creation of the calculation export page """

        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Export du calcul")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Exporter tous les détails du calcul réalisé et conserver une trace exploitable pour contrôle ou audit.")
        subtitle.setObjectName("subtitle")

        self.button_export_results = QPushButton("Exporter tous les détails")
        self.button_export_results.setObjectName("primaryButton")

        self.table_resultats = QTableWidget()
        self.table_resultats.setColumnCount(6)
        self.table_resultats.setHorizontalHeaderLabels([
            "Fournisseur",
            "Période",
            "CA déclaré",
            "Taux accord",
            "Revenu",
            "Détail du calcul"
        ])
        self.table_resultats.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.button_export_results)
        layout.addWidget(self.table_resultats)

        return page

    # -----

    def create_consultation_page_method(self) -> QWidget:
        """ GUI Main Window Class: creation of the consultation and correction page """

        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Consultation et correction")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Afficher les données produits et les accords au même endroit pour vérifier, corriger et valider sans aller-retour.")
        subtitle.setObjectName("subtitle")

        self.consultation_tabs = QTabWidget()
        self.consultation_tabs.setObjectName("consultationTabs")
        self.consultation_tabs.setMovable(True)
        self.consultation_tabs.setTabBar(TearOffTabBar(self.consultation_tabs))
        self.consultation_tabs.tabBar().tearOffRequested.connect(self.detach_consultation_tab_method)

        products_tab = QWidget()
        products_layout = QVBoxLayout(products_tab)

        self.table_consult_products = QTableWidget()
        self.table_consult_products.setColumnCount(5)
        self.table_consult_products.setHorizontalHeaderLabels([
            "ID produit",
            "Produit source",
            "Produit mappé",
            "Statut",
            "Action"
        ])
        self.table_consult_products.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_consult_products.setEditTriggers(QTableWidget.EditTrigger.AllEditTriggers)

        self.product_dock_output = QTextEdit()
        self.product_dock_output.setReadOnly(True)
        self.product_dock_output.setPlaceholderText(
            "Sélectionner une ligne pour afficher le détail produit ici."
        )

        products_layout.addWidget(self.table_consult_products)
        products_layout.addWidget(self.product_dock_output)

        accords_tab = QWidget()
        accords_layout = QVBoxLayout(accords_tab)

        self.table_consult_accords = QTableWidget()
        self.table_consult_accords.setColumnCount(6)
        self.table_consult_accords.setHorizontalHeaderLabels([
            "ID accord",
            "Fournisseur",
            "Produit",
            "Période",
            "Taux",
            "Statut"
        ])
        self.table_consult_accords.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_consult_accords.setEditTriggers(QTableWidget.EditTrigger.AllEditTriggers)

        self.accord_dock_output = QTextEdit()
        self.accord_dock_output.setReadOnly(True)
        self.accord_dock_output.setPlaceholderText(
            "Sélectionner une ligne pour afficher le détail accord ici."
        )

        accords_layout.addWidget(self.table_consult_accords)
        accords_layout.addWidget(self.accord_dock_output)

        self.consultation_tabs.addTab(products_tab, "Produits")
        self.consultation_tabs.addTab(accords_tab, "Accords")

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.consultation_tabs)

        return page

    # -----
