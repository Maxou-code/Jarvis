import json
import shutil
from pathlib import Path

from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QSizePolicy, QToolButton, QVBoxLayout, QWidget,
)

from UI.attachment_preview import (
    IMAGE_EXTENSIONS, create_attachment_button, open_attachment_preview,
)
from UI.chart_view import InlineChart
from UI.markdown_view import MarkdownWebView, render_markdown
from UI.viewer3d import Inline3DViewer


class ChatAttachmentCard(QFrame):
    def __init__(self, attachment, parent=None):
        super().__init__(parent)
        self.path = Path(attachment.get("path", ""))
        self.is_image = self.path.suffix.lower() in IMAGE_EXTENSIONS
        self.setStyleSheet("""
            QFrame { background:#081923; border:1px solid #145064; border-radius:7px; }
            QLabel { color:#D7F8FF; border:none; background:transparent; }
            QPushButton {
                background:#0D2A37; color:#C9D7E8; border:1px solid #176078;
                border-radius:6px; padding:4px;
            }
            QPushButton:hover { background:#145064; }
        """)
        row = QHBoxLayout(self)
        row.setContentsMargins(7, 5, 7, 5)
        row.setSpacing(8)

        self.preview = QLabel()
        self.preview.setFixedSize(48, 48)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setStyleSheet("background:#0A202B; border-radius:5px;")
        if self.is_image and self.path.is_file():
            pixmap = QPixmap(str(self.path))
            if not pixmap.isNull():
                self.preview.setPixmap(pixmap.scaled(
                    self.preview.width() - 4, self.preview.height() - 4,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                ))
            else:
                self.preview.setText("IMAGE")
        else:
            self.preview.setText(self.path.suffix.upper().lstrip(".")[:5] or "FICHIER")
        row.addWidget(self.preview)

        name = QLabel(str(attachment.get("name") or self.path.name))
        name.setToolTip(str(self.path))
        name.setMinimumWidth(0)
        name.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        name.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        row.addWidget(name, 1)

        open_button = create_attachment_button(
            "Icons/arrow-up-right-from-square-solid-full.svg",
            "Ouvrir en grand",
            self,
        )
        open_button.clicked.connect(self.open_attachment)
        row.addWidget(open_button)
        save_button = create_attachment_button(
            "Icons/download-solid-full.svg",
            "Télécharger / enregistrer une copie",
            self,
        )
        save_button.clicked.connect(self.save_attachment)
        row.addWidget(save_button)

    def open_attachment(self):
        open_attachment_preview(self.path, self)

    def save_attachment(self):
        if not self.path.is_file():
            QMessageBox.warning(self, "Téléchargement impossible", "Le fichier source n'existe plus.")
            return
        destination, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer une copie du fichier",
            str(Path.home() / self.path.name), "Tous les fichiers (*)",
        )
        if not destination:
            return
        target = Path(destination)
        if target.resolve() == self.path.resolve():
            QMessageBox.information(self, "Copie inutile", "Le fichier est déjà à cet emplacement.")
            return
        try:
            shutil.copy2(self.path, target)
        except OSError as exc:
            QMessageBox.warning(self, "Échec de la copie", str(exc))


class ChartPreview(QFrame):
    open_requested = pyqtSignal(object)
    save_requested = pyqtSignal(object)

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = dict(data or {})
        self.setStyleSheet("""
            QFrame { background:#050B12; border:1px solid #174052; border-radius:6px; } 
            QLabel { color:#D9F8FF; border:none; font-weight:700; } 
            QPushButton { background:#102B38; color:#C8F5FF; border:1px solid #216078; 
            border-radius:4px; padding:5px 10px; } 
            QPushButton:hover { background:#17485B; }
            QPushButton#pngButton {
                background:#123D32;
                border-color:#27865F;
                color:#A5F0C7;
            }

            QPushButton#pngButton:hover {
                background:#195641;
            }
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(5)

        toolbar = QHBoxLayout()
        title = QLabel(str(self.data.get("title", "Graphique"))[:120])
        toolbar.addWidget(title, 1)

        open_button = QPushButton()
        open_button.setIcon(QIcon("Icons/arrow-up-right-from-square-solid-full.svg"))
        open_button.setToolTip("Ouvrir en grand")
        open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        open_button.clicked.connect(
            lambda: self.open_requested.emit(self.data)
        )
        toolbar.addWidget(open_button)

        save_button = QPushButton()
        save_button.setIcon(QIcon("Icons/download-solid-full.svg"))
        save_button.setToolTip("Enregistrer en PNG")
        save_button.setObjectName("pngButton")
        save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        save_button.clicked.connect(
            lambda: self.save_requested.emit(self.data)
        )
        toolbar.addWidget(save_button)
        layout.addLayout(toolbar)

        self.chart = InlineChart(self.data, self)
        layout.addWidget(self.chart)


class CollapsiblePanel(QFrame):
    open_content_requested = pyqtSignal(str, object)

    def __init__(self, title, content="", expanded=False, max_height=320):
        super().__init__()
        self.setObjectName("collapsePanel")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.max_height = max_height
        self._content_height = 48

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 6)
        layout.setSpacing(4)

        self.toggle = QToolButton()
        self.title = title
        self.toggle.setText(("⌄  " if expanded else "›  ") + title)
        self.toggle.setCheckable(True)
        self.toggle.setChecked(expanded)
        self.toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.toggle.setStyleSheet("""
            QToolButton { background: transparent; color: #38DDFB; border: none;
                padding: 5px 7px; text-align: left; font-size: 14px; font-weight: 650; }
            QToolButton:hover { color: #B9F7FF; }
        """)
        layout.addWidget(self.toggle)

        self.body = MarkdownWebView(self)
        self.body.open_content_requested.connect(self.open_content_requested)
        self.body.setVisible(expanded)
        self.body.setFixedHeight(48)
        self.body.content_size_changed.connect(self._on_content_size)
        layout.addWidget(self.body)

        self.toggle.toggled.connect(self._toggle)
        self.set_markdown(content)

    def _toggle(self, checked):
        self.toggle.setText(("⌄  " if checked else "›  ") + self.title)
        self.body.setVisible(checked)
        self.updateGeometry()

    def _on_content_size(self, _width, height):
        self._content_height = height
        self.refit()

    def refit(self):
        height = self._content_height
        if self.max_height is not None:
            height = min(height, self.max_height)
        self.body.setFixedHeight(max(36, height))
        self.updateGeometry()

    def set_markdown(self, markdown):
        self.current_markdown = markdown or ""
        self.body._markdown_source = self.current_markdown
        self.body.set_markdown(self.current_markdown)

    def set_plain_text(self, text):
        self.set_markdown(str(text).replace("\n", "  \n"))

    def append(self, text):
        self.current_markdown += str(text)
        self.set_markdown(self.current_markdown)


class MarkdownMessage(QFrame):
    """Bulle de message dont les vues HTML sont dimensionnées par WebEngine."""

    open_content_requested = pyqtSignal(str, object)
    save_content_requested = pyqtSignal(str, object)

    def __init__(self, role):
        super().__init__()
        self.role = role
        self.available_width = 900
        self.markdown_views = []
        self.panels = []
        self.extra_widgets = []
        self._view_sizes = {}
        self._fitting = False

        self.setObjectName("userBubble" if role == "user" else "assistantBubble")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(17, 13, 17, 14)
        self.layout.setSpacing(9)

        self.heading = QLabel("VOUS" if role == "user" else "JARVIS")
        self.heading.setStyleSheet("""
            QLabel { color: #36DDFB; font-size: 13px; font-weight: 750;
                background: transparent; border: none; letter-spacing: 1px; }
        """)
        self.layout.addWidget(self.heading)

        self.default_view = None
        self.last_markdown_view = None

    def _create_markdown_view(self):
        view = MarkdownWebView(self)
        view.open_content_requested.connect(self.open_content_requested)
        view.setFixedHeight(44)
        view.content_size_changed.connect(
            lambda width, height, v=view: self._on_view_size(v, width, height)
        )
        return view

    def _on_view_size(self, view, natural_width, height):
        self._view_sizes[view] = (natural_width, height)
        view.setFixedHeight(max(28, height))
        self._fit()
        self._fit()

    def set_markdown(self, markdown):
        if self.default_view is None:
            if markdown:
                self.default_view = self.add_markdown_block(markdown)
            return
        render_markdown(self.default_view, markdown)

    def add_markdown_block(self, markdown=""):
        view = self._create_markdown_view()
        self.layout.addWidget(view)
        self.markdown_views.append(view)
        if self.default_view is None:
            self.default_view = view
        self.last_markdown_view = view
        render_markdown(view, markdown)
        self._fit()
        return view

    def add_panel(self, title, content="", expanded=False, max_height=320):
        panel = CollapsiblePanel(title, content, expanded, max_height)
        panel.open_content_requested.connect(self.open_content_requested)
        self.layout.addWidget(panel)
        self.panels.append(panel)
        self._fit()
        return panel

    def add_chart(self,data):
        widget = ChartPreview(data, self)
        widget.open_requested.connect(
            lambda chart_data: self.open_content_requested.emit("graphique", chart_data)
        )
        widget.save_requested.connect(
            lambda chart_data: self.save_content_requested.emit("graphique", chart_data)
        )
        self.layout.addWidget(widget)
        self.extra_widgets.append(widget)
        self._fit()
        return widget

    def add_3d_model(self, model_data):
        widget = Inline3DViewer(model_data, self)
        widget.open_requested.connect(
            lambda data: self.open_content_requested.emit("modèle 3D", data)
        )
        self.layout.addWidget(widget)
        self.extra_widgets.append(widget)
        self._fit()
        return widget

    def add_attachments(self, attachments):
        for attachment in attachments:
            widget = ChatAttachmentCard(attachment, self)
            self.layout.addWidget(widget)
            self.extra_widgets.append(widget)
        self._fit()

    def set_available_width(self, width):
        self.available_width = max(0, int(width))
        self._fit()

    def _fit(self):
        if self._fitting or not hasattr(self, "layout"):
            return
        self._fitting = True
        try:
            max_width = max(
                0,
                int(self.available_width * (0.72 if self.role == "user" else 1.0))
            )
            natural_widths = [size[0] for size in self._view_sizes.values()]
            ideal_width = max(natural_widths, default=260)

            # Les blocs techniques occupent davantage d'espace ; les textes courts restent compacts.
            width = min(max(ideal_width + 48, min(300, max_width)), max_width)
            if self.panels:
                width = max(width, min(560, max_width))
            if self.role != "user":
                width = max_width  # la bulle du modèle occupe toujours toute la largeur
            self.setFixedWidth(width)
            content_width = max(0, width - 34)

            for view in self.markdown_views:
                if view.width() != content_width:
                    view.setFixedWidth(content_width)
                    QTimer.singleShot(0, view._measure_height)
            for panel in self.panels:
                panel.setFixedWidth(content_width)

                body_width = max(0, content_width - 16)
                panel.body.setFixedWidth(body_width)

                QTimer.singleShot(0, panel.body._measure_height)

                panel.refit()
            for widget in self.extra_widgets:
                widget.setFixedWidth(content_width)
            self.updateGeometry()
        finally:
            self._fitting = False


def tool_details_to_markdown(details):
    """Présente les structures d'outils lisiblement, sans perdre le Markdown texte."""
    if isinstance(details, (dict, list)):
        return "```json\n" + json.dumps(details, ensure_ascii=False, indent=2) + "\n```"

    text = str(details or "")
    stripped = text.strip()
    if stripped:
        try:
            parsed = json.loads(stripped)
        except (json.JSONDecodeError, TypeError):
            return text
        return "```json\n" + json.dumps(parsed, ensure_ascii=False, indent=2) + "\n```"
    return "_Aucun détail fourni._"
