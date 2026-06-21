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

# Pattern regex pour détecter les codes UPC dans la description, par exemple "12x250ml", "6X1L", "x3", etc.
UPC_PATTERN = re.compile(r'\d+[A-Za-z]+[xX*](\d+)|\d+[xX*](\d+)|(?<![A-Za-z\d])[xX](\d+)')

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

        if not any(keyword_brand in brand_norm for keyword_brand in keywords_brands):
            continue

        keywords_others = [
            normalize_string_method(keyword_other)
            for keyword_other in str(rule["keywords_others"]).split(";")
            if keyword_other.strip()
        ]

        # Compter le nombre de mots-clés présents dans la description normalisée
        matched = sum(1 for keyword_other in keywords_others if keyword_other in description_norm)

        if matched > 0 and matched > best_score:
            best_score        = matched
            best_product_name = rule["product_name"]

    return best_product_name

# -----

def parse_palier_column_name_method(param_column_name: str):
    """
    Retourne (group_key, min_uvc, max_uvc_inclusive) ou None.
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

def import_transactions(param_file_path: str, param_progress_callback=None, param_transaction_date: date | None = None,) -> dict:
    """
    Import d'un fichier Excel de transactions.
    Accepte le format brut (colonnes françaises) et le format final (colonnes anglaises avec product_name).
    En format brut : nettoyage des unités, détection des marques, insertion des nouveaux produits.
    La catégorie des nouveaux produits est déduite des accords actifs en base de données.
    param_transaction_date : date à associer aux transactions importées — par défaut, la date du jour.
    Ajoute de nouvelles transactions; résout les FK à partir du catalogue et des accords existants.
    """

    transaction_date = param_transaction_date or date.today()

    # -----

    def _progression_bar(param_percentage: int, param_message: str) -> None:
        """ Met à jour la barre de progression """

        if param_progress_callback:
            param_progress_callback(param_percentage, param_message)

        return None

    # -----

    # ── Étape 1 : Lecture et normalisation des colonnes ──────────────────────
    _progression_bar(0, "Lecture du fichier…")

    dataframe = pd.read_excel(param_file_path)
    dataframe.dropna(how="all", inplace=True)
    dataframe.reset_index(drop=True, inplace=True) # Réindexer après suppression des lignes vides

    # Supprimer les lignes de métadonnées (ex : pied de page "Filtres appliqués" ou "filtres appliqués" des exports filtrés)
    filter_mask = dataframe.apply(
        lambda row: row.astype(str).str.contains("Filtres appliqués", case=False, na=False).any(),
        axis=1
    )
    if filter_mask.any():
        dataframe = dataframe[~filter_mask].reset_index(drop=True)

    # Auto-détection du format brut : renommage des colonnes françaises
    is_raw_format = "DISTRIBUTEUR" in dataframe.columns
    if is_raw_format:
        dataframe = dataframe.rename(columns=RAW_COLUMN_MAP)
        quantity_column = next((column for column in dataframe.columns if "Fac" in column or "fac" in column), None)

        if quantity_column:
            dataframe = dataframe.rename(columns={quantity_column: "quantity"})

        if "Montant HT" in dataframe.columns:
            dataframe = dataframe.rename(columns={"Montant HT": "amount_ht"})

    # ── Étape 1b : Nettoyage et attribution du product_name (format brut) ────
    if is_raw_format:
        _progression_bar(5, "Attribution des noms produits…")

        # Normalisation des codes unités (BTE → BOÎTE, U → UNITÉ, etc.)
        if "unit" in dataframe.columns:
            dataframe["unit"] = dataframe["unit"].str.upper().replace(RAW_UNIT_MAP)

        # Correction des codes produits connus (HELLMANNSQUEEZE → HELLMANN'S SQUEEZE, etc.)
        if "product_code" in dataframe.columns:
            dataframe["product_code"] = dataframe["product_code"].str.upper().replace(RAW_CODE_MAP)

        # Détection de la marque depuis la description et le code produit
        for brand_keyword in DESCRIPTION_BRAND_KEYWORDS:
            mask_description = dataframe["description"].str.contains(brand_keyword, case=False, na=False)
            mask_code = (
                dataframe["product_code"].str.contains(brand_keyword, case=False, na=False)
                if "product_code" in dataframe.columns
                else pd.Series(False, index=dataframe.index)
            )
            dataframe.loc[mask_description | mask_code, "brand"] = brand_keyword

        # Title case sur toutes les colonnes texte, vérification des majuscules après apostrophe (ex : Hellmann's → Hellmann's, pas Hellmann'S)
        for column in dataframe.select_dtypes(include=["object"]).columns:
            dataframe[column] = (
                dataframe[column]
                .str.title()
                .str.replace(r"(?<=')([A-Z])", lambda match: match.group(0).lower(), regex=True)
            )

        # Correction des marques après title case (Hellmanns → Hellmann's, etc.)
        if "brand" in dataframe.columns:
            dataframe["brand"] = dataframe["brand"].map(
                lambda brand: BRAND_CORRECTION.get(brand, brand) if pd.notna(brand) else brand
            )

        # product_name sera résolu depuis la base de données pour les produits existants (étape 4)
        if "product_name" not in dataframe.columns:
            dataframe["product_name"] = None

    required = {"distributor", "product_name", "quantity", "amount_ht"}
    missing = required - set(dataframe.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes dans le fichier : {missing}")

    dataframe["quantity"]  = pd.to_numeric(dataframe["quantity"],  errors="coerce").fillna(0) # coerce = NaN pour les valeurs non convertibles
    dataframe["amount_ht"] = pd.to_numeric(dataframe["amount_ht"], errors="coerce").fillna(0)

    if "brand" in dataframe.columns:
        dataframe["brand"] = dataframe["brand"].map(
            lambda brand: BRAND_CORRECTION.get(brand, brand) if pd.notna(brand) else brand
        )

    # Normaliser product_code, description et data_source à "" pour les NaN (clé de join cohérente)
    for column in ("product_code", "description", "data_source"):
        if column in dataframe.columns:
            dataframe[column] = dataframe[column].fillna("").astype(str).replace("nan", "")
        else:
            dataframe[column] = ""

    # ── Étape 2 : Alimentation des tables de référence ───────────────────────
    _progression_bar(10, "Mise à jour des tables de référence…")

    with get_connection() as connection:
        get_or_create_many(param_connection=connection, param_table="distributor", param_column_name="distributor_name", param_values=dataframe["distributor"])
        if "data_source" in dataframe.columns:
            get_or_create_many(param_connection=connection, param_table="data_source", param_column_name="data_source_name", param_values=dataframe["data_source"])
        if "industrial" in dataframe.columns:
            get_or_create_many(param_connection=connection, param_table="industrial", param_column_name="industrial_name", param_values=dataframe["industrial"])
        if "brand" in dataframe.columns:
            get_or_create_many(param_connection=connection, param_table="brand", param_column_name="brand_name", param_values=dataframe["brand"])
        if "unit" in dataframe.columns:
            get_or_create_many(param_connection=connection, param_table="unit", param_column_name="unit_name", param_values=dataframe["unit"])
        get_or_create(param_connection=connection, param_table="category", param_column_name="category_name", param_value="Non catégorisé")
        connection.commit()

    # ── Étape 3 : Chargement du catalogue ────────────────────────────────────
    _progression_bar(25, "Chargement du catalogue produits…")

    with get_connection() as connection:
        database_distributor = pd.read_sql(
            text("SELECT id_distributor, distributor_name FROM distributor"), connection
        )

        database_product = pd.read_sql(
            text("""
                SELECT product.id_product, product.product_name, product.product_code, product.description,
                product.fk_id_brand, product.fk_id_category, data_source_table.data_source_name as data_source
                FROM product
                JOIN data_source AS data_source_table ON data_source_table.id_data_source = product.fk_id_data_source
            """),
            connection
        )

        for column in ("product_code", "description", "data_source"):
            database_product[column] = database_product[column].fillna("").astype(str).replace("nan", "")

        # Uniquement les accords actifs (end_date >= aujourd'hui) — ORDER BY start_date DESC
        # pour que drop_duplicates ci-dessous conserve le plus récent en premier
        database_agreement = pd.read_sql(
            text("""
                SELECT id_agreement, fk_id_brand, fk_id_category
                FROM agreement
                WHERE end_date >= CURDATE()
                ORDER BY start_date DESC
            """),
            connection
        )

        # On garde le plus récent par (fk_id_brand, fk_id_category)
        # en cas de doublons (accords actifs multiples pour la même marque/catégorie)
        database_agreement = database_agreement.drop_duplicates(
            subset=["fk_id_brand", "fk_id_category"], keep="first"
        )

    # ── Étape 3b : Insertion des nouveaux produits ───────────────────────────
    if is_raw_format:
        _progression_bar(32, "Insertion des nouveaux produits…")

        with get_connection() as connection:
            database_brand_reference        = pd.read_sql(text("SELECT id_brand, brand_name FROM brand"),                   connection)
            database_category_reference     = pd.read_sql(text("SELECT id_category, category_name FROM category"),          connection)
            database_unit_reference         = pd.read_sql(text("SELECT id_unit, unit_name FROM unit"),                      connection)
            database_datasource_reference   = pd.read_sql(text("SELECT id_data_source, data_source_name FROM data_source"), connection)
            database_brand_categories_agreement = pd.read_sql(
                text("SELECT DISTINCT fk_id_brand, fk_id_category FROM agreement WHERE end_date >= CURDATE()"),
                connection
            )

        # Dictionnaires de correspondance {nom: id} pour les FK
        brand_id_map      = dict(zip(database_brand_reference["brand_name"],            database_brand_reference["id_brand"].astype(int)))
        category_id_map   = dict(zip(database_category_reference["category_name"],      database_category_reference["id_category"].astype(int)))
        unit_id_map       = dict(zip(database_unit_reference["unit_name"],              database_unit_reference["id_unit"].astype(int)))
        datasource_id_map = dict(zip(database_datasource_reference["data_source_name"], database_datasource_reference["id_data_source"].astype(int)))

        # Catégorie depuis les accords actifs : une marque avec un seul accord actif → catégorie directe
        brand_to_category_id: dict = {}
        for brand_id, group in database_brand_categories_agreement.groupby("fk_id_brand"):
            categories_ids = group["fk_id_category"].unique()
            if len(categories_ids) == 1:
                brand_to_category_id[int(brand_id)] = int(categories_ids[0])

        # Clé d'existence : (product_code, description, data_source) — product_name peut être NULL
        existing_keys: set = set(
            zip(
                database_product["product_code"],
                database_product["description"],
                database_product["data_source"],
            )
        )

        # Une ligne par (product_code, description, data_source) unique — on préfère les lignes avec product_name
        unique_products_dataframe = (
            dataframe
            .sort_values("product_name", na_position="last")
            .drop_duplicates(subset=["product_code", "description", "data_source"], keep="first")
        )

        new_products: list = []
        seen_keys:    set  = set()

        for _, product_row in unique_products_dataframe.iterrows():
            product_name  = product_row.get("product_name") if pd.notna(product_row.get("product_name")) else None
            product_code  = str(product_row.get("product_code", ""))
            description  = str(product_row.get("description",  ""))
            data_source    = str(product_row.get("data_source",  ""))
            key    = (product_code, description, data_source)

            # existing_keys = déjà présent en base avant cet import
            # seen_keys     = déjà traité plus tôt dans cette boucle (même clé dans le fichier)
            if key in existing_keys or key in seen_keys:
                continue

            brand_name = str(product_row["brand"])       if pd.notna(product_row.get("brand"))       else None
            unit_name  = str(product_row["unit"])        if pd.notna(product_row.get("unit"))        else None
            datasource_name    = str(product_row["data_source"]) if pd.notna(product_row.get("data_source")) else None

            id_brand = brand_id_map.get(brand_name) if brand_name else None

            # Catégorie depuis les accords actifs en base de données
            id_category = brand_to_category_id.get(id_brand) if id_brand else None
            if not id_category:
                id_category = category_id_map.get("Non catégorisé")

            id_unit = unit_id_map.get(unit_name) if unit_name else None
            id_datasource   = datasource_id_map.get(datasource_name) if datasource_name else None

            if not all([id_brand, id_category, id_unit, id_datasource]):
                continue

            # units_per_case calculé depuis la description au moment de l'insertion
            units_per_case = 1
            if description:
                units_per_case_match = UPC_PATTERN.search(description)
                if units_per_case_match:
                    units_per_case = int(units_per_case_match.group(1) or units_per_case_match.group(2) or units_per_case_match.group(3))

            new_products.append({
                "fk_id_brand":       id_brand,
                "fk_id_category":    id_category,
                "fk_id_unit":        id_unit,
                "fk_id_data_source": id_datasource,
                "product_name":      product_name,
                "product_code":      product_code if product_code else None,
                "description":       description if description else None,
                "units_per_case":    units_per_case,
            })
            seen_keys.add(key)

        if new_products:
            insert_products_sql = text(
                """
                INSERT INTO product
                    (fk_id_brand, fk_id_category, fk_id_unit, fk_id_data_source,
                    product_name, product_code, description, units_per_case)
                VALUES
                    (:fk_id_brand, :fk_id_category, :fk_id_unit, :fk_id_data_source,
                    :product_name, :product_code, :description, :units_per_case)
                """
            )

            with get_connection() as connection:
                for value in new_products:
                    connection.execute(insert_products_sql, value)

                connection.commit()

            # Recharger le catalogue pour que le merge Étape 4 trouve les nouveaux produits
            with get_connection() as connection:
                database_product = pd.read_sql(
                    text("""
                        SELECT product.id_product, product.product_name, product.product_code, product.description,
                        product.fk_id_brand, product.fk_id_category, data_source_table.data_source_name AS data_source
                        FROM product
                        JOIN data_source data_source_table ON data_source_table.id_data_source = product.fk_id_data_source
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

    safe_quantity = dataframe["quantity"].replace(0, float("nan"))
    dataframe["unit_price"] = (dataframe["amount_ht"] / safe_quantity).round(2).fillna(0.0)

    # ── Étape 5 : Insertion des transactions ─────────────────────────────────
    _progression_bar(55, "Insertion des transactions…")

    insert_sql = text(
        """
        INSERT INTO `transaction`
            (fk_id_product, fk_id_agreement, fk_id_distributor,
            quantity, unit_price, total_price, transaction_date)
        VALUES
            (:fk_id_product, :fk_id_agreement, :fk_id_distributor,
            :quantity, :unit_price, :total_price, :transaction_date)
        """
    )

    inserted      = 0
    null_fk_count = 0
    total         = len(dataframe)

    with get_connection() as connection:
        for index_dataframe, (_, row) in enumerate(dataframe.iterrows()):
            has_null = (
                pd.isna(row.get("id_product"))
                or pd.isna(row.get("id_agreement"))
                or pd.isna(row.get("id_distributor"))
            )

            if has_null:
                null_fk_count += 1

            connection.execute(
                insert_sql,
                {
                    "fk_id_product":     int(row["id_product"])     if pd.notna(row.get("id_product"))     else None,
                    "fk_id_agreement":   int(row["id_agreement"])   if pd.notna(row.get("id_agreement"))   else None,
                    "fk_id_distributor": int(row["id_distributor"]) if pd.notna(row.get("id_distributor")) else None,
                    "quantity":          int(row["quantity"]),
                    "unit_price":        float(row["unit_price"])   if pd.notna(row.get("unit_price"))     else 0.0,
                    "total_price":       float(row["amount_ht"]),
                    "transaction_date":  transaction_date,
                },
            )

            inserted += 1
            if index_dataframe % 50 == 0:
                _progression_bar(55 + int(38 * index_dataframe / total), f"Insertion {index_dataframe + 1}/{total}…")

        connection.commit()

    _progression_bar(100, f"{inserted} transactions insérées ({null_fk_count} avec FK manquants).")

    return {
        "inserted": inserted,
        "null_fk":  null_fk_count,
        "total":    total,
        "transaction_date_used": transaction_date.isoformat(),
    }
