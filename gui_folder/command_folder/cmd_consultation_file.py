# Import Python packages
## None

# Import modules from Python packages
## None

# Import third party packages
## None

# Import modules from third party packages
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox, QTableWidgetItem

# Import personal functions
from gui_folder.graphic_folder.gui_consultation_file import GuiConsultationPageClass
# -----
from core_folder.consultation_file import (
    load_consultation_products_method,
    load_consultation_agreements_method,
    load_all_transactions_method,
    load_all_product_conversions_method,
    load_all_brands_method,
    load_all_categories_method,
    load_all_distributors_method,
    load_all_industrials_method,
    load_all_units_method,
)

# Custom variable type construction
## None

# -----

class CmdConsultationPageClass(GuiConsultationPageClass):
    """
    Contrôleur de la page Consultation.
    Hérite de la vue GuiConsultationPageClass et y ajoute le chargement des données depuis la base.
    Toutes les tables sont en lecture seule dans ce prototype.
    """

    def __init__(self) -> None:
        super().__init__()
        return None

    # -----

    def load_data_method(self) -> None:
        """
        Charge toutes les tables de consultation depuis la base de données.
        Appelé au démarrage et après chaque import réussi.
        """

        try:

            # ── Onglet Produits ───────────────────────────────────────────────
            # Colonnes : [id_product, product_name, mapped_to, unit_name, status]
            self._fill_table_method(
                self.table_consult_products,
                load_consultation_products_method(),
                color_col=4,  # Colonne Statut reçoit une couleur selon la valeur
            )

            # ── Onglet Accords ────────────────────────────────────────────────
            # Colonnes : [id_agreement, industrial_name, produit, periode, taux, status]
            self._fill_table_method(
                self.table_consult_accords,
                load_consultation_agreements_method(),
            )

            # ── Onglet Transactions ───────────────────────────────────────────
            # Colonnes : [id, date, distributor, product_name, quantity, unit_price, total_price]
            self._fill_table_method(
                self.table_consult_transactions,
                load_all_transactions_method(),
            )

            # ── Onglets référentiels (ID + Nom) ───────────────────────────────
            self._fill_table_method(self.table_consult_brands,       load_all_brands_method())
            self._fill_table_method(self.table_consult_categories,   load_all_categories_method())
            self._fill_table_method(self.table_consult_distributors, load_all_distributors_method())
            self._fill_table_method(self.table_consult_industrials,  load_all_industrials_method())
            self._fill_table_method(self.table_consult_units,        load_all_units_method())
            self._fill_table_method(self.table_consult_conversions,  load_all_product_conversions_method())

        except Exception as exc:
            QMessageBox.warning(
                self,
                "Erreur de chargement",
                f"Impossible de charger les données :\n{exc}",
            )

        return None

    # -----

    def _fill_table_method(
        self,
        param_table,
        param_rows: list,
        color_col: int = None,
    ) -> None:
        """
        Remplit un QTableWidget avec les lignes données.
        Toutes les cellules sont en lecture seule (prototype).
        Le paramètre color_col indique quelle colonne reçoit une couleur selon sa valeur.
        """

        param_table.setRowCount(len(param_rows))

        for row_index, row_data in enumerate(param_rows):
            for col_index, cell_value in enumerate(row_data):
                cell_text = str(cell_value) if cell_value is not None else ""
                cell_item = QTableWidgetItem(cell_text)

                # Lecture seule au niveau de l'item (en plus du NoEditTriggers sur le tableau)
                # À retirer par colonne pour activer l'édition dans une version future
                cell_item.setFlags(cell_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                # Couleur de statut sur la colonne demandée (Produits uniquement pour l'instant)
                if col_index == color_col:
                    status_color = (
                        Qt.GlobalColor.darkGreen if cell_text == "OK"
                        else Qt.GlobalColor.red  if cell_text == "À corriger"
                        else Qt.GlobalColor.darkGray
                    )
                    cell_item.setForeground(status_color)

                param_table.setItem(row_index, col_index, cell_item)

        return None
