# Import Python packages
## None

# Import modules from Python packages
## None

# Import third party packages
## None

# Import modules from third party packages
from PyQt6.QtWidgets import QMessageBox

# Import personal functions
from gui_folder.graphic_folder.gui_mainwindow_file import GuiMainWindowClass
from gui_folder.command_folder.cmd_import_file import CmdImportPageClass
from gui_folder.command_folder.cmd_calculation_file import CmdCalculationPageClass
from gui_folder.command_folder.cmd_consultation_file import CmdConsultationPageClass
# -----
from core_folder.calculation_file import load_dashboard_kpis_method
# Custom variable type construction
## None

# -----


class CmdMainWindowClass(GuiMainWindowClass):
    """
    Contrôleur de la fenêtre principale.
    Assemble les 3 pages fonctionnelles dans le QStackedWidget,
    gère la navigation entre les pages et la mise à jour du dashboard.
    """

    def __init__(self) -> None:
        super().__init__()

        # ── Création des pages fonctionnelles ────────────────────────────────
        # Chaque page est un CmdXxx qui hérite de GuiXxx (vue + logique ensemble)
        self.import_page       = CmdImportPageClass()
        self.calculation_page  = CmdCalculationPageClass()
        self.consultation_page = CmdConsultationPageClass()

        # ── Ajout des pages dans le QStackedWidget ────────────────────────────
        # L'ordre définit l'index utilisé dans change_page_method :
        # 0 = Dashboard, 1 = Import, 2 = Calcul, 3 = Consultation
        self.pages.addWidget(self.dashboard_page)
        self.pages.addWidget(self.import_page)
        self.pages.addWidget(self.calculation_page)
        self.pages.addWidget(self.consultation_page)

        self.connect_events_method()

        # Page de démarrage : tableau de bord
        self.change_page_method(0, self.button_dashboard)

        # Chargement initial des données depuis la base
        self.refresh_dashboard_method()
        self.consultation_page.load_data_method()

        return None

    # -----

    def connect_events_method(self) -> None:
        """ Connexion des boutons de navigation et des signaux inter-pages """

        # Boutons de la sidebar → changement de page
        self.button_dashboard.clicked.connect(
            lambda: self.change_page_method(0, self.button_dashboard)
        )
        self.button_import.clicked.connect(
            lambda: self.change_page_method(1, self.button_import)
        )
        self.button_calculation.clicked.connect(
            lambda: self.change_page_method(2, self.button_calculation)
        )
        self.button_consultation.clicked.connect(
            lambda: self.change_page_method(3, self.button_consultation)
        )

        # Après un import réussi : rafraîchir le dashboard et la consultation
        self.import_page.data_changed.connect(self.refresh_dashboard_method)
        self.import_page.data_changed.connect(self.consultation_page.load_data_method)

        # Après un calcul réussi : mettre à jour le KPI revenu sur le dashboard
        self.calculation_page.calc_done.connect(self.on_calculation_done_method)

        return None

    # -----

    def change_page_method(self, param_page_index: int, param_active_button) -> None:
        """ Change la page visible et met à jour l'état visuel actif du bouton dans la sidebar """

        self.pages.setCurrentIndex(param_page_index)

        # Réinitialisation de l'état actif de tous les boutons
        nav_buttons = [
            self.button_dashboard,
            self.button_import,
            self.button_calculation,
            self.button_consultation,
        ]
        for nav_button in nav_buttons:
            nav_button.setProperty("active", False)
            nav_button.style().unpolish(nav_button)
            nav_button.style().polish(nav_button)

        # Activation du bouton sélectionné (met à jour la couleur via QSS)
        param_active_button.setProperty("active", True)
        param_active_button.style().unpolish(param_active_button)
        param_active_button.style().polish(param_active_button)

        return None

    # -----

    def refresh_dashboard_method(self) -> None:
        """ Recharge les 3 KPI chiffrés depuis la base et met à jour les cartes """

        try:
            kpis = load_dashboard_kpis_method()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Connexion base de données",
                f"Impossible de charger les données :\n{exc}\n\nVérifiez .env.local.",
            )
            return

        # Mise à jour des cartes (le KPI revenu est géré séparément par on_calculation_done_method)
        self.kpi_accords.value_label.setText(str(kpis["accords"]))
        self.kpi_produits.value_label.setText(str(kpis["produits"]))
        self.kpi_a_verifier.value_label.setText(str(kpis["a_verifier"]))

        return None

    # -----

    def on_calculation_done_method(self, param_total_revenue: float) -> None:
        """ Met à jour le KPI revenu sur le dashboard après un calcul réussi """

        # Formatage : séparateur espace pour les milliers (convention française), 2 décimales
        revenue_display = f"{param_total_revenue:,.2f} €".replace(",", " ")
        self.kpi_revenus.value_label.setText(revenue_display)

        return None
