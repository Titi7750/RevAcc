# Documentation technique — `core_folder/`

> **À qui s'adresse ce document ?**
> À toute personne qui reprend ce projet sans l'avoir jamais vu. Chaque fichier, chaque fonction et chaque étape clé y sont expliqués avec des extraits de code commentés.

---

## Sommaire

1. [Vue d'ensemble](#1-vue-densemble)
2. [database_file.py — Connexion & utilitaires base de données](#2-database_filepy)
3. [import_file.py — Import des données](#3-import_filepy)
4. [calculation_file.py — Calcul des revenus d'accords](#4-calculation_filepy)
5. [export_file.py — Export Excel](#5-export_filepy)
6. [consultation_file.py — Lecture des données](#6-consultation_filepy)
7. [dashboard_file.py — Tableau de bord KPI](#7-dashboard_filepy)

---

## 1. Vue d'ensemble

Le dossier `core_folder/` contient toute la **logique métier** de l'application. Il n'y a ici aucun code d'interface graphique : seulement des fonctions Python pures qui lisent, transforment et écrivent des données.

```
core_folder/
├── database_file.py      ← Connexion à la BDD, fonctions utilitaires
├── import_file.py        ← Import des fichiers Excel (transactions, accords, conversions)
├── calculation_file.py   ← Calcul des revenus par accord et par palier
├── export_file.py        ← Export des résultats dans un fichier Excel
├── consultation_file.py  ← Requêtes SQL de lecture (pour l'interface)
└── dashboard_file.py     ← KPIs agrégés pour le tableau de bord
```

### Flux de données général

```
Fichiers Excel (client)
        │
        ▼
  import_file.py        → insère en base : transactions, produits, accords, conversions
        │
        ▼
 calculation_file.py    → lit la base, calcule les revenus, écrit les résultats en base
        │
        ▼
  export_file.py        → exporte un fichier Excel avec les résultats du calcul
        │
  consultation_file.py  → lecture des données pour l'affichage dans l'interface
  dashboard_file.py     → KPIs synthétiques pour le tableau de bord
```

---

## 2. `database_file.py`

> **Rôle :** Gérer la connexion à la base de données MySQL et fournir deux fonctions utilitaires (`get_or_create`, `get_or_create_many`) utilisées partout dans le projet.

### 2.1 Chargement de la configuration

```python
load_dotenv(Path(__file__).parent.parent / ".env.local", override=True)
_ENGINE = None
```

- `load_dotenv(...)` lit le fichier `.env.local` situé à la racine du projet (deux niveaux au-dessus de ce fichier).
- Les variables d'environnement (`DB_USER`, `DB_PASSWORD`, etc.) sont ainsi disponibles via `os.getenv(...)`.
- `_ENGINE = None` initialise la variable globale qui stockera l'engine SQLAlchemy. Elle est créée une seule fois (pattern Singleton).

---

### 2.2 `get_engine_method()`

```python
def get_engine_method():
    global _ENGINE
    if _ENGINE is None:
        user     = os.getenv("DB_USER", "root")
        password = os.getenv("DB_PASSWORD", "")
        host     = os.getenv("DB_HOST", "localhost")
        port     = os.getenv("DB_PORT", "3306")
        name     = os.getenv("DB_NAME", "rev_acc_database")
        _ENGINE = create_engine(
            f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}",
            pool_pre_ping=True,
            pool_recycle=3600,
        )
    return _ENGINE
```

**Ce que ça fait :**

1. La variable `_ENGINE` est globale : elle persiste entre les appels.
2. Si l'engine n'existe pas encore (`_ENGINE is None`), on lit les variables du `.env.local` pour construire l'URL de connexion.
3. `pool_pre_ping=True` : avant chaque réutilisation d'une connexion dormante, SQLAlchemy envoie un ping pour vérifier qu'elle est toujours active. Évite les erreurs "connexion perdue".
4. `pool_recycle=3600` : une connexion est recyclée toutes les heures pour éviter les timeouts MySQL.
5. L'engine est ensuite retourné et réutilisé lors des prochains appels (pas recréé).

---

### 2.3 `get_connection_method()` / `get_connection`

```python
def get_connection_method():
    return get_engine_method().connect()

get_connection = get_connection_method  # alias
```

**Ce que ça fait :** Ouvre une connexion active depuis l'engine. Tous les autres fichiers du projet font simplement `from core_folder.database_file import get_connection` et utilisent `with get_connection() as connection:` pour exécuter des requêtes SQL.

> **Pattern utilisé partout :**
> ```python
> with get_connection() as connection:
>     connection.execute(text("SELECT ..."))
>     connection.commit()
> ```
> Le `with` garantit que la connexion est correctement fermée même en cas d'erreur.

---

### 2.4 `get_or_create()`

```python
def get_or_create(param_connection, param_table: str, param_column_name: str, param_value: str | None) -> int | None:
```

**Ce que ça fait :** Cherche une valeur dans une table de référence. Si elle existe, retourne son ID. Si elle n'existe pas, crée la ligne et retourne le nouvel ID.

**Exemple concret :**
```python
# On veut l'ID du distributeur "Métro" dans la table `distributor`
id = get_or_create(connection, "distributor", "distributor_name", "Métro")
# → Si "Métro" existe déjà : retourne son id_distributor
# → Sinon : INSERT INTO distributor (distributor_name) VALUES ('Métro') et retourne le nouvel ID
```

**Étapes internes :**
1. Si `param_value` est `None`, retourne `None` immédiatement (pas d'insertion pour une valeur vide).
2. Construit dynamiquement le nom de la colonne PK (`id_{param_table}`).
3. Exécute un `SELECT` avec la valeur en paramètre (protégé contre l'injection SQL via `:value`).
4. Si une ligne est trouvée → retourne l'ID.
5. Sinon → `INSERT` et retourne `result.lastrowid` (ID auto-généré par MySQL).

---

### 2.5 `get_or_create_many()`

```python
def get_or_create_many(param_connection, param_table: str, param_column_name: str, param_values) -> dict:
```

**Ce que ça fait :** Version batch de `get_or_create`. Appelle `get_or_create` pour chaque valeur **unique** et **non vide** d'une liste, et retourne un dictionnaire `{valeur: id}`.

```python
# Exemple : créer tous les distributeurs d'un coup
mapping = get_or_create_many(connection, "distributor", "distributor_name", df["distributor"])
# → {"Métro": 1, "Sysco": 2, "Brake": 3}
```

- Les valeurs `None`, `""` et `"nan"` sont filtrées automatiquement.
- Les doublons sont éliminés via un `set()`.

---

## 3. `import_file.py`

> **Rôle :** Lire des fichiers Excel fournis par le client et peupler la base de données. Contient quatre fonctions indépendantes, appelées depuis l'interface graphique.

### Constantes globales

```python
BRAND_CORRECTION = {"Hellmanns": "Hellmann's"}
INDUSTRIAL_NAME  = "UNILEVER FOODSOLUTIONS"

RAW_COLUMN_MAP = {
    "DISTRIBUTEUR":   "distributor",
    "SOURCE DONNEES": "data_source",
    "CODE PRODUIT":   "product_code",
    ...
}

RAW_UNIT_MAP = {
    "BCL": "BOCAL",
    "BID": "BIDON",
    ...
}

DESCRIPTION_BRAND_KEYWORDS = [
    "AMORA", "HELLMANN'S", "KNORR", "MAILLE", "MAIZENA", "TABASCO", "LIPTON", "ELEPHANT"
]
```

- `BRAND_CORRECTION` : dictionnaire de corrections manuelles pour les noms de marques mal orthographiés dans les fichiers source.
- `RAW_COLUMN_MAP` : renomme les colonnes brutes du fichier Excel vers les noms internes Python.
- `RAW_UNIT_MAP` : normalise les abréviations d'unités (`BCL` → `BOCAL`, etc.).
- `DESCRIPTION_BRAND_KEYWORDS` : liste de mots-clés de marques utilisés pour détecter automatiquement la marque d'un produit depuis sa description.

---

### 3.1 `normalize_string_method()`

```python
def normalize_string_method(param_text: str) -> str:
```

**Ce que ça fait :** Normalise un texte pour le rendre comparable sans se soucier des accents, de la casse ou des espaces.

**Étapes :**
```python
text = unicodedata.normalize("NFKD", param_text)      # décompose les caractères accentués
text = text.encode("ASCII", "ignore").decode("utf-8") # supprime les accents (é → e)
text = text.replace("'", "")                          # supprime les apostrophes
text = re.sub(r"\s+", " ", text).strip()              # réduit les espaces multiples
text = text.upper()                                   # tout en majuscules
text = re.sub(r"(\d+)\s*(ML|L|KG|G)", r"\1\2", text)  # colle le chiffre à l'unité (500 ML → 500ML)
```

**Exemple :**
```
"Hellmann's  Squeeze 500 mL" → "HELLMANNS SQUEEZE 500ML"
```

---

### 3.2 `get_volume_category_method()`

```python
def get_volume_category_method(param_text: str) -> str:
```

**Ce que ça fait :** Extrait le volume d'une description produit et le classe dans une catégorie de taille.

Certaines marques (Tabasco, Maizena) ont des produits qui partagent la même description sauf le volume. Cette fonction permet de les distinguer.

**Logique :**

| Volume détecté | Catégorie retournée |
|---|---|
| `≤ 10 mL` | `"DOSETTE"` |
| `≤ 80 mL` | `"MINI"` |
| `≤ 200 mL` | `"150ML"` |
| `≤ 500 mL` | `"350ML"` |
| `> 500 mL` | `"GRANDFORMAT"` |
| `> 1 kg` | `"1KG"` |
| `≤ 500 g` | `"340G"` |
| `> 500 g` | `"700G"` |

**Exemple :**
```
"Tabasco 60ML"  → "MINI"
"Tabasco 150ML" → "150ML"
```

---

### 3.3 `find_product_name_method()`

```python
def find_product_name_method(param_row: pd.Series, param_mapping: pd.DataFrame) -> str | None:
```

**Ce que ça fait :** Attribue un `product_name` standardisé à un produit brut en le comparant aux règles de correspondance définies dans le fichier `mapping_product.xlsx`.

**Principe du keyword matching :**

Le fichier `mapping_product.xlsx` contient des lignes comme :
```
product_name     | keywords_brands         | keywords_others
"Knorr Fond brun"| "KNORR"                 | "FOND;BRUN;GLACE"
```

Pour chaque ligne du fichier Excel importé, la fonction :
1. Normalise la description et la marque du produit.
2. Pour certaines marques (Tabasco, Maizena), ajoute la catégorie de volume à la description normalisée pour affiner la comparaison.
3. Parcourt toutes les règles du mapping.
4. Filtre les règles dont `keywords_brands` ne correspond pas à la marque → on ignore ces règles.
5. Pour les règles retenues, compte combien de `keywords_others` sont présents dans la description.
6. Retourne le `product_name` de la règle avec le plus grand nombre de correspondances.

```python
# Si la description contient "FOND" et "BRUN" (2 mots-clés sur 3) → score = 2
# Si une autre règle correspond à 1 seul mot-clé → on garde la première
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
```

---

### 3.4 `parse_palier_column_name_method()`

```python
def parse_palier_column_name_method(param_column_name: str):
```

**Ce que ça fait :** Analyse le nom d'une colonne `palier_*` du fichier mapping pour en extraire le groupe, le volume minimum, le volume maximum et l'unité de l'accord (déduite du suffixe de la colonne).

**Formats reconnus :**

| Nom de colonne | Résultat retourné |
|---|---|
| `palier_X_25000-35000_uvc` | `('X', 25000, 34999, 'UVC')` |
| `palier_X_superior-40000_uvc` | `('X', 40000, None, 'UVC')` ← palier ouvert (pas de borne haute) |
| `palier_X_100-500_colis` | `('X', 100, 499, 'COLIS')` ← le suffixe fixe l'unité de l'accord |

> **Note :** Le `- 1` sur `max_volume` est intentionnel : la colonne Excel nomme la borne haute en exclu (`25000-35000` signifie jusqu'à 34 999 inclus).

---

### 3.5 `import_transactions()`

```python
def import_transactions(
    param_file_path: str,
    param_progress_callback=None,
    param_transaction_date: date | None = None,
    param_mapping_path: str | None = None,
) -> dict:
```

**Ce que ça fait :** Importe un fichier Excel de transactions brutes (`product_detail_export.xlsx`) dans la base de données.

**Pipeline complet en 5 étapes :**

---

#### Étape 1 — Lecture et normalisation des colonnes

```python
dataframe = pd.read_excel(param_file_path)
dataframe.dropna(how="all", inplace=True)            # supprime les lignes entièrement vides
dataframe = dataframe.rename(columns=RAW_COLUMN_MAP) # renomme les colonnes brutes
```

- Les lignes contenant "Filtres appliqués" (pied de page du fichier export) sont supprimées.
- La colonne de quantité est détectée dynamiquement (cherche une colonne contenant "Fac" ou "fac").
- Les unités sont normalisées : `"BCL"` → `"BOCAL"`, etc.
- Les codes produits sont corrigés : `"HELLEMANSQUEEZE"` → `"HELLMANN'S SQUEEZE"`.
- Les marques sont détectées automatiquement depuis la description si absentes.
- Toutes les colonnes texte passent en `Title Case` (première lettre majuscule par mot).
- Le `product_name` est attribué via `find_product_name_method()` (keyword matching).

---

#### Étape 2 — Alimentation des tables de référence

```python
with get_connection() as connection:
    get_or_create_many(connection, "distributor", "distributor_name", dataframe["distributor"])
    get_or_create_many(connection, "brand",       "brand_name",       dataframe["brand"])
    get_or_create_many(connection, "unit",        "unit_name",        dataframe["unit"])
    ...
```

- Pour chaque valeur unique trouvée dans le fichier (distributeurs, marques, unités, etc.), on s'assure qu'elle existe dans la table de référence correspondante. Si elle n'existe pas, elle est créée.
- Toutes les catégories du fichier mapping sont également créées, ainsi que la catégorie par défaut `"Non catégorisé"`.

---

#### Étape 3 — Chargement du catalogue et insertion des nouveaux produits

```python
existing_keys = set(zip(
    database_product["product_code"],
    database_product["description"],
    database_product["data_source"],
))
```

- La clé d'unicité d'un produit est le triplet `(product_code, description, data_source)`.
- Les produits du fichier qui n'existent pas encore en base sont insérés.
- La catégorie est déduite du `product_name` via le mapping (`product_name → category_name`).
- Si le `product_name` n'est pas résolu, la catégorie par défaut `"Non catégorisé"` est utilisée.
- Les produits déjà existants en base voient leur `product_name` et `fk_id_category` mis à jour (`UPDATE`) à partir du mapping courant — il n'y a jamais de suppression de produits.

> **Pourquoi mettre à jour les produits existants ?** Le mapping peut évoluer : un produit classé dans la mauvaise catégorie peut être corrigé en modifiant le fichier de mapping et en réimportant. La mise à jour ciblée garantit que la base reflète l'état courant du mapping.

---

#### Étape 4 — Résolution des clés étrangères

```python
# distributor → id_distributor
dataframe = dataframe.merge(database_distributor, ...)

# (product_code, description, data_source) → id_product
dataframe = dataframe.merge(database_product_deduplicate, ...)

# (fk_id_brand, fk_id_category) → id_agreement
dataframe = dataframe.merge(database_agreement, ...)
```

- On enrichit chaque ligne du DataFrame avec les IDs de la base (`id_product`, `id_distributor`, `id_agreement`).
- L'accord est résolu automatiquement via la paire `(marque, catégorie)` du produit.
- Le `unit_price` est calculé : `amount_ht / quantity`.

---

#### Étape 5 — Insertion des transactions

```python
with get_connection() as connection:
    connection.execute(text("TRUNCATE TABLE transaction"))  # vide complètement la table
    ...
    for _, row in dataframe.iterrows():
        connection.execute(insert_transaction_sql, {...})
```

- La table `transaction` est entièrement vidée avant chaque import (`TRUNCATE`). Elle est entièrement dérivée des fichiers source et peut être reconstruite à tout moment.
- Si `fk_id_product` ou `fk_id_distributor` est `None` (produit ou distributeur non résolu), la ligne est ignorée (`null_fk_count`).
- La fonction retourne un résumé `{"inserted": inserted, "null_fk": null_fk_count, "total": total}`.

---

### 3.6 `import_conversions()`

```python
def import_conversions(param_file_path: str, param_progress_callback=None) -> dict:
```

**Ce que ça fait :** Importe le fichier de correspondance (`table_correspondance.xlsx`) qui contient les **facteurs de conversion** entre les unités de transaction des distributeurs et les unités d'accord.

**Colonnes attendues dans le fichier :**

| Colonne Excel | Nom interne |
|---|---|
| `Distributeur` | `distributor_name` |
| `Code produit` | `product_code` |
| `Unité transaction (UF)` | `transaction_unit` |
| `Unité accord` | `agreement_unit` |
| `Facteur de conversion` | `conversion_factor` |

**Exemple de ligne :**
```
Métro | KNORR001 | BOÎTE | UVC | 12
→ 1 boîte Métro = 12 UVC (unités accord)
```

**Étapes :**
1. Lecture et validation du fichier (les colonnes manquantes lèvent une erreur claire).
2. La table `product_conversion` est entièrement vidée (`DELETE FROM product_conversion`).
3. Chaque ligne du fichier est ensuite insérée avec un simple `INSERT` (pas d'`ON DUPLICATE KEY UPDATE` — inutile puisque la table vient d'être vidée à l'étape précédente).

---

### 3.7 `import_agreements()`

```python
def import_agreements(param_file_path: str, param_progress_callback=None) -> dict:
```

**Ce que ça fait :** Importe les accords commerciaux depuis le fichier `mapping_product.xlsx`. Remplace entièrement les accords et paliers existants.

**Structure attendue du fichier mapping :**

```
brand    | categories    | palier_X_25000-35000_uvc | palier_X_superior-40000_uvc
Knorr    | Fond          | 0.15                     | 0.20
Knorr    | Sauce         | 0.12                     | 0.18
Hellmann's | Mayonnaise  | 0.10                     |
```

**Étapes :**

1. **Lecture et détection des colonnes `palier_*`** : toutes les colonnes dont le nom commence par `palier_` sont collectées.
2. **Détection du `palier_group`** : pour chaque ligne, on parse les colonnes `palier_*` pour extraire le nom du groupe (ex : `"X"` dans `palier_X_25000-35000_uvc`).
3. **Alimentation des tables de référence** : les marques, catégories et l'industriel `UNILEVER FOODSOLUTIONS` sont créés si absents. Les unités sont créées dynamiquement à partir du suffixe des colonnes `palier_*` de chaque groupe (ex : `_uvc` → `UVC`, `_colis` → `COLIS`) — `UVC` reste créée par défaut pour les accords sans `palier_group` détecté.

   > **Piège évité** : `id_industrial` et les ID d'unité sont récupérés directement depuis la valeur de retour de `get_or_create()` / `get_or_create_many()`, **pas** en relisant la table puis en filtrant en Python. La base utilise une collation insensible à la casse (`utf8mb4_general_ci`) : si `import_transactions()` a déjà inséré `"Unilever Foodsolutions"` (mis en forme via `.str.title()`), une comparaison de chaînes Python contre la constante `"UNILEVER FOODSOLUTIONS"` ne la retrouve pas alors que SQL, lui, la trouve. Utiliser directement le retour de `get_or_create` contourne le problème.
4. **Suppression de tous les accords existants** :
   ```python
   connection.execute(text("DELETE FROM agreement"))
   ```
   - Les paliers (`agreement_tier`) sont supprimés en cascade (contrainte `ON DELETE CASCADE`).
   - Les transactions pointant vers ces accords passent à `fk_id_agreement = NULL` (contrainte `ON DELETE SET NULL`).
5. **Insertion des nouveaux accords** : un accord par couple `(brand, category)` unique. `fk_id_unit` est déterminé par l'unité du `palier_group` de l'accord (`UVC` par défaut si aucun groupe n'est détecté).
6. **Insertion des paliers** : pour chaque accord, on parcourt les colonnes `palier_*` correspondant au même `palier_group` et on insère les lignes dans `agreement_tier`.

> **Après cet import**, il faut toujours appeler `resolve_agreements_method()` pour que les transactions qui sont passées à `NULL` retrouvent leur accord.

---

### 3.8 `resolve_agreements_method()`

```python
def resolve_agreements_method(param_progress_callback=None) -> None:
```

**Ce que ça fait :** Rerésout la clé `fk_id_agreement` sur toutes les transactions qui n'ont pas d'accord associé (`NULL`).

**Requête principale :**
```sql
UPDATE transaction
JOIN product ON product.id_product = transaction.fk_id_product
JOIN agreement ON agreement.fk_id_brand = product.fk_id_brand
    AND agreement.fk_id_category = product.fk_id_category
SET transaction.fk_id_agreement = agreement.id_agreement
WHERE transaction.fk_id_agreement IS NULL
    AND transaction.fk_id_product IS NOT NULL
```

- Relie chaque transaction à un accord via la paire `(marque, catégorie)` de son produit.

---

## 4. `calculation_file.py`

> **Rôle :** Calculer les revenus liés aux accords commerciaux, en appliquant un système de paliers sur les volumes agrégés.

### Principe métier

Un accord commercial définit des **paliers de volume** : selon la quantité totale vendue (sur tous les distributeurs confondus), un prix différent s'applique. Par exemple :

```
Palier "knorr" :
  - de 25 000 à 34 999 UVC → 0,15 €/UVC
  - de 35 000 à +∞ UVC     → 0,20 €/UVC
```

Le volume est calculé **par groupe de paliers** (`palier_group`) : si Knorr Fond et Knorr Sauce font partie du même groupe `"knorr"`, leurs volumes sont **additionnés** pour déterminer quel palier s'applique. Chaque distributeur a ensuite son propre revenu calculé sur son propre volume.

---

### 4.1 `run_calculation_method()`

```python
def run_calculation_method(param_progress_cb=None) -> tuple:
    # retourne (results_list, summary_dict)
```

**Pipeline en 6 étapes :**

---

#### Étape 1 — Chargement des données

```python
dataframe_transaction = pd.read_sql(text("""
    SELECT
        transaction.fk_id_distributor,
        transaction.fk_id_agreement,
        SUM(
            transaction.quantity * COALESCE(product_conversion.conversion_factor, 1)
        ) AS volume
    FROM transaction
    JOIN product ON product.id_product = transaction.fk_id_product
    JOIN distributor ON distributor.id_distributor = transaction.fk_id_distributor
    JOIN unit ON unit.id_unit = product.fk_id_unit
    LEFT JOIN product_conversion
        ON  product_conversion.distributor_name = distributor.distributor_name
        AND product_conversion.product_code     = product.product_code
        AND product_conversion.transaction_unit = unit.unit_name
    WHERE transaction.fk_id_agreement IS NOT NULL
    GROUP BY transaction.fk_id_distributor, transaction.fk_id_agreement
"""), connection)
```

- Calcule le **volume en UVC** par couple `(distributeur × accord)`.
- Le `COALESCE(conversion_factor, 1)` assure que si aucun facteur de conversion n'est renseigné, la quantité brute est utilisée telle quelle.
- Le `GROUP BY` agrège toutes les transactions d'un même distributeur pour un même accord en une seule ligne.
- Si aucune transaction n'a d'accord résolu → retour anticipé avec `total_revenue: 0`.

On charge également :
- `dataframe_agreement_clean` : nom du fournisseur, de la marque, de la catégorie et `palier_group` pour chaque accord.
- `dataframe_agreement_tiers` : tous les paliers (min, max, prix) pour tous les accords.
- `dataframe_distributors` : référentiel `id → nom` pour les distributeurs.

---

#### Étape 2 — Fusion des DataFrames

```python
dataframe = dataframe_transaction.merge(dataframe_agreement_clean, ...)
dataframe = dataframe.merge(dataframe_distributors, ...)
```

On enrichit chaque ligne `(distributeur × accord)` avec les infos descriptives (marque, catégorie, `palier_group`, nom du distributeur).

---

#### Étape 3 — Calcul du volume total par groupe

```python
group_totals = (
    dataframe[dataframe["palier_group"].notna()]
    .groupby("palier_group")["volume"]
    .sum()
    .rename("group_volume")
    .reset_index()
)
dataframe = dataframe.merge(group_totals, on="palier_group", how="left")
```

- Pour chaque `palier_group`, on **additionne les volumes de tous les accords de tous les distributeurs**.
- Cette colonne `group_volume` est celle qui détermine quel palier s'applique — pas le volume d'un seul distributeur.

---

#### Étape 4 — Remise à zéro des calculs précédents

```python
connection.execute(text("""
    UPDATE transaction
    SET fk_id_agreement_tier  = NULL,
        agreement_unit_price  = NULL,
        agreement_total_price = NULL
    WHERE fk_id_agreement IS NOT NULL
"""))
```

- Avant de recalculer, on remet à `NULL` les colonnes `agreement_*` pour ne pas conserver des résultats obsolètes d'une exécution précédente.

---

#### Étape 5 — Détermination du palier applicable et calcul du revenu

```python
tiers = sorted(
    tiers_by_agreement.get(agreement_id, []),
    key=lambda tier: int(tier["min_volume"]),
    reverse=True  # du plus élevé au plus bas
)

for tier in tiers:
    min_volume = int(tier["min_volume"])
    max_volume = int(tier["max_volume"]) if pd.notna(tier["max_volume"]) else None

    if group_volume >= min_volume and (max_volume is None or group_volume <= max_volume):
        applicable_tier = tier
        break
```

- On trie les paliers du plus haut au plus bas pour trouver le premier qui s'applique.
- Un palier s'applique si `group_volume >= min_volume` **et** (`max_volume` est absent **ou** `group_volume <= max_volume`).
- `max_volume is None` représente le palier ouvert ("40 000 et plus").
- Si aucun palier ne s'applique (volume trop faible), les colonnes restent à `NULL`.

Le palier atteint (`applicable_tier`) et son `tier_price` (prix/unité accord) sont désormais connus pour ce couple (distributeur × accord). Le revenu exact n'est **pas** calculé ici en Python — il est calculé directement en base, transaction par transaction, à l'étape suivante.

---

#### Étape 6 — Enregistrement en base et résumé

```python
UPDATE transaction
SET fk_id_agreement_tier  = :fk_id_agreement_tier,
    agreement_unit_price  = :agreement_unit_price,
    agreement_total_price = ROUND(
        :agreement_unit_price * transaction.quantity * COALESCE(product_conversion.conversion_factor, 1),
        2
    )
WHERE transaction.fk_id_agreement = :fk_id_agreement
  AND transaction.fk_id_distributor = :fk_id_distributor
```

- `agreement_total_price` est calculé directement en SQL pour chaque transaction individuelle (pas seulement par agrégat distributeur × accord) — c'est cette valeur, arrondie à 2 décimales par transaction (`DECIMAL(10,2)`), qui fait foi.
- Le résumé final est calculé depuis la base en sommant `agreement_total_price` par `palier_group`.

**Relecture du revenu réel pour le detail affiché :**

```python
dataframe_actual_revenue = pd.read_sql(text("""
    SELECT fk_id_agreement, fk_id_distributor, SUM(agreement_total_price) AS revenue
    FROM transaction
    WHERE agreement_total_price IS NOT NULL
    GROUP BY fk_id_agreement, fk_id_distributor
"""), connection)
```

- Une fois l'`UPDATE` exécuté, le revenu affiché dans `results[i]["detail"]` (pour les accords ayant atteint un palier) n'est pas recalculé en Python (`volume_accord x tier_price`) — il est **relu depuis la base**, en sommant les `agreement_total_price` réellement stockés pour ce couple `(fk_id_agreement, fk_id_distributor)`.
- Cela garantit que le détail affiché à l'écran/Excel correspond **exactement, au centime près**, au total utilisé dans `summary["total_revenue"]` — les deux proviennent de la même source (`agreement_total_price` en base), au lieu d'un calcul agrégé fait séparément qui pourrait diverger de quelques centimes à cause des arrondis par transaction.

**Valeur retournée :**
```python
return results, {
    "total_revenue":    1234.56,
    "agreements":       12,
    "transactions":     850,
    "revenue_by_group": {"knorr": 800.0, "dressing": 434.56}
}
```

---

## 5. `export_file.py`

> **Rôle :** Exporter les résultats du calcul dans un fichier Excel avec deux feuilles.

### 5.1 `export_calculation_method()`

```python
def export_calculation_method(param_file_path: str, param_results: list, param_summary: dict) -> None:
```

**Ce que ça fait :** Génère un fichier Excel à `param_file_path` avec deux feuilles :

**Feuille "Résumé" :**
- Un tableau avec : Distributeur, Fournisseur, Marque, Catégorie, Total volume, Taux accord, Détail du calcul.
- Deux lignes plus bas : un second tableau avec le revenu par groupe d'accords et le total global.

```python
start_row_totaux = len(dataframe_resume) + 2
dataframe_totaux.to_excel(writer, sheet_name="Résumé", index=False, startrow=start_row_totaux)
```

**Feuille "Transactions" :**
- Toutes les transactions de la base avec : nom produit, description, marque, catégorie, distributeur, fournisseur, quantité, prix unitaire, prix total, unité de transaction, date, taux accord, unité accord, statut mapping.

```python
CASE
    WHEN transaction.fk_id_agreement IS NULL THEN 'Sans accord'
    ELSE 'OK'
END AS mapping_status
```
- Une transaction sans accord est marquée `'Sans accord'` (le produit n'a pas été résolu par le mapping).

- La colonne **"Unité accord"** vient de `product_conversion.agreement_unit`, retrouvé via un `LEFT JOIN` sur la clé métier `(distributor_name, product_code, transaction_unit)` — la même clé que celle utilisée dans `calculation_file.py` pour le facteur de conversion :
  ```sql
  LEFT JOIN product_conversion
      ON  product_conversion.distributor_name = distributor.distributor_name
      AND product_conversion.product_code     = product.product_code
      AND product_conversion.transaction_unit = unit.unit_name
  ```
  Colonne informative, sans influence sur le calcul : saisie manuelle du client dans `table_correspondance.xlsx`. Même statut pour `agreement.fk_id_unit`, utilisé uniquement pour l'affichage dans l'onglet "Accords" (`consultation_file.py`). Sans correspondance dans `product_conversion`, la valeur affichée est `"—"`.

**Formatage du taux accord et de l'unité accord :**
```python
def _format_taux(row):
    """ Formatage du taux d'accord pour l'affichage dans le fichier Excel """

    if pd.isna(row["agreement_unit_price"]):
        return "—"

    return f"{float(row['agreement_unit_price']):.2f}"

# -----

dataframe_transactions["Unité accord"] = dataframe_transactions["agreement_unit"].fillna("—")
```

---

## 6. `consultation_file.py`

> **Rôle :** Fournir des fonctions de lecture SQL pour alimenter les onglets de consultation dans l'interface graphique. Chaque fonction retourne une liste de listes, directement utilisable pour remplir un tableau.

### Fonctions disponibles

| Fonction | Onglet alimenté | Données retournées |
|---|---|---|
| `load_consultation_products_method()` | Produits | Nom, marque-catégorie, unité, statut |
| `load_consultation_agreements_method()` | Accords | Industriel, produit, taux (paliers) |
| `load_all_transactions_method()` | Transactions | Date, distributeur, produit, qté, prix |
| `load_all_product_conversions_method()` | Correspondances | Distributeur, code, unité tx, unité accord, facteur |
| `load_all_brands_method()` | Listes déroulantes | Noms de marques |
| `load_all_categories_method()` | Listes déroulantes | Noms de catégories |
| `load_all_distributors_method()` | Listes déroulantes | Noms de distributeurs |
| `load_all_industrials_method()` | Listes déroulantes | Noms d'industriels |
| `load_all_units_method()` | Listes déroulantes | Noms d'unités |

### Détail : `load_consultation_products_method()`

```sql
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
...
GROUP BY product.id_product
ORDER BY status, product.product_name
```

Le statut d'un produit est calculé directement en SQL :
- `'Sans transaction'` → le produit existe dans le catalogue mais n'a aucune transaction.
- `'À corriger'` → au moins une transaction du produit n'a pas d'accord résolu.
- `'OK'` → toutes les transactions du produit ont un accord.

### Détail : `load_consultation_agreements_method()`

```sql
GROUP_CONCAT(
    CONCAT(
        agreement_tier.min_volume, ' - ',
        COALESCE(agreement_tier.max_volume, '+∞'), ' ', unit.unit_name, ' : ',
        agreement_tier.price, ' €/', unit.unit_name
    )
    ORDER BY agreement_tier.min_volume SEPARATOR ' | '
) AS taux
```

- `GROUP_CONCAT` agrège tous les paliers d'un accord en une seule chaîne lisible.
- Exemple de résultat : `"25000 - 34999 UVC : 0.15 €/UVC | 35000 - +∞ UVC : 0.20 €/UVC"`.

---

## 7. `dashboard_file.py`

> **Rôle :** Calculer les indicateurs clés (KPIs) affichés sur le tableau de bord de l'application.

### 7.1 `load_dashboard_kpis_method()`

```python
def load_dashboard_kpis_method() -> dict:
```

**Ce que ça fait :** Exécute plusieurs requêtes `COUNT` simples et retourne un dictionnaire de KPIs.

**KPIs retournés :**

| Clé | Description |
|---|---|
| `"accords"` | Nombre d'accords enregistrés dans la table `agreement` |
| `"products"` | Nombre de produits dans le catalogue |
| `"product_to_be_verified"` | Transactions dont `fk_id_product` est `NULL` |
| `"agreement_to_be_verified"` | Transactions dont `fk_id_agreement` est `NULL` (sans accord) |
| `"distributor_to_be_verified"` | Transactions dont `fk_id_distributor` est `NULL` |

```python
# Exemple d'utilisation dans l'interface
kpis = load_dashboard_kpis_method()
print(kpis["agreement_to_be_verified"])  # → 42 (transactions sans accord)
```

- `.scalar()` retourne directement la première valeur de la première ligne (idéal pour un `COUNT(*)`).
- Le `or 0` à la fin protège contre un retour `None` si la table est vide.

---

## Annexe — Dépendances entre les fichiers

```
database_file.py
    ↑ importé par tous les autres fichiers

import_file.py
    → utilise : database_file (get_connection, get_or_create, get_or_create_many)
    → appelle : normalize_string_method, find_product_name_method, parse_palier_column_name_method

calculation_file.py
    → utilise : database_file (get_connection)

export_file.py
    → utilise : database_file (get_connection)

consultation_file.py
    → utilise : database_file (get_connection)

dashboard_file.py
    → utilise : database_file (get_connection)
```

---

## Annexe — Ordre d'appel recommandé pour un premier import

```
1. import_conversions()        ← table_correspondance.xlsx (facteurs de conversion)
2. import_agreements()         ← mapping_product.xlsx (accords + paliers)
3. import_transactions()       ← product_detail_export.xlsx (transactions brutes)
                                  résout fk_id_agreement via (fk_id_brand, fk_id_category)
                                  — nécessite que les accords existent déjà en base
4. resolve_agreements_method() ← relie les transactions qui seraient passées à NULL
                                  (cas d'une réimportation d'accords après les transactions)
5. run_calculation_method()    ← calcule les revenus
6. export_calculation_method() ← exporte les résultats dans un Excel
```

> **Important :** `import_agreements()` doit impérativement précéder `import_transactions()`. La résolution de `fk_id_agreement` se fait à l'étape 4 de `import_transactions()` via la paire `(fk_id_brand, fk_id_category)` du produit — si la table `agreement` est vide à ce moment-là, toutes les transactions sont insérées avec `fk_id_agreement = NULL`. `resolve_agreements_method()` reste utile si les accords sont réimportés (et donc supprimés puis recréés) après que des transactions existent déjà en base.
