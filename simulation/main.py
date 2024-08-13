import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QLineEdit, QFormLayout


sys.path.insert(0,'..')
sys.path.insert(0,'../..')
sys.path.insert(0,'../../..')


from Central_Controller.CTGUI import CentralControllerGUI


def main():
    app = QApplication(sys.argv)
    ex = CentralControllerGUI(cell_size=30)
    ex.show()
    sys.exit(app.exec_())
# Main execution
if __name__ == "__main__":
    main()