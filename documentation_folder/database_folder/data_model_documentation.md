# Data Model — `rev_acc_database`

## Vue d'ensemble

Ce modèle de données gère les **accords de reversement** négociés entre industriels et **Entegra**, par marque et catégorie, avec un système de paliers basés sur les volumes (UVC, colis, KG, etc. selon l'accord).

### Chaîne commerciale

```
Industriel → (accord de reversement) → Entegra → (négociation) → Distributeur → (vente) → Client final
```

### Schéma des relations

```
brand ──────────────────────────────┬──▶ product
unit ───────────────────────────────┤
data_source ────────────────────────┤
category ───────────────────────────┘

brand ──────────────────────────────┬──▶ agreement ──▶ agreement_tier
category ───────────────────────────┤                        │
unit ───────────────────────────────┤                        │
industrial ─────────────────────────┘                        │
                                                             │
product ─────────────────────────────┬──▶ transaction ◀─────┘
agreement ───────────────────────────┤
distributor ─────────────────────────┘

product_conversion
```

---

## Conventions

| Élément | Convention |
|---|---|
| Clés primaires | `id_<table>` |
| Clés étrangères | `fk_id_<table_cible>` |
| Suppressions | `ON DELETE CASCADE` sur toutes les FK |
| Encodage | `utf8mb4` / `utf8mb4_general_ci` |
| Moteur | `InnoDB` (support des FK et transactions ACID) |

---

## Tables

### `brand`
Référentiel des marques (ex : Amora, Knorr, Tabasco).

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id_brand` | INT | PK, AUTO_INCREMENT | Identifiant unique |
| `brand_name` | VARCHAR(255) | NOT NULL | Nom de la marque |

---

### `category`
Référentiel des catégories produit (ex : Sauces Salades 5L, Tabasco Mini).

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id_category` | INT | PK, AUTO_INCREMENT | Identifiant unique |
| `category_name` | VARCHAR(255) | NOT NULL | Nom de la catégorie |

---

### `data_source`
Référentiel des sources de données (ex : Déclaratif Distributeur Cadhi, Déclaratif Distributeur Entegra Ami2).

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id_data_source` | INT | PK, AUTO_INCREMENT | Identifiant unique |
| `data_source_name` | VARCHAR(255) | NOT NULL | Nom de la source de données |

---

### `distributor`
Référentiel des distributeurs (ex : Back Europe, France Frais, Pomona Episaveurs). Les distributeurs sont les clients d'Entegra — ils n'interviennent pas dans la négociation des accords, uniquement dans les transactions.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id_distributor` | INT | PK, AUTO_INCREMENT | Identifiant unique |
| `distributor_name` | VARCHAR(255) | NOT NULL | Nom du distributeur |

---

### `industrial`
Référentiel des industriels / fournisseurs (ex : Unilever FoodSolutions).

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id_industrial` | INT | PK, AUTO_INCREMENT | Identifiant unique |
| `industrial_name` | VARCHAR(255) | NOT NULL | Nom de l'industriel |

---

### `unit`
Référentiel des unités de vente (ex : Kg, Seau, Bouteille).

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id_unit` | INT | PK, AUTO_INCREMENT | Identifiant unique |
| `unit_name` | VARCHAR(255) | NOT NULL | Nom de l'unité |

---

### `product`
Produits commercialisés, rattachés à une marque, une catégorie et une source de données.

> **Choix de conception** : `product` n'est pas lié à un distributeur ou un industriel spécifique. Un même produit peut être vendu dans le cadre de plusieurs accords différents. Ces liens sont portés par `transaction` et `agreement`. La colonne `fk_id_data_source` trace l'origine du référentiel produit (système déclaratif source).

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id_product` | INT | PK, AUTO_INCREMENT | Identifiant unique |
| `fk_id_brand` | INT | FK → `brand`, NOT NULL | Marque du produit |
| `fk_id_category` | INT | FK → `category`, NOT NULL | Catégorie du produit |
| `fk_id_unit` | INT | FK → `unit`, NOT NULL | Unité de vente |
| `fk_id_data_source` | INT | FK → `data_source`, NOT NULL | Source du référentiel produit |
| `product_name` | VARCHAR(255) | NULL | Nom du produit (peut être absent si non mappé) |
| `product_code` | VARCHAR(255) | NULL | Code du produit |
| `description` | TEXT | NULL | Description libre |
| `product_date` | DATE | NULL | Date associée au produit |

---

### `product_conversion`
Table de correspondance entre l'unité de transaction (UF) et l'unité de l'accord, par distributeur et code produit. Renseignée manuellement par le client à partir du fichier `table_correspondance.xlsx`.

> **Choix de conception** : le facteur de conversion absorbe toute la logique de conversion quelle que soit l'unité de l'accord (UVC, colis, KG, etc.). `product_name` n'est pas stocké ici — `product_code` suffit à faire le lien avec la table `product`. La clé d'unicité porte sur `(distributor_name, product_code, transaction_unit)` : un même produit peut avoir des conditionnements différents selon le distributeur.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id_conversion` | INT | PK, AUTO_INCREMENT | Identifiant unique |
| `distributor_name` | VARCHAR(255) | NOT NULL | Nom du distributeur |
| `product_code` | VARCHAR(255) | NOT NULL | Code du produit |
| `transaction_unit` | VARCHAR(50) | NOT NULL | Unité de transaction (UF) — ex : UNITÉ, SEAU, KG |
| `agreement_unit` | VARCHAR(50) | NOT NULL, DEFAULT 'UVC' | Unité dans laquelle l'accord est exprimé — ex : UVC, Colis, KG |
| `conversion_factor` | DECIMAL(10,4) | NOT NULL, DEFAULT 1 | Nombre d'unités accord par unité de transaction — ex : 1 colis = 40 UVC → facteur = 40 |

---

### `agreement`
> **Choix de conception** : Entegra étant toujours le signataire, elle n'est pas stockée comme FK — ce serait une valeur constante sans intérêt analytique. Un accord est la table de jonction implicite entre `brand`, `category` et `industrial`. Le champ `palier_group` permet de regrouper plusieurs accords (marques/catégories différentes) sous un même compteur de volume pour le calcul du palier — par exemple, tous les accords Knorr partagent le même `palier_group` et leurs volumes sont additionnés pour déterminer le palier commun.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id_agreement` | INT | PK, AUTO_INCREMENT | Identifiant unique |
| `fk_id_brand` | INT | FK → `brand`, NOT NULL | Marque concernée |
| `fk_id_category` | INT | FK → `category`, NOT NULL | Catégorie concernée |
| `fk_id_industrial` | INT | FK → `industrial`, NOT NULL | Industriel signataire |
| `fk_id_unit` | INT | FK → `unit`, NOT NULL | Unité dans laquelle les paliers sont exprimés |
| `palier_group` | VARCHAR(255) | NULL | Groupe de palier partagé entre plusieurs accords (ex : `knorr`, `dressing+maizena+tvb`) |
| `start_date` | DATE | NULL | Date de début de l'accord |
| `end_date` | DATE | NULL | Date de fin de l'accord |

---

### `agreement_tier`
Paliers de reversement d'un accord. Chaque ligne définit une tranche de volume et le prix de reversement associé. Le volume est exprimé dans l'unité définie par `agreement.fk_id_unit`.

> **Choix de conception** : Les paliers sont dans une table dédiée plutôt qu'en colonnes fixes afin de supporter un nombre variable de paliers par accord. Le dernier palier d'un accord a `max_volume = NULL` (pas de plafond).

**Exemple** pour un accord Amora / Sauces Salades 5L (unité : UVC) :

| `min_volume` | `max_volume` | `price` |
|---|---|---|
| 25 000 | 35 000 | 1,20 € |
| 35 000 | 40 000 | 1,30 € |
| 40 000 | NULL | 1,50 € |

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id_agreement_tier` | INT | PK, AUTO_INCREMENT | Identifiant unique |
| `fk_id_agreement` | INT | FK → `agreement`, NOT NULL | Accord parent |
| `min_volume` | INT | NOT NULL | Borne inférieure du palier (incluse) |
| `max_volume` | INT | NULL | Borne supérieure du palier (NULL = pas de plafond) |
| `price` | DECIMAL(10,2) | NOT NULL | Prix de reversement pour ce palier (€) |

---

### `transaction`
Vente effective d'un produit, dans le cadre d'un accord commercial.

> **Choix de conception** :
> - `fk_id_agreement` permet de remonter à l'accord applicable au moment de la vente.
> - `fk_id_agreement_tier` identifie le palier précis qui a été atteint lors du calcul.
> - `fk_id_distributor` identifie quel est le distributeur.
> - `unit_price` et `total_price` sont les prix de vente réel au moment de la transaction. Ils ne doivent pas être recalculés dynamiquement.
> - `agreement_unit_price` et `agreement_total_price` sont les colonnes de reversement, renseignées par le Bouton de calcul. Elles restent `NULL` jusqu'au lancement du calcul. `agreement_total_price` est la source utilisée pour les totaux de revenu.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id_transaction` | INT | PK, AUTO_INCREMENT | Identifiant unique |
| `fk_id_product` | INT | FK → `product`, NULL | Produit vendu |
| `fk_id_agreement` | INT | FK → `agreement`, NULL | Accord applicable (NULL si produit non mappé) |
| `fk_id_agreement_tier` | INT | FK → `agreement_tier`, NULL | Palier atteint lors du calcul (NULL avant calcul) |
| `fk_id_distributor` | INT | FK → `distributor`, NULL | Distributeur |
| `quantity` | INT | NOT NULL | Quantité vendue en colis |
| `unit_price` | DECIMAL(10,2) | NOT NULL | Prix unitaire au moment de la vente |
| `agreement_unit_price` | DECIMAL(10,2) | NULL | Prix du palier de reversement (€/unité accord) — renseigné par le calcul |
| `total_price` | DECIMAL(10,2) | NOT NULL | Montant total de vente |
| `agreement_total_price` | DECIMAL(10,2) | NULL | Revenu de reversement = volume × agreement_unit_price — renseigné par le calcul |
| `transaction_date` | DATE | NULL | Date de la transaction |

---

## Screenshot du Modèle Physique des Données dans DBeaver

![MPD database rev_acc_database](database_rev_acc_database.png)
