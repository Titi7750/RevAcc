# Import Python packages
## None

# Import modules from Python packages
## None

# Import third party packages
## None

# Import modules from third party packages
from PyQt6.QtWidgets import (
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# Import personal functions
## None

# Custom variable type construction
## None

# -----

class GuiCalculationPageClass(QWidget):
    """
    Page Calcul (vue uniquement).
    Un seul bouton lance le calcul et ouvre directement la fenêtre d'enregistrement Excel.
    La logique est dans CmdCalculationPageClass.
    """

    def __init__(self) -> None:
        super().__init__()
        self.init_ui_method()
        return None

    # -----

    def init_ui_method(self) -> None:
        """ Création de la mise en page de la page Calcul """

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        # ── En-tête ──────────────────────────────────────────────────────────
        title_label = QLabel("Calcul des revenus")
        title_label.setObjectName("pageTitle")
        subtitle_label = QLabel(
            "Lance le calcul sur toutes les transactions présentes en base, "
            "puis ouvre une fenêtre pour choisir où enregistrer le fichier Excel de résultats."
        )
        subtitle_label.setObjectName("subtitle")
        subtitle_label.setWordWrap(True)

        # ── Bouton de lancement ───────────────────────────────────────────────
        self.button_start_calculation = QPushButton("Calculer et exporter vers Excel")
        self.button_start_calculation.setObjectName("primaryButton")

        # ── Progression ───────────────────────────────────────────────────────
        self.progress_calcul = QProgressBar()
        self.progress_calcul.setValue(0)

        self.label_calcul_status = QLabel("Aucun calcul lancé.")
        self.label_calcul_status.setObjectName("subtitle")

        # ── Log du calcul (accord par accord) ────────────────────────────────
        log_title = QLabel("Détail du calcul")

        self.calculation_log = QTextEdit()
        self.calculation_log.setReadOnly(True)
        self.calculation_log.setPlaceholderText(
            "Le détail accord par accord apparaîtra ici après le calcul."
        )

        # Assemblage final
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addSpacing(10)
        layout.addWidget(self.button_start_calculation)
        layout.addWidget(self.progress_calcul)
        layout.addWidget(self.label_calcul_status)
        layout.addWidget(log_title)
        layout.addWidget(self.calculation_log)

        return None
