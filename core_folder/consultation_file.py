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
    """
    Retourne les lignes pour l'onglet Produits de la consultation : id, nom, marque - catégorie, unité, statut

    On peut avoir 3 statuts :
        - "Sans transaction" : le produit n'a jamais été utilisé dans une transaction
        - "À corriger" : le produit a été utilisé dans une transaction mais n'a pas d'accord associé
        - "OK" : le produit a été utilisé dans une transaction et a un accord associé
    """

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
                    GROUP_CONCAT(
                        CONCAT(
                            agreement_tier.min_volume, ' - ',
                            COALESCE(agreement_tier.max_volume, '+∞'), ' ', unit.unit_name, ' : ',
                            agreement_tier.price, ' €/', unit.unit_name
                        )
                        ORDER BY agreement_tier.min_volume SEPARATOR ' | '
                    ) AS taux
                FROM agreement
                JOIN industrial          ON industrial.id_industrial       = agreement.fk_id_industrial
                JOIN brand               ON brand.id_brand                 = agreement.fk_id_brand
                JOIN category            ON category.id_category           = agreement.fk_id_category
                JOIN unit                ON unit.id_unit                   = agreement.fk_id_unit
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
                COALESCE(product.product_code, '')         AS product_code,
                COALESCE(distributor.distributor_name, '') AS distributor_name,
                COALESCE(product.product_name, '')         AS product_name,
                transaction.quantity,
                transaction.unit_price,
                transaction.total_price
            FROM transaction
            LEFT JOIN distributor ON distributor.id_distributor = transaction.fk_id_distributor
            LEFT JOIN product     ON product.id_product         = transaction.fk_id_product
            ORDER BY product.product_code
            """
        )).fetchall()

    return [list(row) for row in rows]

# -----

def load_all_product_conversions_method() -> list:
    """ Retourne toutes les lignes de la table de correspondance """

    with get_connection() as connection:
        rows = connection.execute(text(
            """
            SELECT
                distributor_name,
                product_code,
                transaction_unit,
                agreement_unit,
                conversion_factor
            FROM product_conversion
            ORDER BY distributor_name, product_code
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
