import re
from pathlib import Path

from PyQt6.QtCore import QEasingCurve, QRect, Qt, QTimer, QVariantAnimation, pyqtSignal
from PyQt6.QtGui import (
    QColor, QFont, QImage, QPainter, QSyntaxHighlighter, QTextCharFormat, QIcon,
)
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QMessageBox,
    QPlainTextEdit, QPushButton, QSizePolicy, QStackedWidget, QVBoxLayout,
    QWidget,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from pygments import lex
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.styles import get_style_by_name
from pygments.util import ClassNotFound

from UI.chart_view import InlineChart
from UI.viewer3d import Inline3DViewer


class CodeLineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return self.editor.line_number_area_size()

    def paintEvent(self, event):
        self.editor.paint_line_numbers(event)


class PygmentsHighlighter(QSyntaxHighlighter):
    def __init__(self, document, language):
        super().__init__(document)
        try:
            self.lexer = get_lexer_by_name(
                language or "text", stripnl=False, ensurenl=False
            )
        except ClassNotFound:
            self.lexer = TextLexer(stripnl=False, ensurenl=False)
        self.style = get_style_by_name("dracula")
        self._line_formats = []

    def refresh(self, text):
        self._line_formats = [[]]
        line_index = 0
        column = 0

        for token, value in lex(text, self.lexer):
            token_style = self.style.style_for_token(token)
            char_format = QTextCharFormat()
            if token_style.get("color"):
                char_format.setForeground(QColor(f"#{token_style['color']}"))
            if token_style.get("bold"):
                char_format.setFontWeight(QFont.Weight.Bold)
            if token_style.get("italic"):
                char_format.setFontItalic(True)
            if token_style.get("underline"):
                char_format.setFontUnderline(True)

            for segment in value.splitlines(keepends=True):
                visible = segment.rstrip("\r\n")
                if visible:
                    self._line_formats[line_index].append(
                        (column, len(visible), char_format)
                    )

                if segment.endswith(("\n", "\r")):
                    line_index += 1
                    column = 0
                    self._line_formats.append([])
                else:
                    column += len(segment)

        self.rehighlight()

    def highlightBlock(self, text):
        block_index = self.currentBlock().blockNumber()
        if block_index >= len(self._line_formats):
            return
        for start, length, char_format in self._line_formats[block_index]:
            self.setFormat(start, length, char_format)


class CodeEditor(QPlainTextEdit):
    def __init__(self, code, language, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFont(QFont("Cascadia Code", 10))
        self.setPlainText(code)

        self.line_number_area = CodeLineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.update_line_number_area_width()

        self.highlighter = PygmentsHighlighter(self.document(), language)
        self.highlighter.refresh(self.toPlainText())

    def line_number_area_size(self):
        digits = max(2, len(str(max(1, self.blockCount()))))
        width = 8 + self.fontMetrics().horizontalAdvance("9") * digits
        return QRect(0, 0, width, 0).size()

    def update_line_number_area_width(self, _block_count=None):
        self.setViewportMargins(self.line_number_area_size().width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(
                0, rect.y(), self.line_number_area.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        contents = self.contentsRect()
        width = self.line_number_area_size().width()
        self.line_number_area.setGeometry(
            QRect(contents.left(), contents.top(), width, contents.height())
        )

    def paint_line_numbers(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#081923"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(
            self.contentOffset()
        ).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor("#63838E"))
                painter.drawText(
                    0, top, self.line_number_area.width() - 5,
                    self.fontMetrics().height(), Qt.AlignmentFlag.AlignRight,
                    str(block_number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1


class RoundedWebView(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.page().setBackgroundColor(QColor("#07121B"))
        self.loadFinished.connect(self._apply_rounded_corners)

    def _apply_rounded_corners(self, _success):
        self.page().runJavaScript(
            "document.documentElement.style.clipPath = 'inset(0 round 4px)';"
        )


class PreviewPanel(QFrame):
    close_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("previewPanel")
        self.setMinimumWidth(300)
        self.setStyleSheet("""
            QFrame#previewPanel {
                background:#07121B;
                border-left:1px solid #145064;
            }
            QLabel#previewTitle {
                color:#43BFD5;
                font-size:12px;
                font-weight:700;
                letter-spacing:1px;
            }
            QPushButton {
                background:#102B38;
                color:#C8F5FF;
                border:1px solid #216078;
                border-radius:4px;
                padding:6px 12px;
                font-weight:600;
            }

            QPushButton:hover {
                background:#17485B;
            }
            
            QPushButton#saveButton {
                background:#123D32;
                border-color:#27865F;
                color:#A5F0C7;
            }
            QPushButton#saveButton:hover {
                background:#195641;
            }
                        
            QPushButton#visualizeButton {
                background:#102B38;
                color:#C8F5FF;
                border:1px solid #216078;
                border-radius:4px;
                padding:6px 12px;
                font-weight:600;
            }

            QPushButton#visualizeButton:hover {
                background:#17485B;
            }

            QPushButton#visualizeButton:checked {
                background:#00AFCF;
                border-color:#7CEEFF;
                color:#102B38;
            }            
            
            QPlainTextEdit {
                background:#050D14;
                color:#D7F8FF;
                border:1px solid #145064;
                border-radius:4px;
                padding:8px;
                font-family:"Cascadia Code","Consolas",monospace;
                font-size:12px;
            }
            QPlainTextEdit::corner { background:#081923; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        toolbar = QHBoxLayout()
        self.title = QLabel("APERÇU")
        self.title.setObjectName("previewTitle")
        toolbar.addWidget(self.title, 1)

        close_button = QPushButton()
        close_button.setIcon(QIcon("Icons/xmark-solid-full.svg"))
        close_button.setFixedSize(25, 25)
        close_button.setToolTip("Fermer le volet")
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.clicked.connect(lambda: self.close_requested.emit())
        toolbar.addWidget(close_button)
        layout.addLayout(toolbar)

        self.content_stack = QStackedWidget(self)
        layout.addWidget(self.content_stack, 1)
        self._active_kind = None
        self._active_data = None
        self._html_editor = None
        self._html_view = None

        self.copy_button = QPushButton()
        self.copy_button.setIcon(QIcon("Icons/copy-solid-full.svg"))
        self.copy_button.setToolTip("Copier")
        self.copy_button.setObjectName("copyButton")
        self.copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_button.clicked.connect(self._copy_code)
        self.copy_button.hide()
        toolbar.insertWidget(1, self.copy_button)

        self._copy_feedback_progress = 0.0
        self._copy_feedback_target = 0.0
        self._copy_feedback_animation = QVariantAnimation(self)
        self._copy_feedback_animation.setDuration(180)
        self._copy_feedback_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._copy_feedback_animation.valueChanged.connect(
            self._update_copy_feedback
        )
        self._copy_feedback_animation.finished.connect(
            self._finish_copy_feedback
        )
        self._copy_feedback_timer = QTimer(self)
        self._copy_feedback_timer.setSingleShot(True)
        self._copy_feedback_timer.timeout.connect(self._reset_copy_feedback)

        self.visualize_button = QPushButton()
        self.visualize_button.setIcon(QIcon("Icons/eye-solid-full.svg"))
        self.visualize_button.setToolTip("Visualiser")
        self.visualize_button.setObjectName("visualizeButton")
        self.visualize_button.setCheckable(True)
        self.visualize_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.visualize_button.toggled.connect(self._toggle_html_preview)
        self.visualize_button.hide()
        toolbar.insertWidget(2, self.visualize_button)

        self.save_button = QPushButton()
        self.save_button.setIcon(QIcon("Icons/download-solid-full.svg"))
        self.save_button.setToolTip("Enregistrer")
        self.save_button.setObjectName("saveButton")
        self.save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_button.clicked.connect(self._save_active_content)
        self.save_button.hide()
        toolbar.insertWidget(3, self.save_button)


    def show_content(self, kind, data):
        self._clear_content()
        self._active_kind = kind
        self._active_data = data

        if kind == "programme":
            code_data = data if isinstance(data, dict) else {"code": str(data)}
            code = str(code_data.get("code", ""))
            language = str(code_data.get("language", "text"))
            name = str(code_data.get("name", "")).strip()
            content = CodeEditor(code, language, self.content_stack)
            normalized_language = language.strip().lower()
            is_html = (
                normalized_language in {"html", "htm", "xhtml"}
                or Path(name).suffix.lower() in {".html", ".htm"}
            )
            if is_html:
                self._html_editor = content
                self._html_view = RoundedWebView(self.content_stack)
                self._html_view.setHtml(code)
                self.content_stack.addWidget(self._html_view)
                self.visualize_button.show()
            self.title.setText(name or language.upper() or "TEXTE")
            self.save_button.setVisible(True)
            self.copy_button.setVisible(True)
        elif kind == "graphique":
            content = InlineChart(data, self.content_stack)
            content.setMinimumHeight(0)
            content.setMaximumHeight(16777215)
            content.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding,
            )
            self.title.setText("GRAPHIQUE")
            self.save_button.setVisible(True)
            self.copy_button.hide()
        elif kind == "modèle 3D":
            content = Inline3DViewer(
                data, self.content_stack, show_open_button=False
            )
            content.setMinimumHeight(0)
            content.setMaximumHeight(16777215)
            content.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding,
            )
            self.title.setText("MODÈLE 3D")
            self.save_button.hide()
            self.copy_button.hide()
        else:
            raise ValueError(f"Type d'aperçu inconnu : {kind}")

        self.content_stack.addWidget(content)
        self.content_stack.setCurrentWidget(content)

    def _toggle_html_preview(self, checked):
        if self._html_editor is None or self._html_view is None:
            return

        target = self._html_view if checked else self._html_editor
        self.content_stack.setCurrentWidget(target)
        self.visualize_button.setToolTip(
            "Afficher le code" if checked else "Visualiser"
        )

    def _save_active_content(self):
        if self._active_kind == "programme":
            self._save_code()
        elif self._active_kind == "graphique":
            self._save_chart()

    def save_chart(self, data):
        self._active_kind = "graphique"
        self._active_data = data
        self._save_chart()

    def _save_code(self):
        data = self._active_data if isinstance(self._active_data, dict) else {}
        language = str(data.get("language", "text")).lower()
        extension = {
            "python": "py", "py": "py", "javascript": "js", "js": "js",
            "typescript": "ts", "json": "json", "html": "html", "css": "css",
            "java": "java", "c": "c", "cpp": "cpp", "c++": "cpp",
            "csharp": "cs", "c#": "cs", "sql": "sql", "bash": "sh",
            "sh": "sh", "powershell": "ps1", "rust": "rs", "go": "go",
            "yaml": "yaml", "xml": "xml",
        }.get(language, "txt")
        name = Path(str(data.get("name", "")).strip()).name
        if not name:
            name = f"programme.{extension}"
        elif not Path(name).suffix:
            name = f"{name}.{extension}"

        destination, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer le programme", name,
            f"Fichier de code (*.{extension});;Tous les fichiers (*)",
        )
        if not destination:
            return

        target = Path(destination)
        if not target.suffix:
            target = target.with_suffix(f".{extension}")
        try:
            target.write_text(str(data.get("code", "")), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(
                self, "Enregistrement impossible", str(exc)
            )

    def _copy_code(self):
        data = self._active_data if isinstance(self._active_data, dict) else {}
        QApplication.clipboard().setText(str(data.get("code", "")))
        self.copy_button.setIcon(QIcon("Icons/copy-regular-full.svg"))
        self._animate_copy_feedback(1.0)
        self._copy_feedback_timer.start(1500)

    def _animate_copy_feedback(self, target):
        self._copy_feedback_animation.stop()
        self._copy_feedback_target = target
        self._copy_feedback_animation.setStartValue(self._copy_feedback_progress)
        self._copy_feedback_animation.setEndValue(target)
        self._copy_feedback_animation.start()

    def _update_copy_feedback(self, value):
        self._copy_feedback_progress = float(value)
        base_background = QColor("#0A202B")
        copied_background = QColor("#183D2B")
        base_border = QColor("#145064")
        copied_border = QColor("#2E9D62")

        def blend(start, end):
            progress = self._copy_feedback_progress
            return QColor(
                round(start.red() + (end.red() - start.red()) * progress),
                round(start.green() + (end.green() - start.green()) * progress),
                round(start.blue() + (end.blue() - start.blue()) * progress),
            )

        background = blend(base_background, copied_background)
        border = blend(base_border, copied_border)
        self.copy_button.setStyleSheet(
            "QPushButton#copyButton {"
            f"background-color: {background.name()};"
            f"border-color: {border.name()};"
            "}"
        )

    def _finish_copy_feedback(self):
        if self._copy_feedback_target == 0.0:
            self.copy_button.setStyleSheet("")

    def _reset_copy_feedback(self):
        self.copy_button.setIcon(QIcon("Icons/copy-solid-full.svg"))
        self._animate_copy_feedback(0.0)

    def _save_chart(self):
        data = self._active_data if isinstance(self._active_data, dict) else {}
        title = re.sub(
            r'[<>:"/\\|?*\x00-\x1f]', "_",
            str(data.get("title", "graphique")).strip(),
        ).strip(" .")
        default_name = f"{title or 'graphique'}.png"
        destination, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer le graphique", default_name, "Image PNG (*.png)"
        )
        if not destination:
            return

        target = Path(destination)
        if target.suffix.lower() != ".png":
            target = target.with_suffix(".png")

        image = QImage(1920, 1080, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(QColor("#06111A"))
        chart = InlineChart(data)
        chart.setMinimumHeight(0)
        chart.setMaximumHeight(16777215)
        chart.resize(image.size())
        chart.ensurePolished()
        painter = QPainter(image)
        chart.render(painter)
        painter.end()

        if not image.save(str(target), "PNG"):
            QMessageBox.warning(
                self, "Enregistrement impossible",
                f"Impossible d'enregistrer l'image : {target}",
            )
        chart.deleteLater()

    def _clear_content(self):
        while self.content_stack.count():
            content = self.content_stack.widget(0)
            self.content_stack.removeWidget(content)
            if isinstance(content, Inline3DViewer):
                content.close_renderer()
            content.deleteLater()
        self._active_kind = None
        self._active_data = None
        self._html_editor = None
        self._html_view = None
        self.visualize_button.setChecked(False)
        self.visualize_button.setToolTip("Visualiser")
        self.save_button.hide()
        self.copy_button.hide()
        self.visualize_button.hide()

    def clear_content(self):
        self._clear_content()
