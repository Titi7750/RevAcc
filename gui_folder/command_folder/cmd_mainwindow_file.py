# Import Python packages
## None

# Import modules from Python packages
## None

# Import third party packages
## None

# Import modules from third party packages
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtWidgets import QMessageBox

# Import personnal functions
from gui_folder.graphic_folder.gui_mainwindow_file import GuiMainWindowClass

# Custom variable type construction
## None

# -----

class CmdMainWindowClass(GuiMainWindowClass):
    """ CMD Main Window Class """

    def __init__(self) -> None:
        """ CMD Main Window Class: initialisation Method """

        super().__init__()

        self.connect_events_method()
        self.change_page_method(0, self.button_dashboard)

        self.load_fake_data_method()

        return None

    # -----

    def connect_events_method(self) -> None:
        """ CMD Main Window Class: Connect events method """

        # Navigation
        self.button_dashboard.clicked.connect(lambda: self.change_page_method(0, self.button_dashboard))
        self.button_import.clicked.connect(lambda: self.change_page_method(1, self.button_import))
        self.button_mapping.clicked.connect(lambda: self.change_page_method(2, self.button_mapping))
        self.button_calculation.clicked.connect(lambda: self.change_page_method(3, self.button_calculation))
        self.button_result.clicked.connect(lambda: self.change_page_method(4, self.button_result))
        self.button_anomalies.clicked.connect(lambda: self.change_page_method(5, self.button_anomalies))

        # Import
        self.button_import_transactions.clicked.connect(
            lambda: self.import_file_method("Transactions")
        )
        self.button_import_produits.clicked.connect(
            lambda: self.import_file_method("Produits")
        )
        self.button_import_accords.clicked.connect(
            lambda: self.import_file_method("Accords")
        )

        # Calcul
        self.button_start_calculation.clicked.connect(self.run_calculation_method)

        # Export
        self.button_export_results.clicked.connect(self.export_result_method)

        return None

    # -----

    def change_page_method(self, param_page_index: int, param_active_button) -> None:
        """ CMD Main Window Class: Change page method """

        self.pages.setCurrentIndex(param_page_index)

        menu_buttons = [
            self.button_dashboard,
            self.button_import,
            self.button_mapping,
            self.button_calculation,
            self.button_result,
            self.button_anomalies
        ]

        for button in menu_buttons:
            button.setProperty("active", False)
            button.style().unpolish(button)
            button.style().polish(button)

        param_active_button.setProperty("active", True)
        param_active_button.style().unpolish(param_active_button)
        param_active_button.style().polish(param_active_button)

        return None

    # -----

    def import_file_method(self, param_file_type: str) -> None:
        """ CMD Main Window Class: Import file method """

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Importer {param_file_type}",
            "",
            "Fichiers Excel/CSV (*.xlsx *.csv)"
        )

        if not file_path:
            return

        row = self.table_imports.rowCount()
        self.table_imports.insertRow(row)

        self.table_imports.setItem(row, 0, QTableWidgetItem(param_file_type))
        self.table_imports.setItem(row, 1, QTableWidgetItem(file_path))
        self.table_imports.setItem(row, 2, QTableWidgetItem("Importé"))

        QMessageBox.information(
            self,
            "Import réussi",
            f"Le fichier {param_file_type} a bien été importé."
        )

        return None

    # ----- START OF FUNCTIONS TEMPORARY -----

    def load_fake_data_method(self) -> None:
        """ CMD Main Window Class: Load fake data method """

        self.load_fake_mapping_method()
        self.load_fake_results_method()
        self.load_fake_anomalies_method()
        self.update_dashboard_method()

        return None

    # -----

    def load_fake_mapping_method(self) -> None:
        """ CMD Main Window Class: Load fake mapping method """

        data = [
            ["Coca-Cola 24x33cl", "Coca-Cola 33cl", "carton → unité", "OK"],
            ["Sprite Zero 12x50cl", "Sprite Zero 50cl", "carton → unité", "OK"],
            ["Evian Pack 6x1L", "Evian 1L", "pack → unité", "OK"],
            ["Produit inconnu ABC", "", "", "À corriger"],
        ]

        self.table_mapping.setRowCount(len(data))

        for row_index, row_data in enumerate(data):
            for col_index, value in enumerate(row_data):
                self.table_mapping.setItem(
                    row_index,
                    col_index,
                    QTableWidgetItem(value)
                )

        return None

    # -----

    def load_fake_results_method(self) -> None:
        """ CMD Main Window Class: Load fake results method """

        data = [
            ["Coca-Cola", "Avril 2026", "52 000 €", "5 %", "2 600 €"],
            ["Nestlé", "Avril 2026", "38 400 €", "4 %", "1 536 €"],
            ["Danone", "Avril 2026", "61 200 €", "3,5 %", "2 142 €"],
            ["PepsiCo", "Avril 2026", "29 800 €", "5 %", "1 490 €"],
        ]

        self.table_resultats.setRowCount(len(data))

        for row_index, row_data in enumerate(data):
            for col_index, value in enumerate(row_data):
                self.table_resultats.setItem(
                    row_index,
                    col_index,
                    QTableWidgetItem(value)
                )

        return None

    # -----

    def load_fake_anomalies_method(self) -> None:
        """ CMD Main Window Class: Load fake anomalies method """

        anomalies = [
            "Produit inconnu : Produit inconnu ABC",
            "Unité non reconnue : carton_12btl",
            "Accord manquant : Supplier ID 458",
            "Doublon transaction : TX-2026-0418",
        ]

        self.list_anomalies.clear()
        self.list_anomalies.addItems(anomalies)

        return None

    # ----- END OF FUNCTIONS TEMPORARY -----

    def update_dashboard_method(self) -> None:
        """ CMD Main Window Class: Update dashboard method """

        self.kpi_revenus.value_label.setText("7 768 €")
        self.kpi_accords.value_label.setText("42")
        self.kpi_produits.value_label.setText("1 284")
        self.kpi_anomalies.value_label.setText(
            str(self.list_anomalies.count())
        )

        return None

    # -----

    def run_calculation_method(self) -> None:
        """ CMD Main Window Class: Run calculation method """

        self.progress_calcul.setValue(0)
        self.label_calcul_status.setText("Calcul en cours...")

        # Simulation simple
        for value in range(0, 101, 20):
            self.progress_calcul.setValue(value)
            QApplication.processEvents()

        self.label_calcul_status.setText("Calcul terminé avec succès.")
        self.update_dashboard_method()

        QMessageBox.information(
            self,
            "Calcul terminé",
            "Les revenus ont été calculés avec succès."
        )

        return None

    # -----

    def export_result_method(self) -> None:
        """ CMD Main Window Class: Export results method """

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter les résultats",
            "resultats_revacc.xlsx",
            "Fichier Excel (*.xlsx)"
        )

        if not file_path:
            return

        QMessageBox.information(
            self,
            "Export",
            f"Export prévu vers :\n{file_path}\n\n"
        )

        return None

    # -----
