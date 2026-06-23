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
    1. Calculer les UVC par (distributeur x accord) :
        - is_billed_per_case = 0 → uvc = quantity x units_per_case
        - is_billed_per_case = 1 → uvc = quantity  (ex : Amora - Dosette, compté en colis)
    2. Sommer les UVC de tous les accords du même palier_group, tous distributeurs confondus
        → UVC totale du groupe (commune à tous les distributeurs)
    3. Déterminer le palier applicable depuis l'UVC totale du groupe
    4. Revenu par accord = uvc_accord x prix_palier (€/UVC)
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
        # Charge les UVC par (distributeur x accord) depuis la base
        # Le CASE WHEN gère l'exception Amora Dosette (is_billed_per_case = 1) :
        # pour cette catégorie, on compte en colis (quantity directement) plutôt
        # qu'en unités (quantity x units_per_case). Pour tous les autres produits,
        # on applique le facteur de conversion extrait de la description à l'import
        # Le GROUP BY agrège toutes les transactions d'un même distributeur pour un
        # même accord en une seule ligne — c'est l'unité de travail du calcul
        dataframe_transaction = pd.read_sql(
            text("""
                SELECT
                    transaction.fk_id_distributor,
                    transaction.fk_id_agreement,
                    SUM(
                        CASE WHEN agreement.is_billed_per_case = 1
                            THEN transaction.quantity
                        ELSE transaction.quantity * product.units_per_case
                        END
                    ) AS uvc
                FROM transaction
                JOIN product   ON product.id_product   = transaction.fk_id_product
                JOIN agreement ON agreement.id_agreement = transaction.fk_id_agreement
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
        # une par tranche de volume (min_uvc, max_uvc, price). C'est dans cette table
        # qu'on va chercher le prix applicable une fois le palier déterminé
        dataframe_agreement_tiers = pd.read_sql(
            text("""
                SELECT id_agreement_tier, fk_id_agreement, min_uvc, max_uvc, price
                FROM agreement_tier
                ORDER BY fk_id_agreement, min_uvc
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
            text("SELECT COUNT(*) FROM `transaction` WHERE fk_id_agreement IS NOT NULL")
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

    # UVC totale par palier_group — global tous distributeurs confondus
    # C'est ce total qui détermine le palier atteint; il s'applique ensuite
    # à chaque (distributeur x accord) pour calculer son propre revenu
    group_totals = (
        dataframe[dataframe["palier_group"].notna()] # Ignore les accords sans palier_group
        .groupby("palier_group")["uvc"] # Sommer toutes les UVC du groupe, tous distributeurs confondus
        .sum() # Sommer les UVC pour chaque groupe
        .rename("group_uvc") # Renommer la colonne
        .reset_index() # Remettre les colonnes de groupement comme colonnes normales
    )

    dataframe = dataframe.merge(
        group_totals,
        on="palier_group",
        how="left"
    )

    # Construit un dictionnaire d'accès rapide aux paliers : {id_agreement: [liste de paliers]}
    # Évite de refiltrer le DataFrame à chaque itération de la boucle principale —
    # un simple .get(agreement_id) suffit pour récupérer les 3 paliers d'un accord
    tiers_by_agreement: dict = {}
    for _, tier_row in dataframe_agreement_tiers.iterrows():
        foreign_key = int(tier_row["fk_id_agreement"])
        tiers_by_agreement.setdefault(foreign_key, []).append(tier_row)

    # ── Étape 3 : Résolution du palier et calcul du revenu ───────────────────

    # results : liste des résultats à retourner à l'interface pour affichage
    # transactions_to_update : liste des mises à jour à appliquer en base (étape 4)
    results:             list = []
    transactions_to_update: list = []
    total = len(dataframe)

    for index, (_, row) in enumerate(dataframe.iterrows()):
        _progression_bar(50 + int(35 * index / max(total, 1)), f"Accord {index + 1}/{total}…")

        # Extraction des valeurs de la ligne courante avec des noms explicites
        # Les str() et or "N/A" protègent contre les valeurs NULL
        # comme NaN depuis pandas, ce qui provoquerait des erreurs à l'affichage
        agreement_id   = int(row["fk_id_agreement"])
        distributor_id = int(row["fk_id_distributor"])
        uvc_accord     = int(row["uvc"])
        industrial     = str(row.get("industrial_name") or "N/A")
        brand          = str(row.get("brand_name")      or "N/A")
        category       = str(row.get("category_name")   or "N/A")
        distributor    = str(row.get("distributor_name") or "N/A")
        palier_group   = str(row.get("palier_group")     or "—")

        # group_uvc est le volume total du palier_group (tous accords + tous distributeurs confondus)
        # Si l'accord n'a pas de palier_group (ex : produit hors accord comme Lipton),
        # on utilise le volume de l'accord seul comme fallback — il n'atteindra jamais
        # de palier, mais ça évite une erreur et produit un message "Aucun palier applicable"
        group_uvc_raw = row.get("group_uvc")
        group_uvc     = int(group_uvc_raw) if pd.notna(group_uvc_raw) else uvc_accord

        # Récupère les paliers de cet accord et les trie du plus élevé au plus bas
        # On teste d'abord le palier le plus haut : dès qu'on trouve un intervalle
        # [min_uvc, max_uvc] qui contient group_uvc, c'est le palier applicable
        tiers = sorted(
            tiers_by_agreement.get(agreement_id, []),
            key=lambda tier: int(tier["min_uvc"]),
            reverse=True
        )

        applicable_tier = None
        for tier in tiers:
            min_uvc = int(tier["min_uvc"])
            max_uvc = int(tier["max_uvc"]) if pd.notna(tier["max_uvc"]) else None

            if group_uvc >= min_uvc and (max_uvc is None or group_uvc <= max_uvc):
                applicable_tier = tier
                break

        # Palier trouvé → préparation de la mise à jour en base et construction du détail.
        # revenue est calculé uniquement pour alimenter la chaîne detail (affichage).
        # Chaque distributeur a ses propres UVC, mais tous partagent le même palier
        # (déterminé par le group_uvc global, tous distributeurs confondus).
        if applicable_tier is not None:
            tier_id    = int(applicable_tier["id_agreement_tier"])
            tier_price = float(applicable_tier["price"])
            min_palier   = int(applicable_tier["min_uvc"])
            max_palier   = (
                f"{int(applicable_tier['max_uvc']):,}"
                if pd.notna(applicable_tier["max_uvc"])
                else "+∞"
            )
            revenue  = uvc_accord * tier_price
            tier_str = f"{tier_price:.2f} €/UVC"
            detail   = (
                f"{uvc_accord:,} UVC x {tier_price:.2f} €/UVC "
                f"= {revenue:,.2f} €  "
                f"(palier {min_palier:,}-{max_palier} UVC, total groupe {group_uvc:,} UVC)"
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
            detail     = f"Aucun palier applicable (total groupe {group_uvc:,} UVC)"

        # Empile le résultat de cette ligne pour l'affichage dans l'interface.
        # Chaque entrée correspond à un accord pour un distributeur donné.
        results.append({
            "id_agreement": agreement_id,
            "distributor":  distributor,
            "industrial":   industrial,
            "brand":        brand,
            "category":     category,
            "palier_group": palier_group,
            "total_uvc":    uvc_accord,
            "group_uvc":    group_uvc,
            "tier_price":   tier_str,
            "detail":       detail,
        })

    # ── Étape 4 : Mise à jour des colonnes agreement dans transaction ─────────
    _progression_bar(85, "Mise à jour des transactions…")

    if transactions_to_update:
        # Met à jour en base les 3 colonnes agreement_* ayant atteint un palier
        # agreement_total_price est recalculé directement en SQL
        # avec la même logique CASE WHEN que l'étape 1 : quantity pour is_billed_per_case = 1,
        # quantity x units_per_case sinon
        update_sql = text("""
            UPDATE transaction
            JOIN product   ON product.id_product     = transaction.fk_id_product
            JOIN agreement ON agreement.id_agreement = transaction.fk_id_agreement
            SET transaction.fk_id_agreement_tier  = :fk_id_agreement_tier,
                transaction.agreement_unit_price  = :agreement_unit_price,
                transaction.agreement_total_price = ROUND(
                    :agreement_unit_price *
                    CASE
                        WHEN agreement.is_billed_per_case = 1 THEN transaction.quantity
                        ELSE transaction.quantity * product.units_per_case
                    END,
                    2
                )
            WHERE transaction.fk_id_agreement = :fk_id_agreement
                AND transaction.fk_id_distributor = :fk_id_distributor
        """)

        with get_connection() as connection:
            for update_transaction in transactions_to_update:
                connection.execute(update_sql, update_transaction)

            connection.commit()

    # Idem : si le calcul est relancé après une modification des données
    # (nouveau fichier importé, accord mis à jour...), certains
    # peuvent ne plus atteindre de palier. On remet leurs colonnes agreement_* à NULL
    # pour ne pas laisser des valeurs obsolètes du run précédent.
    agreements_updated = {(update_transaction["fk_id_agreement"], update_transaction["fk_id_distributor"]) for update_transaction in transactions_to_update}
    agreements_all = {(int(row["fk_id_agreement"]), int(row["fk_id_distributor"])) for _, row in dataframe.iterrows()}
    agreements_no_tier = agreements_all - agreements_updated

    if agreements_no_tier:
        reset_sql = text("""
            UPDATE transaction
            SET fk_id_agreement_tier  = NULL,
                agreement_unit_price  = NULL,
                agreement_total_price = NULL
            WHERE fk_id_agreement     = :fk_id_agreement
                AND fk_id_distributor = :fk_id_distributor
        """)

        with get_connection() as connection:
            for agreement_id, distributor_id in agreements_no_tier:
                connection.execute(reset_sql, {
                    "fk_id_agreement":   agreement_id,
                    "fk_id_distributor": distributor_id,
                })

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
