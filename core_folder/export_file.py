# Import Python packages
## None

# Import modules from Python packages
## None

# Import third party packages
import pandas as pd

# Import modules from third party packages
from sqlalchemy import text

# Import personal functions
from core_folder.database_file import get_connection

# Custom variable type construction
## None

# -----

def export_calculation_method(param_file_path: str, param_results: list) -> None:
    """ Exporte les résultats de calcul dans un fichier Excel (deux feuilles : Résumé + Transactions) """

    dataframe_resume = pd.DataFrame([{
        "Distributeur":     result["distributor"],
        "Fournisseur":      result["industrial"],
        "Marque":           result["brand"],
        "Catégorie":        result["category"],
        "Total UVC":        result["total_uvc"],
        "CA déclaré (€)":   round(result["total_ca"], 2),
        "Taux accord":      result["tier_price"],
        "Revenu (€)":       round(result["revenue"], 2),
        "Détail du calcul": result["detail"]
    } for result in param_results])

    with get_connection() as connection:
        dataframe_transactions = pd.read_sql(
            text("""
                SELECT transaction.id_transaction, product.product_name, brand.brand_name,
                category.category_name, distributor.distributor_name, industrial.industrial_name,
                transaction.quantity, transaction.unit_price, transaction.total_price,
                transaction.transaction_date,
                CASE
                    WHEN transaction.fk_id_agreement IS NULL THEN 'Sans accord'
                ELSE 'Mappé'
                END AS mapping_status
                FROM transaction
                LEFT JOIN product     ON product.id_product         = transaction.fk_id_product
                LEFT JOIN brand       ON brand.id_brand             = product.fk_id_brand
                LEFT JOIN category    ON category.id_category       = product.fk_id_category
                LEFT JOIN distributor ON distributor.id_distributor = transaction.fk_id_distributor
                LEFT JOIN agreement   ON agreement.id_agreement     = transaction.fk_id_agreement
                LEFT JOIN industrial  ON industrial.id_industrial   = agreement.fk_id_industrial
                ORDER BY transaction.id_transaction
            """),
            connection
        )

    with pd.ExcelWriter(param_file_path, engine="openpyxl") as writer:
        dataframe_resume.to_excel(writer, sheet_name="Résumé", index=False)
        dataframe_transactions.to_excel(writer, sheet_name="Transactions", index=False)
