# Import Python packages
## None

# Import modules from Python packages
## None

# Import third party packages
## None

# Import modules from third party packages
from sqlalchemy import text

# Import personal functions
from core_folder.database_file import get_connection

# Custom variable type construction
## None

# -----

def load_consultation_products_method() -> list:
    """ Retourne les lignes pour l'onglet Produits de la consultation : id, nom, marque - catégorie, unité, statut """

    with get_connection() as connection:
        rows = connection.execute(
            text(
                """
                SELECT
                    product.product_name,
                    CONCAT(brand.brand_name, ' - ', category.category_name) AS mapped_to,
                    unit.unit_name,
                    CASE
                        WHEN COUNT(transaction.id_transaction) = 0 THEN 'Sans transaction'
                        WHEN SUM(CASE WHEN transaction.fk_id_agreement IS NULL THEN 1 ELSE 0 END) > 0 THEN 'À corriger'
                        ELSE 'OK'
                    END AS status
                FROM product
                JOIN brand            ON brand.id_brand            = product.fk_id_brand
                JOIN category         ON category.id_category      = product.fk_id_category
                JOIN unit             ON unit.id_unit              = product.fk_id_unit
                LEFT JOIN transaction ON transaction.fk_id_product = product.id_product
                GROUP BY product.id_product, product.product_name, brand.brand_name, category.category_name, unit.unit_name
                ORDER BY status, product.product_name
                """
            )
        ).fetchall()

    return [list(row) for row in rows]

# -----

def load_consultation_agreements_method() -> list:
    """ Retourne les lignes pour l'onglet Accords de la consultation """

    with get_connection() as connection:
        rows = connection.execute(
            text(
                """
                SELECT
                    industrial.industrial_name,
                    CONCAT(brand.brand_name, ' - ', category.category_name) AS produit,
                    CASE
                        WHEN agreement.start_date IS NULL AND agreement.end_date IS NULL THEN 'Toutes périodes'
                        WHEN agreement.end_date IS NULL THEN CONCAT('Depuis ', agreement.start_date)
                        ELSE CONCAT(agreement.start_date, ' - ', agreement.end_date)
                    END AS periode,
                    GROUP_CONCAT(
                        CONCAT(
                            agreement_tier.min_uvc, ' - ',
                            COALESCE(agreement_tier.max_uvc, '+∞'), ' UVC : ',
                            agreement_tier.price, ' €/UVC'
                        )
                        ORDER BY agreement_tier.min_uvc SEPARATOR ' | '
                    ) AS taux,
                    'Actif' AS status
                FROM agreement
                JOIN industrial          ON industrial.id_industrial       = agreement.fk_id_industrial
                JOIN brand               ON brand.id_brand                 = agreement.fk_id_brand
                JOIN category            ON category.id_category           = agreement.fk_id_category
                LEFT JOIN agreement_tier ON agreement_tier.fk_id_agreement = agreement.id_agreement
                GROUP BY agreement.id_agreement
                ORDER BY industrial.industrial_name, brand.brand_name
                """
            )
        ).fetchall()

    return [list(row) for row in rows]

# -----

def load_all_transactions_method() -> list:
    """ Retourne les lignes pour l'onglet Transactions de la consultation """

    with get_connection() as connection:
        rows = connection.execute(text(
            """
            SELECT
                COALESCE(CAST(transaction.transaction_date AS CHAR), '') AS transaction_date,
                COALESCE(distributor.distributor_name, '')               AS distributor_name,
                COALESCE(product.product_name, '')                       AS product_name,
                transaction.quantity,
                transaction.unit_price,
                transaction.total_price
            FROM transaction
            LEFT JOIN distributor ON distributor.id_distributor = transaction.fk_id_distributor
            LEFT JOIN product     ON product.id_product         = transaction.fk_id_product
            ORDER BY transaction.transaction_date DESC, transaction.id_transaction DESC
            """
        )).fetchall()

    return [list(row) for row in rows]

# -----

def load_all_brands_method() -> list:
    """ Retourne toutes les marques triées par nom """

    with get_connection() as connection:
        rows = connection.execute(text(
            "SELECT brand_name FROM brand ORDER BY brand_name"
        )).fetchall()

    return [list(row) for row in rows]

# -----

def load_all_categories_method() -> list:
    """ Retourne toutes les catégories triées par nom """

    with get_connection() as connection:
        rows = connection.execute(text(
            "SELECT category_name FROM category ORDER BY category_name"
        )).fetchall()

    return [list(row) for row in rows]

# -----

def load_all_distributors_method() -> list:
    """ Retourne tous les distributeurs triés par nom """

    with get_connection() as connection:
        rows = connection.execute(text(
            "SELECT distributor_name FROM distributor ORDER BY distributor_name"
        )).fetchall()

    return [list(row) for row in rows]

# -----

def load_all_industrials_method() -> list:
    """ Retourne tous les industriels triés par nom """

    with get_connection() as connection:
        rows = connection.execute(text(
            "SELECT industrial_name FROM industrial ORDER BY industrial_name"
        )).fetchall()

    return [list(row) for row in rows]

# -----

def load_all_units_method() -> list:
    """ Retourne toutes les unités triées par nom """

    with get_connection() as connection:
        rows = connection.execute(text(
            "SELECT unit_name FROM unit ORDER BY unit_name"
        )).fetchall()

    return [list(row) for row in rows]
