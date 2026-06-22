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
    Calcule le revenu par accord, par distributeur.

    Logique :
    1. Calculer les UVC par (distributeur x accord) :
        - is_billed_per_case = 0 → uvc = quantity x units_per_case
        - is_billed_per_case = 1 → uvc = quantity  (ex : Amora - Dosette, compté en colis)
    2. Sommer les UVC de tous les accords du même (distributeur x palier_group)
        → UVC totale du groupe pour CE distributeur
    3. Déterminer le palier applicable depuis l'UVC totale du groupe
    4. Revenu par accord = uvc_accord x prix_palier (€/UVC)
    5. Mettre à jour fk_id_agreement_tier, agreement_unit_price, agreement_total_price dans la table transaction

    Si un distributeur n'atteint aucun seuil pour un groupe, les colonnes agreement
    restent NULL (aucune écriture).

    Retourne (results_list, summary_dict).
    """

    def _progression_bar(param_percentage: int, param_message: str):
        """ Met à jour la barre de progression """

        if param_progress_cb:
            param_progress_cb(param_percentage, param_message)

    # ── Étape 1 : Chargement des données ─────────────────────────────────────
    _progression_bar(0, "Chargement des transactions…")

    with get_connection() as connection:
        # UVC par (distributeur x accord), avec gestion is_billed_per_case
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
                    ) AS uvc,
                    SUM(transaction.total_price) AS total_ca
                FROM transaction
                JOIN product   ON product.id_product   = transaction.fk_id_product
                JOIN agreement ON agreement.id_agreement = transaction.fk_id_agreement
                WHERE transaction.fk_id_agreement IS NOT NULL
                GROUP BY transaction.fk_id_distributor, transaction.fk_id_agreement
            """),
            connection
        )

        if dataframe_transaction.empty:
            return [], {"total_revenue": 0.0, "agreements": 0, "transactions": 0}

        _progression_bar(20, "Chargement des accords…")

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

        dataframe_agreement_tiers = pd.read_sql(
            text("""
                SELECT id_agreement_tier, fk_id_agreement, min_uvc, max_uvc, price
                FROM agreement_tier
                ORDER BY fk_id_agreement, min_uvc
            """),
            connection
        )

        dataframe_distributors = pd.read_sql(
            text("SELECT id_distributor, distributor_name FROM distributor"),
            connection
        )

        _progression_bar(45, "Comptage des transactions…")
        transaction_count = connection.execute(
            text("SELECT COUNT(*) FROM `transaction` WHERE fk_id_agreement IS NOT NULL")
        ).scalar() or 0

    # ── Étape 2 : Enrichissement et agrégation ────────────────────────────────
    _progression_bar(50, "Calcul des revenus par groupe de palier…")

    # Jointure avec les infos d'accord et de distributeur
    dataframe = dataframe_transaction.merge(
        dataframe_agreement_clean,
        left_on="fk_id_agreement",
        right_on="id_agreement",
        how="left"
    )
    dataframe = dataframe.merge(
        dataframe_distributors,
        left_on="fk_id_distributor",
        right_on="id_distributor",
        how="left"
    )

    # UVC totale par (distributeur x palier_group) — chaque distributeur a son propre compteur
    group_totals = (
        dataframe[dataframe["palier_group"].notna()] # Ignore les accords sans palier_group
        .groupby(["fk_id_distributor", "palier_group"])["uvc"] # Grouper par distributor et palier_group
        .sum() # Sommer les UVC pour chaque groupe
        .rename("group_uvc") # Renommer la colonne
        .reset_index() # Remettre les colonnes de groupement comme colonnes normales
    )

    dataframe = dataframe.merge(
        group_totals,
        on=["fk_id_distributor", "palier_group"],
        how="left"
    )

    # Index des paliers pour lookup rapide : {fk_id_agreement: [tier_rows]}
    tiers_by_agreement: dict = {}
    for _, tier_row in dataframe_agreement_tiers.iterrows():
        foreign_key = int(tier_row["fk_id_agreement"])
        tiers_by_agreement.setdefault(foreign_key, []).append(tier_row)

    # ── Étape 3 : Résolution du palier et calcul du revenu ───────────────────
    results:             list = []
    transactions_to_update: list = []
    total = len(dataframe)

    for index, (_, row) in enumerate(dataframe.iterrows()):
        _progression_bar(50 + int(35 * index / max(total, 1)), f"Accord {index + 1}/{total}…")

        agreement_id   = int(row["fk_id_agreement"])
        distributor_id = int(row["fk_id_distributor"])
        uvc_accord     = int(row["uvc"])
        total_ca       = float(row["total_ca"])
        industrial     = str(row.get("industrial_name") or "N/A")
        brand          = str(row.get("brand_name")      or "N/A")
        category       = str(row.get("category_name")   or "N/A")
        distributor    = str(row.get("distributor_name") or "N/A")
        palier_group   = str(row.get("palier_group")     or "—")

        group_uvc_raw = row.get("group_uvc")
        group_uvc     = int(group_uvc_raw) if pd.notna(group_uvc_raw) else uvc_accord

        # Palier applicable basé sur l'UVC totale DU GROUPE pour CE distributeur
        # Tri décroissant → on teste le palier le plus élevé en premier
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
                f"{uvc_accord:,} UVC × {tier_price:.2f} €/UVC "
                f"= {revenue:,.2f} €  "
                f"(palier {min_palier:,}–{max_palier} UVC, total groupe {group_uvc:,} UVC)"
            )

            # Prépare la mise à jour des transactions de cet accord + distributeur
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
            revenue    = 0.0
            detail     = f"Aucun palier applicable (total groupe {group_uvc:,} UVC)"

        results.append({
            "id_agreement": agreement_id,
            "distributor":  distributor,
            "industrial":   industrial,
            "brand":        brand,
            "category":     category,
            "palier_group": palier_group,
            "total_uvc":    uvc_accord,
            "group_uvc":    group_uvc,
            "total_ca":     total_ca,
            "tier_price":   tier_str,
            "revenue":      revenue,
            "detail":       detail,
        })

    # ── Étape 4 : Mise à jour des colonnes agreement dans transaction ─────────
    _progression_bar(85, "Mise à jour des transactions…")

    if transactions_to_update:
        update_sql = text("""
            UPDATE transaction
            SET fk_id_agreement_tier  = :fk_id_agreement_tier,
                agreement_unit_price  = :agreement_unit_price,
                agreement_total_price = ROUND(:agreement_unit_price * quantity, 2)
            WHERE fk_id_agreement     = :fk_id_agreement
                AND fk_id_distributor = :fk_id_distributor
        """)

        with get_connection() as connection:
            for update_transaction in transactions_to_update:
                connection.execute(update_sql, update_transaction)

            connection.commit()

    # Remettre à NULL les transactions dont le distributeur n'a atteint aucun palier
    # (cas d'un recalcul après modification des données)
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

    summary = {
        "total_revenue": sum(result["revenue"] for result in results),
        "agreements":    len(results),
        "transactions":  int(transaction_count),
    }

    return results, summary
