from pathlib import Path

from PyQt6.QtCore import QSize, Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel, QMessageBox,
    QPlainTextEdit, QPushButton, QScrollArea, QVBoxLayout,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView


IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"
}
TEXT_EXTENSIONS = {
    ".txt", ".md", ".py", ".json", ".csv", ".xml", ".html", ".htm",
    ".css", ".js", ".log", ".yaml", ".yml", ".ini",
}


def create_attachment_button(icon_path, tooltip, parent=None):
    button = QPushButton(parent)
    button.setIcon(QIcon(icon_path))
    button.setIconSize(QSize(16, 16))
    button.setFixedSize(30, 30)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setToolTip(tooltip)
    return button


def extract_attachment_text(path):
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            return "[PDF joint : installez pypdf pour extraire son texte.]"
    if suffix == ".docx":
        try:
            from docx import Document
            document = Document(str(path))
            chunks = [paragraph.text for paragraph in document.paragraphs]
            for table in document.tables:
                for row in table.rows:
                    chunks.append(" | ".join(cell.text for cell in row.cells))
            return "\n".join(chunks)
        except ImportError:
            return "[DOCX joint : installez python-docx pour en extraire le texte.]"
    if suffix == ".xlsx":
        try:
            from openpyxl import load_workbook
            workbook = load_workbook(str(path), read_only=True, data_only=True)
            chunks = []
            for sheet in workbook.worksheets:
                chunks.append(f"[Feuille : {sheet.title}]")
                for row in sheet.iter_rows(values_only=True):
                    values = ["" if value is None else str(value) for value in row]
                    if any(values):
                        chunks.append(" | ".join(values))
            workbook.close()
            return "\n".join(chunks)
        except ImportError:
            return "[XLSX joint : installez openpyxl pour en extraire le contenu.]"
    if suffix in TEXT_EXTENSIONS:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="utf-8-sig", errors="replace")
    return None


def open_with_default_application(path, parent=None):
    if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve()))):
        QMessageBox.warning(
            parent, "Ouverture impossible",
            "Windows n'a pas pu ouvrir ce fichier avec son application par défaut.",
        )


def open_attachment_preview(path, parent=None):
    path = Path(path)
    if not path.is_file():
        QMessageBox.warning(
            parent, "Ouverture impossible",
            "Le fichier n'existe plus à cet emplacement.",
        )
        return

    suffix = path.suffix.lower()
    dialog = QDialog(parent)
    dialog.setWindowTitle(path.name)
    dialog.resize(900, 700)
    layout = QVBoxLayout(dialog)

    if suffix in IMAGE_EXTENSIONS:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            QMessageBox.warning(
                parent, "Aperçu impossible",
                "Ce format d'image ne peut pas être affiché.",
            )
            return
        image = QLabel()
        image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image.setPixmap(pixmap.scaled(
            860, 610, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(image)
        layout.addWidget(scroll)
        layout.addWidget(
            QLabel(f"{path.name}  •  {pixmap.width()} × {pixmap.height()} px")
        )
    elif suffix == ".pdf":
        pdf_view = QWebEngineView(dialog)
        pdf_view.setUrl(QUrl.fromLocalFile(str(path.resolve())))
        layout.addWidget(pdf_view)
    else:
        try:
            text = extract_attachment_text(path)
        except Exception as exc:
            QMessageBox.warning(parent, "Aperçu impossible", str(exc))
            return
        if text is None:
            details = QLabel(
                "L'aperçu intégré n'est pas disponible pour ce format. "
                "Vous pouvez l'ouvrir avec l'application par défaut."
            )
            details.setWordWrap(True)
            layout.addWidget(details)
            open_button = QPushButton("Ouvrir avec l'application par défaut")
            open_button.clicked.connect(
                lambda checked=False: open_with_default_application(path, dialog)
            )
            layout.addWidget(open_button)
        else:
            document = QPlainTextEdit()
            document.setReadOnly(True)
            document.setPlainText(text or "Aucun texte lisible dans ce document.")
            layout.addWidget(document)

    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    buttons.rejected.connect(dialog.reject)
    buttons.accepted.connect(dialog.accept)
    layout.addWidget(buttons)
    dialog.exec()
