# Import Python packages
## None

# Import modules from Python packages
## None

# Import third party packages
## None

# Import modules from third party packages
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

# Import personal functions
from gui_folder.graphic_folder.gui_calculation_file import GuiCalculationPageClass
# -----
from core_folder.calculation_file import run_calculation_method
from core_folder.export_file import export_calculation_method

# Custom variable type construction
## None

# -----


class CalculationWorker(QThread):
    """
    Thread d'arrière-plan pour exécuter le calcul des revenus sans bloquer l'interface.
    Émet progress(pourcentage, message) pendant le calcul,
    puis finished(résultats, résumé) ou error(message) à la fin.
    """

    progress = pyqtSignal(int, str)
    finished = pyqtSignal(list, dict)
    error    = pyqtSignal(str)

    # -----

    def run(self) -> None:
        """ Exécution du calcul dans le thread (appelé automatiquement par QThread.start) """

        try:
            calc_results, calc_summary = run_calculation_method(self.progress.emit)
            self.finished.emit(calc_results, calc_summary)

        except Exception as exc:
            self.error.emit(str(exc))

# -----

class CmdCalculationPageClass(GuiCalculationPageClass):
    """
    Contrôleur de la page Calcul.
    Hérite de la vue GuiCalculationPageClass et y ajoute la logique :
    lancement du thread, affichage du log, export Excel direct.
    """

    # Émis après un calcul réussi avec le revenu total → la fenêtre principale met à jour le KPI
    calc_done = pyqtSignal(float)

    # -----

    def __init__(self) -> None:
        super().__init__()
        self._calc_worker = None
        self.connect_events_method()
        return None

    # -----

    def connect_events_method(self) -> None:
        """ Connexion du bouton de lancement """

        self.button_start_calculation.clicked.connect(self.start_calculation_method)

        return None

    # -----

    def start_calculation_method(self) -> None:
        """ Réinitialise l'affichage et lance le calcul dans un thread séparé """

        self.button_start_calculation.setEnabled(False)
        self.progress_calcul.setValue(0)
        self.label_calcul_status.setText("Calcul en cours…")
        self.calculation_log.clear()

        # Démarrage du worker
        self._calc_worker = CalculationWorker()
        self._calc_worker.progress.connect(self.on_calculation_progress_method)
        self._calc_worker.finished.connect(self.on_calculation_finished_method)
        self._calc_worker.error.connect(self.on_calculation_error_method)
        self._calc_worker.start()

        return None

    # -----

    def on_calculation_progress_method(self, param_percent: int, param_message: str) -> None:
        """ Mise à jour de la barre de progression et du label de statut """

        self.progress_calcul.setValue(param_percent)
        self.label_calcul_status.setText(param_message)
        QApplication.processEvents()

        return None

    # -----

    def on_calculation_finished_method(self, param_results: list, param_summary: dict) -> None:
        """
        Traitement de la fin d'un calcul réussi :
        1. Affiche le log détaillé
        2. Émet le signal pour mettre à jour le dashboard
        3. Ouvre la fenêtre d'enregistrement du fichier Excel
        """

        self.button_start_calculation.setEnabled(True)
        self.progress_calcul.setValue(100)

        total_revenue = param_summary["total_revenue"]
        self.label_calcul_status.setText(
            f"Calcul terminé — Revenu total : {total_revenue:,.2f} €"
        )

        # ── Affichage du log accord par accord ───────────────────────────────
        log_lines = [
            f"Transactions analysées : {param_summary['transactions']}",
            f"Accords concernés      : {param_summary['agreements']}",
            f"Revenu total calculé   : {total_revenue:,.2f} €",
            "",
            "Détail par accord :",
        ]
        for result_item in param_results:
            log_lines.append(
                f"  • {result_item['industrial']} / {result_item['brand']} / {result_item['category']}"
                f"  →  {result_item['detail']}"
            )
        self.calculation_log.setPlainText("\n".join(log_lines))

        # ── Notification du dashboard via signal ─────────────────────────────
        self.calc_done.emit(total_revenue)

        # ── Export immédiat vers Excel ────────────────────────────────────────
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer le calcul détaillé",
            "calcul_revacc.xlsx",
            "Fichier Excel (*.xlsx)",
        )

        if not file_path:
            # L'utilisateur a annulé l'export — le log reste visible dans la page
            return

        try:
            export_calculation_method(file_path, param_results, param_summary)
            QMessageBox.information(self, "Export réussi", f"Fichier enregistré :\n{file_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Erreur d'export", str(exc))

        return None

    # -----

    def on_calculation_error_method(self, param_error_message: str) -> None:
        """ Traitement d'une erreur pendant le calcul """

        self.button_start_calculation.setEnabled(True)
        self.progress_calcul.setValue(0)
        self.label_calcul_status.setText("Erreur lors du calcul.")
        QMessageBox.critical(self, "Erreur de calcul", param_error_message)

        return None
