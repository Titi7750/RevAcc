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

def run_calculation_method(param_progress_cb=None) -> tuple:
    """
    Calcule des revenus des accords

    Logique :
    1. Calculer le volume par (distributeur x accord) :
        volume = quantity x conversion_factor (depuis la table product_conversion, renseigné par le client)
    2. Sommer le volume de tous les accords du même palier_group, tous distributeurs confondus
        → Volume total du groupe (commun à tous les distributeurs)
    3. Déterminer le palier applicable depuis le volume total du groupe
    4. Revenu par accord = volume_accord x prix_palier (€/UVC)
    5. Mettre à jour fk_id_agreement_tier, agreement_unit_price, agreement_total_price dans la table transaction

    Si un distributeur n'atteint aucun seuil pour un groupe, les colonnes agreement
    restent NULL (aucune écriture)

    Retourne (results_list, summary_dict)
    """

    # -----

    def _progression_bar(param_percentage: int, param_message: str):
        """ Met à jour la barre de progression """

        if param_progress_cb:
            param_progress_cb(param_percentage, param_message)

    # -----

    # ── Étape 1 : Chargement des données ─────────────────────────────────────
    _progression_bar(0, "Chargement des transactions…")

    with get_connection() as connection:
        # Charge le volume par (distributeur x accord) depuis la base
        # Le facteur de conversion provient de product_conversion (renseigné par le client)
        # COALESCE(conversion_factor, 1) sécurise le cas où la correspondance est absente
        # Le GROUP BY agrège toutes les transactions d'un même distributeur pour un
        # même accord en une seule ligne — c'est l'unité de travail du calcul
        dataframe_transaction = pd.read_sql(
            text("""
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
            """),
            connection
        )

        # Sortie anticipée si aucune transaction n'a d'accord résolu en base
        # Cas possible si le Bouton (Importer accords) n'a jamais été lancé
        if dataframe_transaction.empty:
            return [], {"total_revenue": 0.0, "agreements": 0, "transactions": 0}

        _progression_bar(20, "Chargement des accords…")

        # Charge les informations descriptives de chaque accord (fournisseur, marque,
        # catégorie, palier_group). Utilisé pour enrichir les résultats affichés
        # et pour construire la colonne palier_group qui sert à regrouper les UVC
        dataframe_agreement_clean = pd.read_sql(
            text("""
                SELECT
                    agreement.id_agreement,
                    industrial.industrial_name,
                    brand.brand_name,
                    category.category_name,
                    agreement.palier_group
                FROM agreement
                JOIN industrial ON industrial.id_industrial = agreement.fk_id_industrial
                JOIN brand      ON brand.id_brand           = agreement.fk_id_brand
                JOIN category   ON category.id_category     = agreement.fk_id_category
            """),
            connection
        )

        _progression_bar(35, "Chargement des paliers…")

        # Charge tous les paliers de tous les accords. Chaque accord a 3 lignes :
        # une par tranche de volume (min_volume, max_volume, price). C'est dans cette table
        # qu'on va chercher le prix applicable une fois le palier déterminé
        dataframe_agreement_tiers = pd.read_sql(
            text("""
                SELECT id_agreement_tier, fk_id_agreement, min_volume, max_volume, price
                FROM agreement_tier
                ORDER BY fk_id_agreement, min_volume
            """),
            connection
        )

        # Charge le référentiel distributeurs pour résoudre les noms à afficher
        # dans les résultats (id_distributor → distributor_name)
        dataframe_distributors = pd.read_sql(
            text("SELECT id_distributor, distributor_name FROM distributor"),
            connection
        )

        _progression_bar(45, "Comptage des transactions…")

        # Comptage simple pour alimenter le résumé final (summary["transactions"])
        # Ne filtre que les transactions avec accord résolu — les 13 non matchés sont exclus
        transaction_count = connection.execute(
            text("SELECT COUNT(*) FROM transaction WHERE fk_id_agreement IS NOT NULL")
        ).scalar() or 0

    # ── Étape 2 : Enrichissement et agrégation ────────────────────────────────
    _progression_bar(50, "Calcul des revenus par groupe de palier…")

    # Jointure pour ajouter les informations descriptives de l'accord (marque, catégorie,
    # palier_group...) à chaque ligne (distributeur x accord)
    dataframe = dataframe_transaction.merge(
        dataframe_agreement_clean,
        left_on="fk_id_agreement",
        right_on="id_agreement",
        how="left"
    )

    # Jointure pour ajouter le nom du distributeur
    dataframe = dataframe.merge(
        dataframe_distributors,
        left_on="fk_id_distributor",
        right_on="id_distributor",
        how="left"
    )

    # Volume total par palier_group — global tous distributeurs confondus
    # C'est ce total qui détermine le palier atteint; il s'applique ensuite
    # à chaque (distributeur x accord) pour calculer son propre revenu
    group_totals = (
        dataframe[dataframe["palier_group"].notna()] # Ignore les accords sans palier_group
        .groupby("palier_group")["volume"] # Sommer tout le volume du groupe, tous distributeurs confondus
        .sum() # Sommer le volume pour chaque groupe
        .rename("group_volume") # Renommer la colonne
        .reset_index() # Remettre les colonnes de groupement comme colonnes normales
    )

    dataframe = dataframe.merge(
        group_totals,
        on="palier_group",
        how="left"
    )

    # Construit un dictionnaire d'accès rapide aux paliers : {id_agreement: [liste de paliers]}
    # Évite de refiltrer le DataFrame à chaque itération de la boucle principale —
    # un simple .get(agreement_id) - ligne 226 suffit pour récupérer les 3 paliers d'un accord
    tiers_by_agreement: dict = {}
    for _, tier_row in dataframe_agreement_tiers.iterrows():
        foreign_key = int(tier_row["fk_id_agreement"])
        tiers_by_agreement.setdefault(foreign_key, []).append(tier_row)

    # ── Étape 3 : Résolution du palier et calcul du revenu ───────────────────

    # Reset préalable : remet à NULL toutes les colonnes agreement_* pour éviter
    # de conserver des valeurs obsolètes d'un run précédent
    with get_connection() as connection:
        connection.execute(text("""
            UPDATE transaction
            SET fk_id_agreement_tier  = NULL,
                agreement_unit_price  = NULL,
                agreement_total_price = NULL
            WHERE fk_id_agreement IS NOT NULL
        """))
        connection.commit()

    # results : liste des résultats à retourner à l'interface pour affichage
    # transactions_to_update : liste des mises à jour à appliquer en base (étape 4)
    results:             list = []
    transactions_to_update: list = []
    total = len(dataframe)

    for index, (_, row) in enumerate(dataframe.iterrows()):
        _progression_bar(50 + int(35 * index / max(total, 1)), f"Accord {index + 1}/{total}…")

        # Extraction des valeurs la ligne par ligne
        # Les str() et or "N/A" protègent contre les valeurs NULL
        # comme NaN depuis pandas, ce qui provoquerait des erreurs à l'affichage
        agreement_id   = int(row["fk_id_agreement"])
        distributor_id = int(row["fk_id_distributor"])
        volume_accord     = int(row["volume"])
        industrial     = str(row.get("industrial_name") or "N/A")
        brand          = str(row.get("brand_name")      or "N/A")
        category       = str(row.get("category_name")   or "N/A")
        distributor    = str(row.get("distributor_name") or "N/A")
        palier_group   = str(row.get("palier_group")     or "—")

        # group_volume est le volume total du palier_group (tous accords + tous distributeurs confondus)
        # Si l'accord n'a pas de palier_group (ex : produit hors accord comme Lipton),
        # on utilise le volume de l'accord seul comme fallback — il n'atteindra jamais
        # de palier, mais ça évite une erreur et produit un message "Aucun palier applicable"
        group_volume_raw = row.get("group_volume")
        group_volume     = int(group_volume_raw) if pd.notna(group_volume_raw) else volume_accord

        # Récupère les paliers de cet accord et les trie du plus élevé au plus bas
        tiers = sorted(
            tiers_by_agreement.get(agreement_id, []),
            key=lambda tier: int(tier["min_volume"]),
            reverse=True
        )

        # On teste d'abord le palier le plus haut : dès qu'on trouve un intervalle
        # [min_volume, max_volume] qui contient group_volume, c'est le palier applicable
        applicable_tier = None
        for tier in tiers:
            min_volume = int(tier["min_volume"])
            max_volume = int(tier["max_volume"]) if pd.notna(tier["max_volume"]) else None

            # group_volume >= min_volume → la quantité atteint le seuil bas du palier
            # max_volume is None      → le palier est ouvert ("40 000 et plus") : pas de borne haute
            # group_volume <= max_volume → la quantité ne dépasse pas la borne haute
            if group_volume >= min_volume and (max_volume is None or group_volume <= max_volume):
                applicable_tier = tier
                break

        # Palier trouvé → préparation de la mise à jour en base et construction du détail.
        # revenue est calculé uniquement pour alimenter la chaîne detail (affichage).
        # Chaque distributeur a son propre volume, mais tous partagent le même palier
        # (déterminé par le group_volume global, tous distributeurs confondus).
        if applicable_tier is not None:
            tier_id    = int(applicable_tier["id_agreement_tier"])
            tier_price = float(applicable_tier["price"])
            min_palier   = int(applicable_tier["min_volume"])
            max_palier   = (
                f"{int(applicable_tier["max_volume"]):,}"
                if pd.notna(applicable_tier["max_volume"])
                else "+∞"
            )
            revenue  = volume_accord * tier_price
            tier_str = f"{tier_price:.2f} €/unité accord"
            detail   = (
                f"{volume_accord:,} unités x {tier_price:.2f} €/UVC "
                f"= {revenue:,.2f} €  "
                f"(palier {min_palier:,}-{max_palier} unités, total groupe {group_volume:,}unités)"
            )

            # Empile les paramètres nécessaires à l'UPDATE de la table transaction.
            # On stocke l'accord + le distributeur pour cibler exactement les bonnes lignes,
            # et le tier_id + tier_price pour remplir les 3 colonnes agreement_*.
            transactions_to_update.append({
                "fk_id_agreement":      agreement_id,
                "fk_id_distributor":    distributor_id,
                "fk_id_agreement_tier": tier_id,
                "agreement_unit_price": tier_price,
            })
        else:
            tier_id    = None
            tier_price = 0.0
            tier_str   = "Aucun palier"
            detail     = f"Aucun palier applicable (total groupe {group_volume:,}unités)"

        # Empile le résultat de cette ligne pour l'affichage dans l'interface.
        # Chaque entrée correspond à un accord pour un distributeur donné.
        results.append({
            "id_agreement": agreement_id,
            "distributor":  distributor,
            "industrial":   industrial,
            "brand":        brand,
            "category":     category,
            "palier_group": palier_group,
            "total_volume":    volume_accord,
            "group_volume":    group_volume,
            "tier_price":   tier_str,
            "detail":       detail,
        })

    # ── Étape 4 : Mise à jour des colonnes agreement dans transaction ─────────
    _progression_bar(85, "Mise à jour des transactions…")

    if transactions_to_update:
        # Met à jour en base les 3 colonnes agreement_* ayant atteint un palier
        # agreement_total_price = agreement_unit_price x volume de la transaction
        # Le facteur de conversion provient de product_conversion
        # COALESCE(conversion_factor, 1) sécurise le cas où la correspondance est absente
        update_sql = text("""
            UPDATE transaction
            JOIN product ON product.id_product = transaction.fk_id_product
            JOIN distributor ON distributor.id_distributor = transaction.fk_id_distributor
            JOIN unit ON unit.id_unit = product.fk_id_unit
            LEFT JOIN product_conversion
                ON  product_conversion.distributor_name = distributor.distributor_name
                AND product_conversion.product_code     = product.product_code
                AND product_conversion.transaction_unit = unit.unit_name
            SET transaction.fk_id_agreement_tier  = :fk_id_agreement_tier,
                transaction.agreement_unit_price  = :agreement_unit_price,
                transaction.agreement_total_price = ROUND(
                    :agreement_unit_price * transaction.quantity * COALESCE(product_conversion.conversion_factor, 1),
                    2
                )
            WHERE transaction.fk_id_agreement = :fk_id_agreement
                AND transaction.fk_id_distributor = :fk_id_distributor
        """)

        with get_connection() as connection:
            for update_transaction in transactions_to_update:
                connection.execute(update_sql, update_transaction)

            connection.commit()

    _progression_bar(100, "Calcul terminé.")

    # Totaux par palier_group depuis agreement_total_price en base
    # total_revenue = somme de tous les groupes
    # revenue_by_group = détail par groupe pour affichage séparé dans l'interface
    with get_connection() as connection:
        dataframe_revenue_by_group = pd.read_sql(
            text("""
                SELECT
                    agreement.palier_group,
                    SUM(transaction.agreement_total_price) AS total_revenue
                FROM transaction
                JOIN agreement ON agreement.id_agreement = transaction.fk_id_agreement
                WHERE transaction.agreement_total_price IS NOT NULL
                    AND agreement.palier_group IS NOT NULL
                GROUP BY agreement.palier_group
            """),
            connection
        )

    revenue_by_group = {
        str(row["palier_group"]): round(float(row["total_revenue"]), 2)
        for _, row in dataframe_revenue_by_group.iterrows()
    }

    summary = {
        "total_revenue":    round(sum(revenue_by_group.values()), 2),
        "agreements":       len(results),
        "transactions":     int(transaction_count),
        "revenue_by_group": revenue_by_group,
    }

    return results, summary
