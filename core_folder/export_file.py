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

def export_calculation_method(param_file_path: str, param_results: list, param_summary: dict) -> None:
    """ Exporte les résultats de calcul dans un fichier Excel (deux feuilles : Résumé + Transactions) """

    dataframe_resume = pd.DataFrame([{
        "Distributeur":     result["distributor"],
        "Fournisseur":      result["industrial"],
        "Marque":           result["brand"],
        "Catégorie":        result["category"],
        "Total volume":     result["total_volume"],
        "Taux accord":      result["tier_price"],
        "Détail du calcul": result["detail"]
    } for result in param_results])

    # Totaux globaux depuis summary — écrits sur la même feuille sous le tableau principal
    revenue_by_group = param_summary.get("revenue_by_group", {})

    # Création d'un DataFrame pour les totaux par groupe d'accords
    dataframe_totaux = pd.DataFrame([
        {
            "Accord": agreement_name,
            "Revenu (€)": revenue,
        }
        for agreement_name, revenue in revenue_by_group.items()
    ])

    # Ajout d'une ligne pour le total global
    dataframe_totaux.loc[len(dataframe_totaux)] = {
        "Accord": "Total",
        "Revenu (€)": param_summary.get("total_revenue", 0.0),
    }

    with get_connection() as connection:
        dataframe_transactions = pd.read_sql(
            text("""
                SELECT product.product_name, product.description, brand.brand_name,
                category.category_name, distributor.distributor_name, industrial.industrial_name,
                transaction.quantity, transaction.unit_price, transaction.total_price,
                transaction.transaction_date,
                transaction.agreement_unit_price,
                CASE
                    WHEN transaction.fk_id_agreement IS NULL THEN 'Sans accord'
                ELSE 'OK'
                END AS mapping_status
                FROM transaction
                LEFT JOIN product        ON product.id_product               = transaction.fk_id_product
                LEFT JOIN brand          ON brand.id_brand                   = product.fk_id_brand
                LEFT JOIN category       ON category.id_category             = product.fk_id_category
                LEFT JOIN distributor    ON distributor.id_distributor       = transaction.fk_id_distributor
                LEFT JOIN agreement      ON agreement.id_agreement           = transaction.fk_id_agreement
                LEFT JOIN industrial     ON industrial.id_industrial         = agreement.fk_id_industrial
                LEFT JOIN agreement_tier ON agreement_tier.id_agreement_tier = transaction.fk_id_agreement_tier
                ORDER BY transaction.id_transaction
            """),
            connection
        )

    # -----

    def _format_taux(row):
        """ Formatage du taux d'accord pour l'affichage dans le fichier Excel """

        if pd.isna(row["agreement_unit_price"]):
            return "—"

        return f"{float(row['agreement_unit_price']):.2f} €/unité accord"

    # -----

    dataframe_transactions["Taux accord"] = dataframe_transactions.apply(_format_taux, axis=1)
    dataframe_transactions.drop(
        columns=["agreement_unit_price"],
        inplace=True
    )

    with pd.ExcelWriter(param_file_path, engine="openpyxl") as writer:
        dataframe_resume.to_excel(writer, sheet_name="Résumé", index=False)
        # Les totaux sont écrits sur la même feuille, deux lignes sous le tableau principal
        # (une ligne de données + une ligne vide de séparation)
        start_row_totaux = len(dataframe_resume) + 2
        dataframe_totaux.to_excel(writer, sheet_name="Résumé", index=False, startrow=start_row_totaux)
        dataframe_transactions.to_excel(writer, sheet_name="Transactions", index=False)
