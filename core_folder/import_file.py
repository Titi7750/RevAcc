# Import Python packages
import re
import unicodedata
from datetime import date

# Import modules from Python packages
## None

# Import third party packages
import pandas as pd

# Import modules from third party packages
from sqlalchemy import text

# Import personal functions
from core_folder.database_file import get_connection, get_or_create, get_or_create_many

# Custom variable type construction
BRAND_CORRECTION = {"Hellmanns": "Hellmann's"}
INDUSTRIAL_NAME  = "UNILEVER FOODSOLUTIONS"

RAW_COLUMN_MAP = {
    "DISTRIBUTEUR":   "distributor",
    "SOURCE DONNEES": "data_source",
    "CODE PRODUIT":   "product_code",
    "DESCRIPTION":    "description",
    "MARQUE":         "brand",
    "INDUSTRIEL":     "industrial",
    "UF":             "unit",
}

RAW_UNIT_MAP = {
    "BCL":   "BOCAL",
    "BID":   "BIDON",
    "BLLE":  "BOUTEILLE",
    "BT":    "BOÎTE",
    "BT.":   "BOÎTE",
    "BTE":   "BOÎTE",
    "BOITE": "BOÎTE",
    "BRQ":   "BRIQUE",
    "CO":    "COFFRET",
    "COF":   "COFFRET",
    "COL":   "COLIS",
    "FLC":   "FLACON",
    "PI":    "PIÈCE",
    "PCH":   "POCHE",
    "SEA":   "SEAU",
    "U":     "UNITÉ",
}

RAW_CODE_MAP = {
    "HELLEMANSQUEEZE": "HELLMANN'S SQUEEZE",
    "HELLMANNSQUEEZE": "HELLMANN'S SQUEEZE",
    "SAVORA":          "AMORASAVORA",
}

DESCRIPTION_BRAND_KEYWORDS = [
    "AMORA", "HELLMANN'S", "KNORR", "MAILLE", "MAIZENA", "TABASCO", "LIPTON", "ELEPHANT"
]

VOLUME_CATEGORY_BRANDS = {"TABASCO", "MAIZENA"}

# -----

def normalize_string_method(param_text: str) -> str:
    """ Supprime les accents, normalise les espaces et convertit en majuscules """

    text = unicodedata.normalize("NFKD", param_text)
    text = text.encode("ASCII", "ignore").decode("utf-8")
    text = text.replace("'", "")
    text = re.sub(r"\s+", " ", text).strip()
    text = text.upper()
    text = re.sub(r"(\d+)\s*(ML|L|KG|G)", r"\1\2", text)

    return text

# -----

def get_volume_category_method(param_text: str) -> str:
    """ Retourne la catégorie de volume d'un produit à partir de sa description (ML, KG, G) """

    text_upper = param_text.upper()

    match_ml = re.search(r"(\d+)\s*ML", text_upper)
    if match_ml:
        volume = int(match_ml.group(1))
        if volume <= 10:
            return "DOSETTE"
        elif volume <= 80:
            return "MINI"
        elif volume <= 200:
            return "150ML"
        elif volume <= 500:
            return "350ML"
        else:
            return "GRANDFORMAT"

    match_kg = re.search(r"(\d+[,.]?\d*)\s*KG", text_upper)
    if match_kg:
        volume = float(match_kg.group(1).replace(",", "."))
        if volume > 1:
            return "1KG"

    match_g = re.search(r"(\d+)\s*G(?![A-Z])", text_upper)
    if match_g:
        volume = int(match_g.group(1))
        if volume <= 500:
            return "340G"
        else:
            return "700G"

    return ""

# -----

def find_product_name_method(param_row: pd.Series, param_mapping: pd.DataFrame) -> str | None:
    """ Attribue le product_name par correspondance de mots-clés description/marque contre le mapping """

    raw_description  = str(param_row["description"])
    description_norm = normalize_string_method(raw_description)
    brand_norm       = normalize_string_method(str(param_row.get("brand", "")))

    # Certaines marques nécessitent une distinction par volume (ex : Tabasco 60mL vs 150mL)
    if any(brand in brand_norm for brand in VOLUME_CATEGORY_BRANDS):
        volume_category = get_volume_category_method(raw_description)
        if volume_category:
            description_norm += f" {volume_category}"

    best_score        = 0
    best_product_name = None

    for _, rule in param_mapping.iterrows():
        keywords_brands = [
            normalize_string_method(keyword_brand)
            for keyword_brand in str(rule["keywords_brands"]).split(";")
            if keyword_brand.strip()
        ]

        # Si les mots-clés de la marque ne correspondent pas, passez à la règle suivante
        if not any(keyword_brand in brand_norm for keyword_brand in keywords_brands):
            continue

        keywords_others = [
            normalize_string_method(keyword_other)
            for keyword_other in str(rule["keywords_others"]).split(";")
            if keyword_other.strip()
        ]

        # Compter le nombre de mots-clés présents dans la description normalisée
        # Avec le in operator, on peut trouver des correspondances singulier/pluriel (ex : "SEAU" dans "SEAUX")
        matched = sum(1 for keyword_other in keywords_others if keyword_other in description_norm)

        if matched > 0 and matched > best_score:
            best_score        = matched
            best_product_name = rule["product_name"]

    return best_product_name

# -----

def parse_palier_column_name_method(param_column_name: str):
    """
    Retourne (group_key, min_volume, max_volume_inclusive) ou None
    - palier_X_25000-35000_uvc    → ('X', 25000, 34999)
    - palier_X_superior-40000_uvc → ('X', 40000, None)
    """

    match = re.match(r"^palier_(.+)_(\d+)-(\d+)_uvc$", param_column_name)
    if match:
        return match.group(1), int(match.group(2)), int(match.group(3)) - 1

    match = re.match(r"^palier_(.+)_superior-(\d+)_uvc$", param_column_name)
    if match:
        return match.group(1), int(match.group(2)), None

    return None

# -----

def import_transactions(
    param_file_path: str,
    param_progress_callback=None,
    param_transaction_date: date | None = None,
    param_mapping_path: str | None = None,
) -> dict:
    """
    Import d'un fichier Excel de transactions au format brut (product_detail_export.xlsx)

    Pipeline : normalisation des colonnes et des unités → détection des marques →
    keyword matching → insertion/mise à jour du catalogue → insertion des transactions

    param_transaction_date : date associée à toutes les transactions. Par défaut : date du jour
    param_mapping_path : chemin vers mapping_product.xlsx — obligatoire
    """

    if not param_mapping_path:
        raise ValueError(
            "param_mapping_path est requis. "
            "Fournissez le chemin vers mapping_product.xlsx depuis l'interface."
        )

    transaction_date = param_transaction_date or date.today()

    # -----

    def _progression_bar(param_percentage: int, param_message: str) -> None:
        """ Met à jour la barre de progression """

        if param_progress_callback:
            param_progress_callback(param_percentage, param_message)

        return None

    # -----

    # ── Étape 1a : Lecture et normalisation des colonnes ─────────────────────
    _progression_bar(0, "Lecture du fichier…")

    dataframe = pd.read_excel(param_file_path)
    dataframe.dropna(how="all", inplace=True)
    dataframe.reset_index(drop=True, inplace=True) # Réindexer après suppression des lignes vides

    # Supprimer les lignes de métadonnées (ex : pied de page "Filtres appliqués")
    filter_mask = dataframe.apply(
        lambda row: row.astype(str).str.contains("Filtres appliqués", case=False, na=False).any(),
        axis=1
    )
    # Vérifier si au moins une ligne correspond au filtre
    if filter_mask.any():
        dataframe = dataframe[~filter_mask].reset_index(drop=True)

    if "DISTRIBUTEUR" not in dataframe.columns:
        raise ValueError(
            "Format de fichier non reconnu : colonne 'DISTRIBUTEUR' absente. "
            "Importez un fichier au format brut (product_detail_export.xlsx)."
        )

    dataframe = dataframe.rename(columns=RAW_COLUMN_MAP)

    # next() permet de trouver la première colonne contenant "Fac" ou "fac" dans son nom
    quantity_column = next((column for column in dataframe.columns if "Fac" in column or "fac" in column), None)
    if quantity_column:
        dataframe = dataframe.rename(columns={quantity_column: "quantity"})

    if "Montant HT" in dataframe.columns:
        dataframe = dataframe.rename(columns={"Montant HT": "amount_ht"})

    # ── Étape 1b : Nettoyage et keyword matching ─────────────────────────────
    _progression_bar(5, "Attribution des noms produits…")

    dataframe["unit"]         = dataframe["unit"].str.upper().replace(RAW_UNIT_MAP)
    dataframe["product_code"] = dataframe["product_code"].str.upper().replace(RAW_CODE_MAP)

    # Détection de la marque depuis la description et le code produit
    for brand_keyword in DESCRIPTION_BRAND_KEYWORDS:
        mask = (
            dataframe["description"].str.contains(brand_keyword, case=False, na=False) |
            dataframe["product_code"].str.contains(brand_keyword, case=False, na=False)
        )
        dataframe.loc[mask, "brand"] = brand_keyword

    # Title case sur toutes les colonnes texte + correction des majuscules après apostrophe
    # object est le type de données pour les colonnes texte dans pandas
    for column in dataframe.select_dtypes(include=["object"]).columns:
        dataframe[column] = (
            dataframe[column]
            .str.title()
            .str.replace(r"(?<=')([A-Z])", lambda match: match.group(0).lower(), regex=True)
        )

    # Correction des marques après title case (Hellmanns → Hellmann's, etc.)
    dataframe["brand"] = dataframe["brand"].map(
        lambda brand: BRAND_CORRECTION.get(brand, brand) if pd.notna(brand) else brand
    )

    mapping_keywords = pd.read_excel(param_mapping_path, sheet_name="mapping_products")

    # On boucle sur chaque ligne du dataframe pour trouver le product_name correspondant via le keyword matching
    dataframe["product_name"] = dataframe.apply(
        lambda row: find_product_name_method(row, mapping_keywords), axis=1
    )

    # Exemple de ce qui pourra être converti en numérique : "1 234,56" → 1234.56; "100" → 100.0,;"abc" → NaN
    dataframe["quantity"]  = pd.to_numeric(dataframe["quantity"],  errors="coerce").fillna(0) # coerce = NaN pour les valeurs non convertibles
    dataframe["amount_ht"] = pd.to_numeric(dataframe["amount_ht"], errors="coerce").fillna(0)

    # product_code peut être lu comme int par pandas (ex. 00123 → 123), description/data_source
    # peuvent contenir des NaN (NaN considéré comme float) -> fillna + astype(str) + replace garantit des str propres en base
    for column in ("product_code", "description", "data_source"):
        dataframe[column] = dataframe[column].fillna("").astype(str).replace("nan", "")

    # ── Étape 2 : Alimentation des tables de référence ───────────────────────
    _progression_bar(10, "Mise à jour des tables de référence…")

    with get_connection() as connection:
        get_or_create_many(param_connection=connection, param_table="distributor", param_column_name="distributor_name", param_values=dataframe["distributor"])
        get_or_create_many(param_connection=connection, param_table="data_source", param_column_name="data_source_name", param_values=dataframe["data_source"])
        get_or_create_many(param_connection=connection, param_table="industrial", param_column_name="industrial_name", param_values=dataframe["industrial"])
        get_or_create_many(param_connection=connection, param_table="brand", param_column_name="brand_name", param_values=dataframe["brand"])
        get_or_create_many(param_connection=connection, param_table="unit", param_column_name="unit_name", param_values=dataframe["unit"])
        # Toutes les catégories du mapping doivent exister avant l'insertion des produits
        get_or_create_many(param_connection=connection, param_table="category", param_column_name="category_name", param_values=mapping_keywords["categories"])
        get_or_create(param_connection=connection, param_table="category", param_column_name="category_name", param_value="Non catégorisé")

        connection.commit()

    # ── Étape 3a : Chargement du catalogue ───────────────────────────────────
    _progression_bar(25, "Chargement du catalogue produits…")

    with get_connection() as connection:
        database_distributor = pd.read_sql(
            text("SELECT id_distributor, distributor_name FROM distributor"), connection
        )

        database_product = pd.read_sql(
            text("""
                SELECT product.id_product, product.product_name, product.product_code, product.description,
                product.fk_id_brand, product.fk_id_category, data_source_table.data_source_name AS data_source
                FROM product
                JOIN data_source AS data_source_table ON data_source_table.id_data_source = product.fk_id_data_source
                ORDER BY product.id_product
            """),
            connection
        )

        for column in ("product_code", "description", "data_source"):
            database_product[column] = database_product[column].fillna("").astype(str).replace("nan", "")

        # Un seul accord par (fk_id_brand, fk_id_category)
        database_agreement = pd.read_sql(
            text("SELECT id_agreement, fk_id_brand, fk_id_category FROM agreement"),
            connection
        )

        database_agreement = database_agreement.drop_duplicates(
            subset=["fk_id_brand", "fk_id_category"], keep="first"
        )

    # ── Étape 3b : Insertion et mise à jour des produits ─────────────────────
    _progression_bar(32, "Insertion des nouveaux produits…")

    with get_connection() as connection:
        database_brand_reference      = pd.read_sql(text("SELECT id_brand, brand_name FROM brand"),                   connection)
        database_category_reference   = pd.read_sql(text("SELECT id_category, category_name FROM category"),          connection)
        database_unit_reference       = pd.read_sql(text("SELECT id_unit, unit_name FROM unit"),                      connection)
        database_datasource_reference = pd.read_sql(text("SELECT id_data_source, data_source_name FROM data_source"), connection)

    # Dictionnaires de correspondance {nom: id} pour les FK
    brand_id_map      = dict(zip(database_brand_reference["brand_name"],            database_brand_reference["id_brand"].astype(int)))
    category_id_map   = dict(zip(database_category_reference["category_name"],      database_category_reference["id_category"].astype(int)))
    unit_id_map       = dict(zip(database_unit_reference["unit_name"],              database_unit_reference["id_unit"].astype(int)))
    datasource_id_map = dict(zip(database_datasource_reference["data_source_name"], database_datasource_reference["id_data_source"].astype(int)))

    # product_name → category_name depuis le mapping (fruit du keyword matching)
    product_name_to_category: dict = {
        str(mapping_row["product_name"]): str(mapping_row["categories"])
        for _, mapping_row in mapping_keywords.iterrows()
        if pd.notna(mapping_row.get("product_name")) and pd.notna(mapping_row.get("categories"))
    }

    # Clé d'existence en base : (product_code, description, data_source)
    existing_keys: set = set(zip(
        database_product["product_code"],
        database_product["description"],
        database_product["data_source"],
    ))

    # Une ligne par clé unique — préférer celles avec product_name renseigné
    # les product_name à NaN sont à la fin du dataframe
    unique_products_dataframe = (
        dataframe
        .sort_values("product_name", na_position="last")
        .drop_duplicates(subset=["product_code", "description", "data_source"], keep="first")
    )

    new_products: list = []
    for _, product_row in unique_products_dataframe.iterrows():
        product_code = str(product_row.get("product_code", ""))
        description = str(product_row.get("description",  ""))
        data_source = str(product_row.get("data_source",  ""))
        key = (product_code, description, data_source)

        # Si le produit existe déjà en base, on ne l'insère pas
        if key in existing_keys:
            continue

        # On récupère les noms de marque, catégorie, unité et source de données pour résoudre les FK
        product_name = product_row.get("product_name") if pd.notna(product_row.get("product_name")) else None
        brand_name = str(product_row["brand"]) if pd.notna(product_row.get("brand")) else None
        unit_name = str(product_row["unit"]) if pd.notna(product_row.get("unit")) else None
        datasource_name = str(product_row["data_source"]) if pd.notna(product_row.get("data_source")) else None

        id_brand = brand_id_map.get(brand_name) if brand_name else None
        id_unit = unit_id_map.get(unit_name) if unit_name else None
        id_datasource = datasource_id_map.get(datasource_name) if datasource_name else None

        # Catégorie depuis le keyword matching → "Non catégorisé" si non résolu
        category_name = product_name_to_category.get(product_name) if product_name else None
        id_category = category_id_map.get(category_name) if category_name else category_id_map.get("Non catégorisé")

        # ⚠️ ATTENTION : si une FK n'a pas pu être résolue (brand/catégorie/unit/data_source introuvable)
        # le produit est ignoré silencieusement
        # Il ne sera jamais inséré en base → les transactions liées à ce produit seront également
        # ignorées (skippées dans la boucle d'insertion des transactions) et n'apparaîtront
        # pas du tout dans la table transaction
        # TODO : envisager un mécanisme de log pour les produits ignorés
        if not all([id_brand, id_category, id_unit, id_datasource]):
            continue

        new_products.append({
            "fk_id_brand":       id_brand,
            "fk_id_category":    id_category,
            "fk_id_unit":        id_unit,
            "fk_id_data_source": id_datasource,
            "product_name":      product_name,
            "product_code":      product_code or None,
            "description":       description  or None,
        })

    if new_products:
        with get_connection() as connection:
            for value in new_products:
                connection.execute(
                    text("""
                        INSERT INTO product
                            (fk_id_brand, fk_id_category, fk_id_unit, fk_id_data_source,
                            product_name, product_code, description)
                        VALUES
                            (:fk_id_brand, :fk_id_category, :fk_id_unit, :fk_id_data_source,
                            :product_name, :product_code, :description)
                    """),
                    value
                )

            connection.commit()

    # Mise à jour des produits existants : product_name et fk_id_category synchronisés
    # avec le mapping courant, pour tous les produits que le keyword matching résout.
    products_to_update = (
        unique_products_dataframe[unique_products_dataframe["product_name"].notna()]
        [["product_code", "description", "data_source", "product_name"]]
        .drop_duplicates(subset=["product_code", "description", "data_source"])
    )

    if not products_to_update.empty:
        with get_connection() as connection:
            for _, update_row in products_to_update.iterrows():
                product_name  = update_row["product_name"]
                category_name = product_name_to_category.get(product_name)
                id_category   = category_id_map.get(category_name) if category_name else category_id_map.get("Non catégorisé")

                connection.execute(
                    text("""
                        UPDATE product
                        SET product_name   = :product_name,
                            fk_id_category = :fk_id_category
                        WHERE product_code = :product_code
                            AND description  = :description
                            AND fk_id_data_source = (
                                SELECT id_data_source FROM data_source
                                WHERE data_source_name = :data_source
                            )
                    """),
                    {
                        "product_name":   product_name,
                        "fk_id_category": id_category,
                        "product_code":   update_row["product_code"],
                        "description":    update_row["description"],
                        "data_source":    update_row["data_source"],
                    },
                )

            connection.commit()

    # Recharger le catalogue pour que l'étape 4 trouve les produits nouvellement insérés
    with get_connection() as connection:
        database_product = pd.read_sql(
            text("""
                SELECT product.id_product, product.product_name, product.product_code, product.description,
                    product.fk_id_brand, product.fk_id_category, data_source_table.data_source_name AS data_source
                FROM product
                JOIN data_source AS data_source_table ON data_source_table.id_data_source = product.fk_id_data_source
                ORDER BY product.id_product
            """),
            connection
        )

        for column in ("product_code", "description", "data_source"):
            database_product[column] = database_product[column].fillna("").astype(str).replace("nan", "")

    # ── Étape 4 : Résolution des clés étrangères ─────────────────────────────
    _progression_bar(40, "Résolution des clés étrangères…")

    # distributor → id_distributor
    dataframe = dataframe.merge(
        database_distributor.rename(columns={"distributor_name": "distributor"}),
        on="distributor",
        how="left",
    )

    # (product_code, description, data_source) → id_product + fk_id_brand, fk_id_category
    # Dédoublonnage du catalogue pour le merge : un seul id_product par (product_code, description, data_source)
    # Évite les doublons de lignes dans le dataframe si plusieurs enregistrements partagent la même clé
    database_product_deduplicate = database_product.drop_duplicates(subset=["product_code", "description", "data_source"], keep="first")
    dataframe = dataframe.merge(
        database_product_deduplicate[["id_product", "product_code", "description", "data_source", "fk_id_brand", "fk_id_category"]],
        on=["product_code", "description", "data_source"],
        how="left",
    )

    # (fk_id_brand, fk_id_category) → id_agreement (accord actif le plus récent)
    dataframe = dataframe.merge(
        database_agreement,
        on=["fk_id_brand", "fk_id_category"],
        how="left",
    )

    # Remplacer les 0 par NaN pour éviter la division par zéro (Erreur en Python)
    safe_quantity = dataframe["quantity"].replace(0, float("nan"))
    dataframe["unit_price"] = (dataframe["amount_ht"] / safe_quantity).round(2).fillna(0.0)

    # ── Étape 5 : Insertion des transactions ─────────────────────────────────
    _progression_bar(55, "Insertion des transactions…")

    # On vide la table avant chaque import : la table transaction est entièrement
    # dérivée des fichiers source + mapping et peut être reconstruite à tout moment.
    # Cela évite les doublons quand le mapping change (fk_id_product reclassé).
    with get_connection() as connection:
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 0")) # Désactiver les contraintes FK pour pouvoir vider la table
        connection.execute(text("TRUNCATE TABLE transaction"))
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 1")) # Réactiver les contraintes FK après le vidage de la table
        connection.commit()

    insert_transaction_sql = text("""
        INSERT INTO transaction
            (fk_id_product, fk_id_agreement, fk_id_distributor,
            quantity, unit_price, total_price, transaction_date)
        VALUES
            (:fk_id_product, :fk_id_agreement, :fk_id_distributor,
            :quantity, :unit_price, :total_price, :transaction_date)
    """)

    inserted      = 0
    null_fk_count = 0
    total         = len(dataframe)

    with get_connection() as connection:
        for index_dataframe, (_, row) in enumerate(dataframe.iterrows()):
            fk_id_product     = int(row["id_product"])     if pd.notna(row.get("id_product"))     else None
            fk_id_distributor = int(row["id_distributor"]) if pd.notna(row.get("id_distributor")) else None
            fk_id_agreement   = int(row["id_agreement"])   if pd.notna(row.get("id_agreement"))   else None
            unit_price        = float(row["unit_price"])    if pd.notna(row.get("unit_price"))     else 0.0
            quantity          = int(row["quantity"])
            total_price       = float(row["amount_ht"])

            # Produit ou distributeur non résolu : impossible d'insérer une transaction cohérente
            if not fk_id_product or not fk_id_distributor:
                null_fk_count += 1
                continue

            connection.execute(
                insert_transaction_sql,
                {
                    "fk_id_product":     fk_id_product,
                    "fk_id_agreement":   fk_id_agreement,
                    "fk_id_distributor": fk_id_distributor,
                    "quantity":          quantity,
                    "unit_price":        unit_price,
                    "total_price":       total_price,
                    "transaction_date":  transaction_date,
                },
            )

            inserted += 1
            # Mise à jour de la barre de progression toutes les 50 transactions pour éviter un trop grand nombre d'appels
            if index_dataframe % 50 == 0:
                _progression_bar(55 + int(38 * index_dataframe / total), f"Insertion {index_dataframe + 1}/{total}…")

        connection.commit()

    _progression_bar(100, f"{inserted} transactions insérées")

    return {
        "inserted": inserted,
        "null_fk": null_fk_count,
        "total": total,
        "transaction_date_used": transaction_date.isoformat()
    }

# -----

def import_conversions(param_file_path: str, param_progress_callback=None) -> dict:
    """
    Import du fichier de correspondance (table_correspondance.xlsx)

    Lit le fichier Excel renseigné par le client et insert ou met à jour la table
    product_conversion avec les facteurs de conversion et les unités accord

    Colonnes attendues dans le fichier :
    - Distributeur
    - Code produit
    - Unité transaction (UF)
    - Unité accord
    - Facteur de conversion
    """

    # -----

    def _progression_bar(param_percentage: int, param_message: str) -> None:
        """ Met à jour la barre de progression """

        if param_progress_callback:
            param_progress_callback(param_percentage, param_message)

        return None

    # -----

    _progression_bar(0, "Lecture du fichier de correspondance…")

    dataframe = pd.read_excel(param_file_path)

    # Vérification des colonnes minimales requises
    required = {"Distributeur", "Code produit", "Unité transaction (UF)", "Unité accord", "Facteur de conversion"}
    missing  = required - set(dataframe.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes dans le fichier : {missing}")

    # Supprimer les lignes avec des valeurs manquantes et renommer les colonnes
    dataframe = dataframe.dropna(subset=["Distributeur", "Code produit", "Unité transaction (UF)", "Unité accord", "Facteur de conversion"])
    dataframe = dataframe.rename(columns={
        "Distributeur":           "distributor_name",
        "Code produit":           "product_code",
        "Unité transaction (UF)": "transaction_unit",
        "Unité accord":           "agreement_unit",
        "Facteur de conversion":  "conversion_factor",
    })

    total = len(dataframe)
    _progression_bar(20, f"{total} lignes à traiter…")

    with get_connection() as connection:
        connection.execute(text("DELETE FROM product_conversion"))
        connection.commit()

    insert_sql = text("""
        INSERT INTO product_conversion
            (distributor_name, product_code, transaction_unit, agreement_unit, conversion_factor)
        VALUES
            (:distributor_name, :product_code, :transaction_unit, :agreement_unit, :conversion_factor)
    """)

    processed = 0
    with get_connection() as connection:
        # index_counter est utilisé pour la barre de progression, _ est l'index de la ligne dans le dataframe
        for index_counter, (_, row) in enumerate(dataframe.iterrows()):
            connection.execute(insert_sql, {
                "distributor_name": str(row["distributor_name"]),
                "product_code":     str(row["product_code"]),
                "transaction_unit": str(row["transaction_unit"]),
                "agreement_unit":   str(row["agreement_unit"]),
                "conversion_factor": float(row["conversion_factor"]),
            })
            processed += 1
            if index_counter % 50 == 0:
                _progression_bar(20 + int(75 * index_counter / max(total, 1)), f"Traitement {index_counter + 1}/{total}…")

        connection.commit()

    _progression_bar(100, f"{processed} correspondances importées.")

    return {
        "processed": processed,
        "total":     total,
    }

# -----

def import_agreements(param_file_path: str, param_progress_callback=None) -> dict:
    """
    Import d'un fichier Excel de mapping (format mapping_product.xlsx)

    Stratégie : suppression totale puis réinsertion
    Tous les accords et paliers existants sont supprimés, puis les nouveaux
    sont insérés depuis le fichier. Les transactions dont fk_id_agreement
    pointait vers un ancien accord passent automatiquement à NULL (ON DELETE SET NULL)
    Appeler resolve_agreements_method() après l'import pour rerésoudre les FK
    """

    def _progression_bar(param_percentage: int, param_message: str) -> None:
        """ Met à jour la barre de progression """

        if param_progress_callback:
            param_progress_callback(param_percentage, param_message)

        return None

    # ── Étape 1 : Lecture et validation du fichier ───────────────────────────
    _progression_bar(0, "Lecture du fichier accords…")

    excel_file = pd.ExcelFile(param_file_path)
    sheet      = "mapping_products" if "mapping_products" in excel_file.sheet_names else excel_file.sheet_names[0]
    mapping    = pd.read_excel(param_file_path, sheet_name=sheet)

    required = {"brand", "categories"}
    missing  = required - set(mapping.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes dans le fichier mapping : {missing}")

    # Normalisation de Hellmanns → Hellmann's
    mapping["brand"] = mapping["brand"].map(
        lambda brand: BRAND_CORRECTION.get(brand, brand) if pd.notna(brand) else brand
    )

    palier_columns = [column for column in mapping.columns if column.startswith("palier_")]
    if not palier_columns:
        raise ValueError("Aucune colonne palier_* trouvée dans le fichier.")

    # -----

    def _detect_palier_group(param_row):
        """ Détecte le palier_group depuis les colonnes palier_* (ex : 'knorr', 'dressing+maizena+TVB') """

        for column in palier_columns:
            if pd.notna(param_row.get(column)):
                parsed = parse_palier_column_name_method(column)
                if parsed:
                    return parsed[0]

        return None

    # -----

    mapping["palier_group"] = mapping.apply(_detect_palier_group, axis=1)

    # ── Étape 2 : Alimentation des tables de référence ───────────────────────
    _progression_bar(10, "Mise à jour des tables de référence…")

    with get_connection() as connection:
        get_or_create_many(connection, "brand",      "brand_name",      mapping["brand"])
        get_or_create_many(connection, "category",   "category_name",   mapping["categories"])
        get_or_create(connection,      "unit",       "unit_name",       "UVC")
        get_or_create(connection,      "industrial", "industrial_name", INDUSTRIAL_NAME)

        connection.commit()

        database_brand      = pd.read_sql(text("SELECT id_brand, brand_name FROM brand"),                connection)
        database_category   = pd.read_sql(text("SELECT id_category, category_name FROM category"),       connection)
        database_industrial = pd.read_sql(text("SELECT id_industrial, industrial_name FROM industrial"), connection)
        database_unit       = pd.read_sql(text("SELECT id_unit, unit_name FROM unit"),                   connection)

    # Récupération des id_unit et id_industrial pour les FK
    id_unit_uvc   = int(database_unit.loc[database_unit["unit_name"] == "UVC", "id_unit"].iloc[0])
    id_industrial = int(database_industrial.loc[database_industrial["industrial_name"] == INDUSTRIAL_NAME, "id_industrial"].iloc[0])

    # ── Étape 3 : Suppression de tous les accords et paliers existants ───────
    # agreement_tier est supprimé en cascade depuis agreement (ON DELETE CASCADE).
    # Les transactions passent automatiquement à fk_id_agreement = NULL (ON DELETE SET NULL).
    # Appeler resolve_agreements_method() après cet import pour rerésoudre les FK.
    _progression_bar(25, "Suppression des accords existants…")

    with get_connection() as connection:
        connection.execute(text("DELETE FROM agreement"))
        connection.commit()

    # ── Étape 4 : Construction de la liste de travail ────────────────────────
    # copy() pour éviter le SettingWithCopyWarning lors de l'itération sur mapping_work
    mapping_work = mapping[["brand", "categories", "palier_group"]].drop_duplicates(subset=["brand", "categories"]).copy()
    mapping_work = mapping_work.merge(
        database_brand.rename(columns={"brand_name": "brand"}), on="brand", how="left"
    )
    mapping_work = mapping_work.merge(
        database_category.rename(columns={"category_name": "categories"}), on="categories", how="left"
    )

    # ── Étape 5 : Insertion des nouveaux accords ──────────────────────────────
    _progression_bar(40, "Insertion des nouveaux accords…")

    insert_agreement_sql = text("""
        INSERT INTO agreement
            (fk_id_brand, fk_id_category, fk_id_industrial, fk_id_unit, palier_group)
        VALUES
            (:fk_id_brand, :fk_id_category, :fk_id_industrial, :fk_id_unit, :palier_group)
    """)

    new_agreement_rows: list = []
    with get_connection() as connection:

        # Insère un accord par (fk_id_brand, fk_id_category) unique
        for _, work_row in mapping_work.iterrows():
            if pd.isna(work_row.get("id_brand")) or pd.isna(work_row.get("id_category")):
                continue

            result = connection.execute(
                insert_agreement_sql,
                {
                    "fk_id_brand":      int(work_row["id_brand"]),
                    "fk_id_category":   int(work_row["id_category"]),
                    "fk_id_industrial": id_industrial,
                    "fk_id_unit":       id_unit_uvc,
                    "palier_group":     work_row.get("palier_group") if pd.notna(work_row.get("palier_group")) else None,
                },
            )
            new_agreement_rows.append((work_row, int(result.lastrowid)))

        connection.commit()

    # ── Étape 6 : Insertion des paliers ───────────────────────────────────────
    _progression_bar(70, "Insertion des paliers…")

    insert_tier_sql = text("""
        INSERT INTO agreement_tier (fk_id_agreement, min_volume, max_volume, price)
        VALUES (:fk_id_agreement, :min_volume, :max_volume, :price)
    """)

    tier_count = 0
    with get_connection() as connection:
        for work_row, new_id_agreement in new_agreement_rows:
            palier_group = work_row.get("palier_group") if pd.notna(work_row.get("palier_group")) else None
            reference_rows = mapping[
                (mapping["brand"] == work_row["brand"]) &
                (mapping["categories"] == work_row["categories"])
            ]

            if reference_rows.empty:
                continue

            reference_row = reference_rows.iloc[0]
            for column in palier_columns:
                parsed = parse_palier_column_name_method(column)
                if not parsed:
                    continue

                group, min_volume, max_volume = parsed
                if group != palier_group:
                    continue

                price = reference_row.get(column)
                if pd.isna(price):
                    continue

                connection.execute(
                    insert_tier_sql,
                    {
                        "fk_id_agreement": new_id_agreement,
                        "min_volume": min_volume,
                        "max_volume": max_volume,
                        "price":           float(price),
                    },
                )
                tier_count += 1

        connection.commit()

    _progression_bar(100, f"{len(new_agreement_rows)} accords insérés — {tier_count} paliers insérés.")

    return {
        "agreements": len(new_agreement_rows),
        "tiers":      tier_count,
    }

# -----

def resolve_agreements_method(param_progress_callback=None) -> None:
    """
    Rerésout fk_id_agreement sur toutes les transactions dont la FK est NULL.

    À appeler après import_agreements() pour que les transactions existantes
    retrouvent un accord valide. La résolution se fait via (fk_id_brand, fk_id_category)
    du produit associé à chaque transaction.

    Retourne un résumé : transactions mises à jour, transactions toujours sans accord.
    """

    # -----

    def _progression_bar(param_percentage: int, param_message: str) -> None:
        """ Met à jour la barre de progression """

        if param_progress_callback:
            param_progress_callback(param_percentage, param_message)

        return None

    # -----

    _progression_bar(0, "Rerésolution des accords sur les transactions…")

    # Met à jour fk_id_agreement sur toutes les transactions sans accord,
    # en joignant product → brand/category → agreement
    # Les transactions sans produit ou sans accord correspondant restent à NULL
    resolve_sql = text("""
        UPDATE transaction
        JOIN product ON product.id_product = transaction.fk_id_product
        JOIN agreement ON agreement.fk_id_brand = product.fk_id_brand
            AND agreement.fk_id_category = product.fk_id_category
        SET transaction.fk_id_agreement = agreement.id_agreement
        WHERE transaction.fk_id_agreement IS NULL
            AND transaction.fk_id_product IS NOT NULL
    """)

    with get_connection() as connection:
        connection.execute(resolve_sql)
        connection.commit()

    _progression_bar(100, "Rerésolution terminée.")

    return None
