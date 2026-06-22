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

def load_dashboard_kpis_method() -> dict:
    """ Retourne les valeurs KPI légères pour le tableau de bord """

    with get_connection() as connection:
        # Nombre d'accords et de produits actifs
        accord_count = connection.execute(
            text("SELECT COUNT(*) FROM agreement")
        ).scalar() or 0 # Utilisation de scalar() pour obtenir la première valeur, par défaut = 0

        product_count = connection.execute(
            text("SELECT COUNT(*) FROM product")
        ).scalar() or 0

        # Nombre de transactions avec au moins une FK manquante
        product_null_count = connection.execute(
            text(
                """
                SELECT COUNT(*) FROM transaction
                WHERE fk_id_product IS NULL
                """
            )
        ).scalar() or 0

        # Nombre de transactions avec au moins une FK manquante
        agreement_null_count = connection.execute(
            text(
                """
                SELECT COUNT(*) FROM transaction
                WHERE fk_id_agreement IS NULL
                """
            )
        ).scalar() or 0

        # Nombre de transactions avec au moins une FK manquante
        distributor_null_count = connection.execute(
            text(
                """
                SELECT COUNT(*) FROM transaction
                WHERE fk_id_distributor IS NULL
                """
            )
        ).scalar() or 0

    return {
        "accords":    int(accord_count),
        "products":   int(product_count),
        "product_to_be_verified": int(product_null_count),
        "agreement_to_be_verified": int(agreement_null_count),
        "distributor_to_be_verified": int(distributor_null_count),
    }
