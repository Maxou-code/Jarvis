import json

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
                             QToolButton, QVBoxLayout, QWidget)

from UI.chart_view import InlineChart
from UI.markdown_view import MarkdownWebView, render_markdown
from UI.viewer3d import Inline3DViewer

class CollapsiblePanel(QFrame):
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
        self.layout.addWidget(panel)
        self.panels.append(panel)
        self._fit()
        return panel

    def add_chart(self,data):
        widget=InlineChart(data); self.layout.addWidget(widget); self.extra_widgets.append(widget); self._fit(); return widget

    def add_3d_model(self, model_data):
        widget = Inline3DViewer(model_data, self)
        self.layout.addWidget(widget)
        self.extra_widgets.append(widget)
        self._fit()
        return widget

    def set_available_width(self, width):
        self.available_width = max(260, int(width))
        self._fit()

    def _fit(self):
        if self._fitting or not hasattr(self, "layout"):
            return
        self._fitting = True
        try:
            max_width = max(
                300,
                int(self.available_width * (0.72 if self.role == "user" else 1.0))
            )
            natural_widths = [size[0] for size in self._view_sizes.values()]
            ideal_width = max(natural_widths, default=260)

            # Les blocs techniques occupent davantage d'espace ; les textes courts restent compacts.
            width = min(max(ideal_width + 48, 300), max_width)
            if self.panels:
                width = max(width, min(560, max_width))
            if self.role != "user":
                width = max_width  # la bulle du modèle occupe toujours toute la largeur
            self.setFixedWidth(width)
            content_width = max(220, width - 34)

            for view in self.markdown_views:
                if view.width() != content_width:
                    view.setFixedWidth(content_width)
                    QTimer.singleShot(0, view._measure_height)
            for panel in self.panels:
                panel.setFixedWidth(content_width)

                body_width = max(180, content_width - 16)
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
