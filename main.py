# Python version : 3.13.13

# Import Python packages
import sys

# Import modules from Python packages
## None

# Import third party packages
## None

# Import modules from third party packages
from PyQt6.QtWidgets import QApplication

# Import personal functions
from gui_folder.command_folder.cmd_mainwindow_file import CmdMainWindowClass as main_window

# Custom variable type construction
## None

# -----

def main():
    """ Function main for start project in GUI """

    application = QApplication(sys.argv)
    mainwindow = main_window()
    mainwindow.show()

    sys.exit(application.exec())

# -----

if __name__ == "__main__":
    main()
