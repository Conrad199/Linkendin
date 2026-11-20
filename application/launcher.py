from __future__ import annotations

import sys

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from application.notifier import send_email_async
from application.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("LinkedIn Auto-Enricher")
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,        QColor("#F8FAFC"))
    palette.setColor(QPalette.ColorRole.WindowText,    QColor("#0F172A"))
    palette.setColor(QPalette.ColorRole.Base,          QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#F1F5F9"))
    palette.setColor(QPalette.ColorRole.Text,          QColor("#0F172A"))
    palette.setColor(QPalette.ColorRole.Button,        QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.ButtonText,    QColor("#0F172A"))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    QTimer.singleShot(
        0,
        lambda: send_email_async(
            "[LinkedIn Scraper] Démarrage du projet",
            "L'application LinkedIn Auto-Enricher a démarré sur le serveur Ubuntu.",
        ),
    )
    sys.exit(app.exec())
