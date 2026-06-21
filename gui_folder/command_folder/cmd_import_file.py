# Import Python packages
## None

# Import modules from Python packages
## None

# Import third party packages
## None

# Import modules from third party packages
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMessageBox,
    QProgressDialog,
    QTableWidgetItem,
)

# Import personal functions
from gui_folder.graphic_folder.gui_import_file import GuiImportPageClass
# -----
from core_folder.export_file import export_agreements_template
from core_folder.import_file import import_transactions, import_agreements

# Custom variable type construction
## None

# -----

class ImportWorker(QThread):
    """
    Thread d'arrière-plan pour exécuter un import Excel sans bloquer l'interface.
    Émet progress(pourcentage, message) pendant l'import,
    puis finished(résultat) ou error(message) à la fin.
    """

    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict)
    error    = pyqtSignal(str)

    # -----

    def __init__(self, param_file_type: str, param_file_path: str) -> None:
        """ Initialisation avec le type d'import ('transactions' ou 'accords') et le chemin du fichier """

        super().__init__()
        self.file_type = param_file_type
        self.file_path = param_file_path

        return None

    # -----

    def run(self) -> None:
        """ Exécution de l'import dans le thread (appelé automatiquement par QThread.start) """

        try:
            # Choix de la fonction selon le type d'import
            if self.file_type == "transactions":
                import_result = import_transactions(self.file_path, self.progress.emit)
            else:
                import_result = import_agreements(self.file_path, self.progress.emit)

            self.finished.emit(import_result)

        except Exception as exc:
            self.error.emit(str(exc))

# -----

class CmdImportPageClass(GuiImportPageClass):
    """
    Contrôleur de la page Import.
    Hérite de la vue GuiImportPageClass et y ajoute toute la logique :
    sélection du fichier, lancement du thread, mise à jour de l'historique.
    """

    # Émis après un import réussi → la fenêtre principale rafraîchit le dashboard et la consultation
    data_changed = pyqtSignal()

    # -----

    def __init__(self) -> None:
        super().__init__()

        # État interne : worker actif et ligne courante dans le tableau d'historique
        self._import_worker      = None
        self._progress_dialog    = None
        self._current_import_row = -1

        self.connect_events_method()

        return None

    # -----

    def connect_events_method(self) -> None:
        """ Connexion des boutons aux méthodes correspondantes """

        self.button_import_transactions.clicked.connect(
            lambda: self.start_import_method("transactions")
        )
        self.button_import_accords.clicked.connect(
            lambda: self.start_import_method("accords")
        )
        self.button_export_template.clicked.connect(self.export_template_method)

        return None

    # -----

    def start_import_method(self, param_file_type: str) -> None:
        """ Ouvre le sélecteur de fichier et lance l'import du type donné """

        # Sélection du fichier Excel principal à importer
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Importer {param_file_type}",
            "",
            "Fichiers Excel (*.xlsx)",
        )
        if not file_path:
            return

        # Confirmation obligatoire avant l'import des accords (opération destructive)
        if param_file_type == "accords":
            reply = QMessageBox.question(
                self,
                "Confirmation — Import accords",
                "L'import va mettre à jour les accords commerciaux.\n"
                "Les accords modifiés seront archivés, les accords identiques prolongés.\n"
                "Aucune donnée ne sera supprimée.\n\n"
                "Continuer ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # Ajout d'une ligne de suivi dans le tableau d'historique
        import_row = self.table_imports.rowCount()
        self.table_imports.insertRow(import_row)
        self.table_imports.setItem(import_row, 0, QTableWidgetItem(param_file_type))
        self.table_imports.setItem(import_row, 1, QTableWidgetItem(file_path))
        self.table_imports.setItem(import_row, 2, QTableWidgetItem("En cours…"))
        self.table_imports.setItem(import_row, 3, QTableWidgetItem(""))
        self._current_import_row = import_row

        # Boîte de progression modale (bloque les interactions pendant l'import)
        self._progress_dialog = QProgressDialog(
            f"Import {param_file_type} en cours…", None, 0, 100, self
        )
        self._progress_dialog.setWindowTitle(f"Import {param_file_type}")
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.setMinimumDuration(0)
        self._progress_dialog.setValue(0)

        # Désactivation des boutons pendant l'import pour éviter un double import
        self.button_import_transactions.setEnabled(False)
        self.button_import_accords.setEnabled(False)

        # Démarrage du thread d'import
        self._import_worker = ImportWorker(param_file_type, file_path)
        self._import_worker.progress.connect(self.on_import_progress_method)
        self._import_worker.finished.connect(self.on_import_finished_method)
        self._import_worker.error.connect(self.on_import_error_method)
        self._import_worker.start()

        return None

    # -----

    def on_import_progress_method(self, param_percent: int, param_message: str) -> None:
        """ Mise à jour de la barre de progression pendant l'import """

        if self._progress_dialog:
            self._progress_dialog.setValue(param_percent)
            self._progress_dialog.setLabelText(param_message)
        QApplication.processEvents()

        return None

    # -----

    def on_import_finished_method(self, param_result: dict) -> None:
        """ Traitement de la fin d'un import réussi : mise à jour historique + signal """

        if self._progress_dialog:
            self._progress_dialog.close()

        self.button_import_transactions.setEnabled(True)
        self.button_import_accords.setEnabled(True)

        # Construction du message de résultat selon le type d'import
        if "inserted" in param_result:
            result_detail = (
                f"{param_result['inserted']} transactions insérées"
                + (f" ({param_result['null_fk']} avec FK manquants)" if param_result["null_fk"] else "")
            )
        else:
            result_detail = (
                f"{param_result['agreements']} accords créés, "
                f"{param_result.get('extended', 0)} prolongés, "
                f"{param_result.get('closed', 0)} archivés — "
                f"{param_result['tiers']} paliers insérés"
            )

        # Mise à jour de la ligne dans le tableau d'historique
        if self._current_import_row >= 0:
            self.table_imports.setItem(self._current_import_row, 2, QTableWidgetItem("Importé"))
            self.table_imports.setItem(self._current_import_row, 3, QTableWidgetItem(result_detail))

        # Signal vers la fenêtre principale pour rafraîchir dashboard + consultation
        self.data_changed.emit()

        QMessageBox.information(self, "Import terminé", result_detail)

        return None

    # -----

    def on_import_error_method(self, param_error_message: str) -> None:
        """ Traitement d'une erreur pendant l'import """

        if self._progress_dialog:
            self._progress_dialog.close()

        self.button_import_transactions.setEnabled(True)
        self.button_import_accords.setEnabled(True)

        if self._current_import_row >= 0:
            self.table_imports.setItem(self._current_import_row, 2, QTableWidgetItem("Erreur"))
            self.table_imports.setItem(self._current_import_row, 3, QTableWidgetItem(param_error_message[:120]))

        QMessageBox.critical(self, "Erreur d'import", param_error_message)

        return None

    # -----

    def export_template_method(self) -> None:
        """ Export du modèle accords vers un fichier Excel choisi par l'utilisateur """

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter le modèle accords",
            "modele_accords_revacc.xlsx",
            "Fichier Excel (*.xlsx)",
        )
        if not file_path:
            return

        try:
            export_agreements_template(file_path)
            QMessageBox.information(
                self,
                "Export réussi",
                f"Modèle exporté vers :\n{file_path}\n\n"
                "Modifiez ce fichier puis importez-le via « Importer accords ».",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Erreur d'export", str(exc))

        return None
