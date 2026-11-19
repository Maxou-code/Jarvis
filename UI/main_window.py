import ctypes
import sys
import ast
import math
from datetime import datetime

# IMPORTANT : régler le DPI avant d'importer PyAutoGUI.
try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(
        ctypes.c_void_p(-4)  # PER_MONITOR_AWARE_V2
    )
except Exception:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

import base64
import io
import json
import os
import re
import sqlite3
import subprocess
import ctypes
import time
import traceback
import html as html_lib
from ctypes import wintypes
from pathlib import Path

# Interface graphique
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer, QUrl, QSize, QEvent
from PyQt6.QtGui import QColor, QPainter, QPen, QFont, QFontMetrics, QPixmap, QDesktopServices, QIcon, QSurfaceFormat, QImage
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QScrollArea, QFrame,
    QSizePolicy, QFileDialog, QToolButton, QListWidget, QListWidgetItem,
    QMessageBox, QDialog, QDialogButtonBox, QGridLayout, QInputDialog, QMenu,
    QSplitter
)

from PyQt6.QtWebEngineWidgets import QWebEngineView

from winotify import Notification, audio

import pyautogui
import requests
import mss

from PIL import Image

# Rendu Markdown fidèle (CommonMark, retours à la ligne, tableaux, code).
# Installation : pip install markdown-it-py
try:
    from markdown_it import MarkdownIt
    from pygments import highlight as pygments_highlight
    from pygments.lexers import get_lexer_by_name
    from pygments.formatters import HtmlFormatter

    # Configuration du thème syntaxique
    _PYGMENTS_FORMATTER = HtmlFormatter(
        style="dracula",
        nowrap=True
    )


    def highlight_code(code, language, attrs):
        if not language:
            return ""

        try:
            lexer = get_lexer_by_name(language)
            return pygments_highlight(
                code,
                lexer,
                _PYGMENTS_FORMATTER
            )
        except Exception:
            # Langage inconnu : affichage normal
            return ""


    _MD = MarkdownIt(
        "commonmark",
        {
            "breaks": True,
            "html": False,
            "highlight": highlight_code
        }
    ).enable(["table", "strikethrough"])

except ImportError:
    _MD = None
    _PYGMENTS_FORMATTER = None

import html

from config import (
    CONTENT_MAX_WIDTH,
    CONTENT_SIDE_MARGIN,
    ENTRY_MAX_WIDTH,
    MAX_ERROR_DETAILS,
    MODEL,
    WORKSPACE,
)
from Core.agent import set_conversation_history
from Core.conversations import ConversationStore
from Core.paths import register_authorized_directory
from UI.chart_view import InlineChart
from UI.markdown_view import MarkdownWebView, render_markdown
from UI.preview_panel import PreviewPanel
from UI.viewer3d import Inline3DViewer
from UI.widgets import MarkdownMessage, tool_details_to_markdown
from UI.worker import AgentWorker


class ConversationListWidget(QListWidget):
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            event.accept()
            return
        super().mousePressEvent(event)


class JarvisWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"JARVIS // THE GRID  |  {MODEL}")
        self.resize(1180, 820)
        self.setMinimumSize(760, 600)
        self.worker_thread = None
        self.worker = None
        self.current_assistant_bubble = None
        self.current_response = ""
        self._response_recorded = False
        self.current_response_view = None
        self.current_thinking_panel = None
        self.current_thinking = ""
        self._thinking_recorded = False
        self._rendered_response = None
        self._rendered_thinking = None
        self._markdown_timer = QTimer(self)
        self._markdown_timer.setInterval(160)
        self._markdown_timer.timeout.connect(self._flush_live_markdown)
        self.attachments = []
        self.message_widgets = []
        self.conversation_store = ConversationStore(WORKSPACE / "conversations.sqlite3")
        self.current_conversation = None

        self.setStyleSheet("""
            QMainWindow, QWidget#root {
                background: #050B12;
                color: #D7F8FF;
                font-family: "Segoe UI";
            }
            QWidget#messagesHost, QWidget#container { background: #050B12; }

            QFrame#topbar {
                background: #07121B;
                border: none;
                border-bottom: 1px solid #087C9A;
            }
            QFrame#historySidebar {
                background: #07121B;
                border-right: 1px solid #145064;
            }
            QLabel#historyTitle {
                color: #43BFD5;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 2px;
            }
            QListWidget#historyList {
                background: transparent;
                border: none;
                color: #A6D3DC;
                outline: none;
            }
            QListWidget#historyList::item {
                background: #0A202B;
                border: 1px solid #145064;
                border-radius: 4px;
                padding: 10px 9px;
                margin: 3px 0;
            }
            QListWidget#historyList::item:hover {
                background: #103746;
                border-color: #20A9C8;
                color: #FFFFFF;
            }
            QListWidget#historyList::item:selected {
                background: #103746;
                border-color: #20A9C8;
                color: #FFFFFF;
            }
            QLabel#brand {
                color: #DDFBFF;
                font-size: 25px;
                font-weight: 800;
                letter-spacing: 5px;
            }
            QLabel#sub {
                color: #43BFD5;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 2px;
            }
            QLabel#status {
                color: #F6A94A;
                font-size: 12px;
                font-weight: 700;
                padding: 8px 14px;
                background: #091A24;
                border: 1px solid #145064;
                border-radius: 5px;
            }

            QFrame#userBubble {
                background: #0A202B;
                border: 1px solid #087C9A;
                border-radius: 5px;
            }
            QFrame#assistantBubble {
                background: #081923;
                border: 1px solid #123B4A;
                border-radius: 5px;
            }
            QFrame#collapsePanel {
                background: #071720;
                border: 1px solid #145064;
                border-radius: 4px;
            }
            QWidget#bottomWidget {
                background: transparent;
                border: none;
            }
            QFrame#composer {
                background: transparent;
                border: 1px solid #00AFCF;
                border-radius: 7px;
            }
            QTextEdit#input {
                background: transparent;
                border: none;
                color: #E4FCFF;
                font-size: 15px;
                padding: 8px 6px;
                selection-background-color: #087C9A;
            }
            QTextEdit#input:focus { border: none; }

            QPushButton#send {
                background: #00BFEA;
                color: #031018;
                border: 1px solid #7CEEFF;
                border-radius: 4px;
                min-width: 42px;
                min-height: 42px;
                font-size: 21px;
                font-weight: 800;
            }
            QPushButton#send:hover {
                background: #38DDFB;
                border: 1px solid #C0FAFF;
            }
            QPushButton#send:pressed { background: #087C9A; }
            QPushButton#send:disabled {
                background: #102B38;
                color: #55717D;
                border-color: #164456;
            }

            QPushButton#reflectionToggle {
                background: #102B38;
                color: #55717D;
                border: 1px solid #145064;
                border-radius: 4px;
                min-width: 42px;
                min-height: 42px;
                font-size: 21px;
                font-weight: 800;
            }
            QPushButton#reflectionToggle:hover {
                background: #103746;
                border-color: #20A9C8;
            }
            QPushButton#reflectionToggle:checked {
                background: #00AFCF;
                color: #031018;
                border-color: #7CEEFF;
            }
            QPushButton#reflectionToggle:checked:hover {
                background: #38DDFB;
                border-color: #C0FAFF;
            }

            QPushButton#attach, QPushButton#clear {
                background: #0A202B;
                color: #8DEEFF;
                border: 1px solid #145064;
                border-radius: 4px;
                min-width: 42px;
                min-height: 42px;
                font-size: 20px;
                font-weight: 700;
            }
            QPushButton#attach:hover, QPushButton#clear:hover {
                background: #103746;
                color: #FFFFFF;
                border: 1px solid #20A9C8;
            }
            QPushButton#attach:pressed, QPushButton#clear:pressed {
                background: #07121B;
            }
            QPushButton {
                outline: none;
            }

            QListWidget {
                background: transparent;
                border: none;
                color: #A6D3DC;
                outline: none;
            }
            QListWidget::item {
                background: #0A202B;
                border: 1px solid #145064;
                border-radius: 4px;
                padding: 8px 12px;
                margin-right: 7px;
            }
            QListWidget::item:selected { background: #103746; }

            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 5px 2px;
            }
            QScrollBar::handle:vertical {
                background: #145064;
                border-radius: 3px;
                min-height: 35px;
            }
            QScrollBar::handle:vertical:hover { background: #20A9C8; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QToolTip {
                background: #071720;
                color: #D7F8FF;
                border: 1px solid #00AFCF;
                padding: 5px;
            }
        """)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)

        # Vue WebEngine de « préchauffage », présente dès l'ouverture de la fenêtre.
        # Ajouter le PREMIER QWebEngineView dans une fenêtre déjà affichée force Qt à
        # recréer la fenêtre native (elle se ferme et se rouvre). Avec cette vue, la
        # fenêtre est créée une seule fois avec le bon type de surface, et Chromium est
        # déjà démarré quand le premier message arrive.
        self._warmup_view = MarkdownWebView(root)
        self._warmup_view.setGeometry(0, 0, 2, 2)
        self._warmup_view.set_markdown("")
        self._warmup_view.lower()
        # Grille superposée : la zone de discussion occupe toute la hauteur
        # disponible et le composeur flotte au-dessus, en bas de la fenêtre.
        main = QGridLayout(root)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        top = QFrame()
        top.setObjectName("topbar")
        top.setFixedHeight(72)
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(28, 12, 28, 12)
        self.history_button = QPushButton("☰")
        self.history_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.history_button.setToolTip("Afficher ou masquer l'historique")
        self.history_button.setStyleSheet(
            "QPushButton { background:#0B202B; color:#C6F7FF; border:1px solid #176078; "
            "border-radius:4px; padding:8px 12px; font-size:18px; } "
            "QPushButton:hover { background:#103746; }"
        )
        self.history_button.clicked.connect(self.toggle_history)
        top_layout.addWidget(self.history_button)
        top_layout.addSpacing(16)

        identity = QVBoxLayout()
        identity.setSpacing(1)
        brand = QLabel("JARVIS")
        brand.setObjectName("brand")
        sub = QLabel(f"THE GRID  //  LOCAL NEURAL CORE  //  {MODEL}")
        sub.setObjectName("sub")
        identity.addWidget(brand)
        identity.addWidget(sub)
        top_layout.addLayout(identity)

        top_layout.addStretch()

        self.folder_button = QPushButton("Dossiers autorisés")
        self.folder_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.folder_button.setToolTip("Ajouter un dossier accessible à JARVIS")
        self.folder_button.setStyleSheet("QPushButton { background:#0B202B; color:#C6F7FF; border:1px solid #176078; border-radius:4px; padding:8px 12px; } QPushButton:hover { background:#35485F; }")
        self.folder_button.clicked.connect(self.authorize_folder)
        top_layout.addWidget(self.folder_button)
        self.status = QLabel("●  Prêt")
        self.status.setStyleSheet("color: #70D9A6;")
        self.status.setObjectName("status")
        self.status.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Maximum
        )
        top_layout.addWidget(self.status)

        self.history_sidebar = QFrame()
        self.history_sidebar.setObjectName("historySidebar")
        self.history_sidebar.setFixedWidth(270)
        history_layout = QVBoxLayout(self.history_sidebar)
        history_layout.setContentsMargins(14, 18, 14, 14)
        history_layout.setSpacing(12)
        history_heading = QLabel("CONVERSATIONS")
        history_heading.setObjectName("historyTitle")
        history_layout.addWidget(history_heading)
        self.new_conversation_button = QPushButton("Nouvelle conversation")
        self.new_conversation_button.setIcon(QIcon("Icons/plus-solid-full.svg"))
        self.new_conversation_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_conversation_button.setStyleSheet(
            "QPushButton { background:#0A202B; color:#8DEEFF; border:1px solid #145064; "
            "border-radius:4px; padding:9px; text-align:left; } "
            "QPushButton:hover { background:#103746; border-color:#20A9C8; }"
        )
        self.new_conversation_button.clicked.connect(self.new_conversation)
        history_layout.addWidget(self.new_conversation_button)
        self.history_list = ConversationListWidget()
        self.history_list.setObjectName("historyList")
        self.history_list.setCursor(Qt.CursorShape.PointingHandCursor)
        self.history_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(self.show_conversation_menu)
        self.history_list.currentItemChanged.connect(self.open_conversation)
        history_layout.addWidget(self.history_list, 1)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        host = QWidget()
        host.setObjectName("messagesHost")
        host.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        host_layout = QHBoxLayout(host)
        host_layout.setContentsMargins(0, 0, 0, 0)
        host_layout.addStretch(1)

        messages_column = QWidget(host)
        messages_column.setObjectName("messagesColumn")
        messages_column.setMinimumWidth(0)
        messages_column.setMaximumWidth(CONTENT_MAX_WIDTH)
        messages_column.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        self.messages_layout = QVBoxLayout(messages_column)
        self.messages_layout.setContentsMargins(CONTENT_SIDE_MARGIN, 24, CONTENT_SIDE_MARGIN, 24)
        self.messages_layout.setSpacing(14)
        self.messages_layout.addStretch(1)
        host_layout.addWidget(messages_column, 10000)
        host_layout.addStretch(1)
        self.messages_host = messages_column

        self.scroll.setWidget(host)

        # Défilement automatique tant que l'utilisateur reste en bas.
        self._autoscroll = True
        scroll_bar = self.scroll.verticalScrollBar()
        scroll_bar.rangeChanged.connect(self._on_scroll_range_changed)
        scroll_bar.valueChanged.connect(self._on_scroll_value_changed)

        # Barre d'entrée : sur sa propre ligne tout en bas, même fond que la conversation,
        # sans trait de séparation. La zone de discussion s'arrête à son bord supérieur :
        # le texte disparaît « sous » la barre et aucune vue web ne peut passer devant.
        bottom = QWidget()
        bottom.setObjectName("bottomWidget")
        bottom.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        bottom.setStyleSheet("QWidget#bottomWidget { border: none; }")
        bottom_layout = QVBoxLayout(bottom)
        self.bottom_layout = bottom_layout
        # Marge droite +14 : même bord droit que les bulles (qui réservent la barre de défilement).
        bottom_layout.setContentsMargins(CONTENT_SIDE_MARGIN, 12, CONTENT_SIDE_MARGIN, 12)
        bottom_layout.setSpacing(10)

        self.file_row = QListWidget()
        self.file_row.setObjectName("attachmentRow")
        self.file_row.setMaximumHeight(92)
        self.file_row.setMinimumHeight(76)
        self.file_row.setFlow(QListWidget.Flow.LeftToRight)
        self.file_row.setWrapping(False)
        self.file_row.setSpacing(7)
        self.file_row.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.file_row.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.file_row.setStyleSheet("""
            QListWidget#attachmentRow { background: transparent; border: none; color: #A6D3DC; }
            QListWidget#attachmentRow::item { background: transparent; border: none; padding: 0; }
            QListWidget#attachmentRow QScrollBar:horizontal { height: 7px; background: transparent; }
            QListWidget#attachmentRow QScrollBar::handle:horizontal { background: #53657B; border-radius: 3px; }
        """)
        self.file_row.hide()
        bottom_layout.addWidget(self.file_row)

        composer = QFrame()
        composer.setObjectName("composer")
        composer_layout = QHBoxLayout(composer)
        composer_layout.setContentsMargins(12, 10, 10, 10)
        composer_layout.setSpacing(12)

        self.attach_button = QPushButton()
        self.attach_button.setIcon(QIcon("Icons/paperclip-solid-full.svg"))
        self.attach_button.setIconSize(QSize(22, 22))
        self.attach_button.setObjectName("attach")
        self.attach_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.attach_button.setToolTip("Joindre un fichier")
        self.attach_button.clicked.connect(self.pick_files)
        composer_layout.addWidget(self.attach_button)

        self.scroll_button = QPushButton()
        self.scroll_button.setIcon(QIcon("Icons/arrow-down-solid-full.svg"))
        self.scroll_button.setIconSize(QSize(22, 22))
        self.scroll_button.setObjectName("attach")
        self.scroll_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scroll_button.setToolTip("Faire défiler la conversation")
        self.scroll_button.clicked.connect(lambda: self.scroll_to_bottom(force=True))
        composer_layout.addWidget(self.scroll_button)

        self.input = QTextEdit()
        self.input.setObjectName("input")
        self.input.setPlaceholderText("Écrivez un message à JARVIS…")
        self.input.setAcceptRichText(False)
        self.input.setMinimumHeight(48)
        self.input.setMaximumHeight(130)
        self.input.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )
        self.input.installEventFilter(self)
        composer_layout.addWidget(self.input, 1)

        self.reflection_button = QPushButton()
        self.reflection_button.setIcon(QIcon("Icons/brain-solid-full.svg"))
        self.reflection_button.setIconSize(QSize(22, 22))
        self.reflection_button.setObjectName("reflectionToggle")
        self.reflection_button.setCheckable(True)
        self.reflection_button.setChecked(True)
        self.reflection_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reflection_button.setToolTip("Désactiver la réflexion du modèle")
        self.reflection_button.toggled.connect(
            lambda enabled: self.reflection_button.setToolTip(
                "Désactiver la réflexion du modèle"
                if enabled else "Activer la réflexion du modèle"
            )
        )
        composer_layout.addWidget(self.reflection_button)

        self.send_button = QPushButton()
        self.send_button.setIcon(QIcon("Icons/paper-plane-regular-full.svg"))
        self.send_button.setIconSize(QSize(22, 22))
        self.send_button.setObjectName("send")
        self.send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_button.clicked.connect(self.send_message)
        composer_layout.addWidget(self.send_button)
        # Barre centrée, largeur max ENTRY_MAX_WIDTH (même largeur que la conversation).
        composer.setMaximumWidth(ENTRY_MAX_WIDTH)
        composer_row = QHBoxLayout()
        composer_row.setContentsMargins(0, 0, 0, 0)
        composer_row.addStretch(1)
        composer_row.addWidget(composer, 10000)
        composer_row.addStretch(1)
        bottom_layout.addLayout(composer_row)

        conversation_area = QWidget(root)
        conversation_layout = QVBoxLayout(conversation_area)
        conversation_layout.setContentsMargins(0, 0, 0, 0)
        conversation_layout.setSpacing(0)
        conversation_layout.addWidget(self.scroll, 1)
        conversation_layout.addWidget(bottom)

        self.preview_panel = PreviewPanel(root)
        self.preview_panel.close_requested.connect(self.close_preview)
        self.preview_panel.hide()

        self.preview_splitter = QSplitter(Qt.Orientation.Horizontal, root)
        self.preview_splitter.setObjectName("previewSplitter")
        self.preview_splitter.setHandleWidth(5)
        self.preview_splitter.setStyleSheet(
            "QSplitter#previewSplitter::handle:horizontal { background:#145064; }"
        )
        self.preview_splitter.addWidget(conversation_area)
        self.preview_splitter.addWidget(self.preview_panel)
        self.preview_splitter.setStretchFactor(0, 1)
        self.preview_splitter.setStretchFactor(1, 0)
        self.preview_splitter.setCollapsible(0, False)
        self.preview_splitter.setCollapsible(1, True)
        self.preview_splitter.splitterMoved.connect(
            lambda _position, _index: QTimer.singleShot(
                0, self._refresh_content_widths
            )
        )

        main.addWidget(top, 0, 0, 1, 2)
        main.addWidget(self.history_sidebar, 1, 0, 2, 1)
        main.addWidget(self.preview_splitter, 1, 1, 2, 1)

        self.bottom_widget = bottom
        self.composer = composer

        main.setRowStretch(0, 0)
        main.setRowStretch(1, 1)
        main.setRowStretch(2, 0)
        main.setColumnStretch(0, 0)
        main.setColumnStretch(1, 1)

        self._activate_conversation(self.conversation_store.create())

    def toggle_history(self):
        self.history_sidebar.setVisible(not self.history_sidebar.isVisible())
        QTimer.singleShot(0, self._refresh_content_widths)

    def open_preview(self, kind, data):
        sizes = self.preview_splitter.sizes()
        was_collapsed = self.preview_panel.isHidden() or not sizes or sizes[1] == 0
        self.preview_panel.show_content(kind, data)
        self.preview_panel.show()
        if was_collapsed:
            total_width = self.preview_splitter.width()
            panel_width = min(520, max(320, total_width // 3))
            self.preview_splitter.setSizes(
                [max(300, total_width - panel_width), panel_width]
            )
        QTimer.singleShot(0, self._refresh_content_widths)

    def save_inline_content(self, kind, data):
        if kind == "graphique":
            self.preview_panel.save_chart(data)

    def close_preview(self):
        self.preview_panel.clear_content()
        self.preview_panel.hide()
        QTimer.singleShot(0, self._refresh_content_widths)

    def _refresh_conversation_list(self):
        selected_id = self.current_conversation["id"] if self.current_conversation else None
        self.history_list.blockSignals(True)
        self.history_list.clear()
        selected_item = None
        for conversation in self.conversation_store.list_conversations():
            width = min(
                self.history_list.viewport().width(),
                self.history_sidebar.width() - 28,
            ) - 36
            title = QFontMetrics(self.history_list.font()).elidedText(
                conversation["title"],
                Qt.TextElideMode.ElideRight,
                max(80, width),
            )
            item = QListWidgetItem(title)
            item.setToolTip(conversation["title"])
            item.setData(Qt.ItemDataRole.UserRole, conversation["id"])
            self.history_list.addItem(item)
            if conversation["id"] == selected_id:
                selected_item = item
        if selected_item is not None:
            self.history_list.setCurrentItem(selected_item)
        self.history_list.blockSignals(False)

    def show_conversation_menu(self, position):
        item = self.history_list.itemAt(position)
        if item is None:
            return
        conversation_id = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        rename_action = menu.addAction("Renommer")
        delete_action = menu.addAction("Supprimer")
        action = menu.exec(self.history_list.mapToGlobal(position))
        if action == rename_action:
            self.rename_conversation(conversation_id)
        elif action == delete_action:
            self.delete_conversation(conversation_id)

    def rename_conversation(self, conversation_id):
        conversation = self.conversation_store.get(conversation_id)
        if conversation is None:
            return
        title, accepted = QInputDialog.getText(
            self,
            "Renommer la conversation",
            "Nouveau nom :",
            text=conversation["title"],
        )
        if not accepted or not title.strip():
            return
        try:
            title = self.conversation_store.rename(conversation_id, title)
        except (sqlite3.Error, KeyError, ValueError) as exc:
            QMessageBox.warning(self, "Renommage impossible", str(exc))
            return
        if self.current_conversation["id"] == conversation_id:
            self.current_conversation["title"] = title
        self._refresh_conversation_list()

    def delete_conversation(self, conversation_id):
        conversation = self.conversation_store.get(conversation_id)
        if conversation is None:
            return
        answer = QMessageBox.question(
            self,
            "Supprimer la conversation",
            f"Supprimer « {conversation['title']} » ? Cette action est irréversible.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.conversation_store.delete(conversation_id)
        except (sqlite3.Error, KeyError) as exc:
            QMessageBox.warning(self, "Suppression impossible", str(exc))
            return
        if self.current_conversation["id"] == conversation_id:
            self._activate_conversation(self.conversation_store.create())
        else:
            self._refresh_conversation_list()

    def _activate_conversation(self, conversation):
        if conversation is None:
            return
        self.current_conversation = conversation
        set_conversation_history(conversation["messages"])
        self.input.clear()
        self.attachments.clear()
        self._refresh_attachment_row()
        self._clear_messages()
        for message in conversation["messages"]:
            role = message.get("role")
            if role == "user":
                self.current_assistant_bubble = None
                self.add_message(message["content"], "user")
            elif role == "assistant":
                self.ensure_assistant_bubble().add_markdown_block(message["content"])
            elif role == "thinking":
                panel = self.ensure_assistant_bubble().add_panel(
                    "Réflexion du modèle", expanded=True, max_height=None
                )
                panel.set_markdown(message["content"])
            elif role == "system":
                self.add_system_panel(
                    message["title"], message["details"],
                    expanded=message.get("expanded", False),
                )
            elif role == "chart":
                self.ensure_assistant_bubble().add_chart(message["data"])
            elif role == "model3d":
                try:
                    self.ensure_assistant_bubble().add_3d_model(message["data"])
                except Exception as exc:
                    self.add_system_panel("Affichage 3D impossible", str(exc), expanded=True)
        self._refresh_conversation_list()
        for index in range(self.history_list.count()):
            item = self.history_list.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == conversation["id"]:
                self.history_list.setCurrentItem(item)
                break

    def _clear_messages(self):
        self.close_preview()
        self._markdown_timer.stop()
        self.current_assistant_bubble = None
        self.current_response = ""
        self._response_recorded = False
        self.current_response_view = None
        self.current_thinking_panel = None
        self.current_thinking = ""
        self._thinking_recorded = False
        self._rendered_response = None
        self._rendered_thinking = None
        self.message_widgets.clear()
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                item.layout().deleteLater()
        self.scroll_to_bottom(force=True)

    def new_conversation(self):
        conversation = self.conversation_store.create()
        self._activate_conversation(conversation)

    def open_conversation(self, current, _previous=None):
        if current is None or self.current_conversation is None:
            return
        conversation_id = current.data(Qt.ItemDataRole.UserRole)
        if conversation_id == self.current_conversation["id"]:
            return
        conversation = self.conversation_store.get(conversation_id)
        if conversation is not None:
            self._activate_conversation(conversation)

    def authorize_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Autoriser un dossier pour JARVIS", str(Path.home()))
        if not folder: return
        try:
            info = register_authorized_directory(folder)
            QMessageBox.information(self, "Dossier autorisé", f"JARVIS peut maintenant accéder à :\n{info['path']}\n\nAlias : {info['alias']}/")
        except Exception as exc:
            QMessageBox.warning(self, "Autorisation impossible", str(exc))

    def eventFilter(self, obj, event):
        if obj is self.input and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    return False
                self.send_message()
                return True
        return super().eventFilter(obj, event)

    def _available_bubble_width(self):
        """Largeur utilisable par les bulles, indépendante de la barre de défilement."""
        host_width = min(
            self.messages_host.maximumWidth(),
            self.scroll.viewport().width(),
        )
        margins = self.messages_layout.contentsMargins()
        return max(0, host_width - margins.left() - margins.right())

    def _update_bubble_width(self):
        available = self._available_bubble_width()
        for bubble in self.message_widgets:
            bubble.set_available_width(available)

    def _refresh_content_widths(self):
        column_width = min(CONTENT_MAX_WIDTH, self.scroll.viewport().width())
        if self.messages_host.width() != column_width:
            self.messages_host.setFixedWidth(column_width)
        self._update_bubble_width()
        self._sync_bar_margins()

    def _sync_bar_margins(self):
        """Aligne le bord droit de la barre d'entrée sur celui des bulles."""
        if not hasattr(self, "bottom_layout"):
            return
        scroll_bar = self.scroll.verticalScrollBar()
        bar_width = scroll_bar.width() if scroll_bar.isVisible() else 0
        host_full = self.scroll.viewport().width() <= CONTENT_MAX_WIDTH
        extra = 8 if host_full else bar_width
        margins = self.bottom_layout.contentsMargins()
        wanted = CONTENT_SIDE_MARGIN + extra
        if margins.right() != wanted:
            self.bottom_layout.setContentsMargins(
                margins.left(), margins.top(), wanted, margins.bottom()
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self._refresh_content_widths)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._refresh_content_widths)

    def _on_scroll_range_changed(self, _minimum, maximum):
        if self._autoscroll:
            self.scroll.verticalScrollBar().setValue(maximum)
        # L'apparition de la barre verticale réduit aussi la largeur des bulles.
        QTimer.singleShot(0, self._refresh_content_widths)

    def _on_scroll_value_changed(self, value):
        bar = self.scroll.verticalScrollBar()
        self._autoscroll = value >= bar.maximum() - 24

    def add_message(self, text, role):
        bubble = MarkdownMessage(role)
        bubble.open_content_requested.connect(self.open_preview)
        bubble.save_content_requested.connect(self.save_inline_content)
        self.message_widgets.append(bubble)
        bubble.set_available_width(self._available_bubble_width())
        bubble.set_markdown(text)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        if role == "user":
            row.addStretch(1)
            row.addWidget(bubble, 0)
        else:
            row.addWidget(bubble, 0)
            row.addStretch(1)
        self.messages_layout.insertLayout(max(0, self.messages_layout.count() - 1), row)
        self.scroll_to_bottom(force=(role == "user"))
        return bubble

    def ensure_assistant_bubble(self):
        if self.current_assistant_bubble is None:
            self.current_assistant_bubble = self.add_message("", "assistant")
            self.current_response_view = None
        return self.current_assistant_bubble

    def add_system_panel(self, title, details, expanded=False):
        bubble = self.ensure_assistant_bubble()
        panel = bubble.add_panel(title, expanded=expanded)
        if isinstance(details, (dict, list)):
            details = json.dumps(details, ensure_ascii=False, indent=2)
        panel.set_markdown(tool_details_to_markdown(details)[:MAX_ERROR_DETAILS])
        self.scroll_to_bottom()
        return panel

    def scroll_to_bottom(self, force=False):
        if force:
            self._autoscroll = True

        bar = self.scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _is_image_attachment(self, path):
        return Path(path).suffix.lower() in {
            ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"
        }

    def _format_file_size(self, size):
        if size < 1024:
            return f"{size} o"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} Ko"
        return f"{size / (1024 * 1024):.1f} Mo"

    def _refresh_attachment_row(self):
        self.file_row.clear()
        for index, attachment in enumerate(self.attachments):
            path = Path(attachment["path"])
            try:
                size_text = self._format_file_size(path.stat().st_size)
            except OSError:
                size_text = "Fichier introuvable"

            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, index)
            self.file_row.addItem(item)

            card = QFrame()
            card.setObjectName("attachmentCard")
            card.setFixedSize(310, 66)
            card.setStyleSheet("""
                QFrame#attachmentCard {
                    background: #081923;
                    border: 1px solid #145064;
                    border-radius: 9px;
                }
                QLabel { color: #DCE6F3; border: none; background: transparent; }
                QPushButton {
                    background: #0D2A37; color: #C9D7E8;
                    border: 1px solid #176078; border-radius: 6px;
                    padding: 4px 7px; min-width: 22px; max-width: 28px;
                }
                QPushButton:hover { background: #145064; color: white; }
                QPushButton#removeAttachment {
                    color: #FF9B82; font-weight: 700;
                }
                QPushButton#removeAttachment:hover { background: #542A20; }
            """)
            row = QHBoxLayout(card)
            row.setContentsMargins(7, 5, 7, 5)
            row.setSpacing(7)

            preview = QLabel()
            preview.setFixedSize(48, 48)
            preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
            preview.setStyleSheet("background:#0A202B; border-radius:6px;")
            if self._is_image_attachment(path) and path.is_file():
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    preview.setPixmap(pixmap.scaled(
                        46, 46,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    ))
                else:
                    preview.setText("IMG")
            else:
                suffix = path.suffix.upper().lstrip(".")[:5] or "FILE"
                preview.setText(suffix)
            row.addWidget(preview)

            info = QVBoxLayout()
            info.setSpacing(2)
            name_label = QLabel(path.name)
            name_label.setToolTip(str(path))
            name_label.setMaximumWidth(125)
            name_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            size_label = QLabel(size_text)
            size_label.setStyleSheet("color:#76AAB7; font-size:10px;")
            info.addWidget(name_label)
            info.addWidget(size_label)
            row.addLayout(info, 1)

            preview_button = QPushButton("Voir" if self._is_image_attachment(path) else "Ouvrir")
            preview_button.setToolTip("Afficher l'image" if self._is_image_attachment(path) else "Ouvrir avec l'application par défaut")
            preview_button.clicked.connect(
                lambda checked=False, i=index: self.preview_attachment(i)
                if self._is_image_attachment(self.attachments[i]["path"])
                else self.open_attachment(i)
            )
            row.addWidget(preview_button)

            download_button = QPushButton("↓")
            download_button.setToolTip("Enregistrer une copie dans un autre dossier")
            download_button.clicked.connect(lambda checked=False, i=index: self.download_attachment(i))
            row.addWidget(download_button)

            remove_button = QPushButton("×")
            remove_button.setObjectName("removeAttachment")
            remove_button.setToolTip("Retirer ce fichier de la liste des pièces jointes")
            remove_button.clicked.connect(lambda checked=False, i=index: self.remove_attachment(i))
            row.addWidget(remove_button)

            self.file_row.setItemWidget(item, card)
            item.setSizeHint(card.sizeHint())

        self.file_row.setVisible(bool(self.attachments))

    def pick_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Joindre des fichiers", str(Path.home()),
            "Tous les fichiers (*);;Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff);;Documents (*.txt *.md *.py *.json *.csv *.xml *.html *.pdf *.docx *.xlsx)"
        )
        known = {str(Path(item["path"]).resolve()) for item in self.attachments}
        for path in paths:
            resolved = str(Path(path).resolve())
            if resolved not in known:
                self.attachments.append({"path": path, "name": Path(path).name})
                known.add(resolved)
        self._refresh_attachment_row()

    def remove_attachment(self, index):
        if not 0 <= index < len(self.attachments):
            return
        removed = self.attachments.pop(index)
        self._refresh_attachment_row()
        self.status.setText(f"●  Pièce jointe retirée : {removed['name']}")

    def preview_attachment(self, index):
        if not 0 <= index < len(self.attachments):
            return
        path = Path(self.attachments[index]["path"])
        if not path.is_file():
            QMessageBox.warning(self, "Aperçu impossible", "Le fichier n'existe plus à cet emplacement.")
            return
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            QMessageBox.warning(self, "Aperçu impossible", "Ce format d'image ne peut pas être affiché.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(path.name)
        dialog.resize(900, 700)
        layout = QVBoxLayout(dialog)
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setPixmap(pixmap.scaled(
            860, 610,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))
        image_scroll = QScrollArea()
        image_scroll.setWidgetResizable(True)
        image_scroll.setWidget(image_label)
        layout.addWidget(image_scroll)
        details = QLabel(f"{path.name}  •  {pixmap.width()} × {pixmap.height()} px")
        details.setStyleSheet("color:#A6D3DC;")
        layout.addWidget(details)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()

    def open_attachment(self, index):
        if not 0 <= index < len(self.attachments):
            return
        path = Path(self.attachments[index]["path"])
        if not path.is_file():
            QMessageBox.warning(self, "Ouverture impossible", "Le fichier n'existe plus à cet emplacement.")
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve()))):
            QMessageBox.warning(self, "Ouverture impossible", "Windows n'a pas pu ouvrir ce fichier avec son application par défaut.")

    def download_attachment(self, index):
        if not 0 <= index < len(self.attachments):
            return
        source = Path(self.attachments[index]["path"])
        if not source.is_file():
            QMessageBox.warning(self, "Téléchargement impossible", "Le fichier source n'existe plus.")
            return
        destination, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer une copie du fichier",
            str(Path.home() / source.name),
            "Tous les fichiers (*)"
        )
        if not destination:
            return
        try:
            import shutil
            target = Path(destination)
            if target.resolve() == source.resolve():
                QMessageBox.information(self, "Copie inutile", "Le fichier est déjà à cet emplacement.")
                return
            shutil.copy2(source, target)
            self.status.setText(f"●  Copie enregistrée : {target.name}")
        except Exception as exc:
            QMessageBox.warning(self, "Échec de la copie", str(exc))

    def load_attachments(self):
        texts, images = [], []
        for item in self.attachments:
            path = Path(item["path"])
            size = path.stat().st_size
            if size > 8_000_000:
                raise ValueError(f"{path.name} dépasse la limite de 8 Mo.")
            suffix = path.suffix.lower()
            if suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}:
                images.append(base64.b64encode(path.read_bytes()).decode("ascii"))
            elif suffix == ".pdf":
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(str(path))
                    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
                except ImportError:
                    extracted = "[PDF joint : installez pypdf pour extraire son texte.]"
                texts.append(f"\n\n--- Fichier : {path.name} ---\n{extracted[:30000]}")
            elif suffix == ".docx":
                try:
                    from docx import Document
                    document = Document(str(path))
                    chunks = [paragraph.text for paragraph in document.paragraphs]
                    for table in document.tables:
                        for row in table.rows:
                            chunks.append(" | ".join(cell.text for cell in row.cells))
                    extracted = "\n".join(chunks)
                except ImportError:
                    extracted = "[DOCX joint : installez python-docx pour en extraire le texte.]"
                texts.append(f"\n\n--- Fichier : {path.name} ---\n{extracted[:30000]}")
            elif suffix == ".xlsx":
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
                    extracted = "\n".join(chunks)
                except ImportError:
                    extracted = "[XLSX joint : installez openpyxl pour en extraire le contenu.]"
                texts.append(f"\n\n--- Fichier : {path.name} ---\n{extracted[:30000]}")
            elif suffix in {".txt", ".md", ".py", ".json", ".csv", ".xml", ".html", ".htm", ".css", ".js", ".log", ".yaml", ".yml", ".ini"}:
                try:
                    extracted = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    extracted = path.read_text(encoding="utf-8-sig", errors="replace")
                texts.append(f"\n\n--- Fichier : {path.name} ---\n{extracted[:30000]}")
            else:
                texts.append(
                    f"\n\n--- Fichier : {path.name} ---\n"
                    "[Fichier joint. Son format n'est pas extrait en texte ; "
                    "utilisez le bouton Ouvrir pour le consulter dans son application.]"
                )
        return "".join(texts), images

    def send_message(self):
        if self.worker_thread and self.worker_thread.isRunning():
            return
        prompt = self.input.toPlainText().strip()
        if not prompt and not self.attachments:
            return
        try:
            attachment_text, images = self.load_attachments()
        except Exception as exc:
            QMessageBox.warning(self, "Fichier non chargé", str(exc))
            return
        if self.attachments:
            names = ", ".join(item["name"] for item in self.attachments)
            visible_prompt = (prompt or "Analyse les fichiers joints.") + f"\n\n📎 {names}"
            prompt = (prompt or "Analyse les fichiers joints.") + f"\n\nFichiers joints : {names}" + attachment_text
        else:
            visible_prompt = prompt
        self.add_message(visible_prompt, "user")
        self.current_conversation["messages"].append({
            "role": "user",
            "content": visible_prompt,
        })
        self._persist_current_conversation()
        self.input.clear()
        self.attachments.clear()
        self.file_row.clear()
        self.file_row.hide()
        self.current_assistant_bubble = None
        self.current_response = ""
        self._response_recorded = False
        self.current_response_view = None
        self.current_thinking_panel = None
        self.current_thinking = ""
        self._thinking_recorded = False
        self._rendered_response = None
        self._rendered_thinking = None
        self._markdown_timer.stop()
        self.send_button.setDisabled(True)
        self.attach_button.setDisabled(True)
        self.history_list.setDisabled(True)
        self.new_conversation_button.setDisabled(True)
        self.status.setText("●  JARVIS réfléchit…")
        self.status.setStyleSheet("color: #FFB454;")

        self.worker_thread = QThread()
        self.worker = AgentWorker(
            prompt, images, think_enabled=self.reflection_button.isChecked()
        )
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.token.connect(self.on_token)
        self.worker.thinking.connect(self.on_thinking)
        self.worker.response_start.connect(self.start_response)
        self.worker.tool_event.connect(self.on_tool_event)
        self.worker.finished.connect(self.on_finished)
        self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.failed.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.cleanup_worker)
        self.worker_thread.start()

    def start_response(self):
        # Termine le rendu du tour précédent avant d'ajouter un nouveau bloc.
        self._flush_live_markdown()
        self._record_current_response()
        self._record_current_thinking()
        bubble = self.ensure_assistant_bubble()
        self.current_response = ""
        self._response_recorded = False
        self._rendered_response = None
        self.current_thinking_panel = None
        self.current_thinking = ""
        self._thinking_recorded = False
        self._rendered_thinking = None
        self.current_response_view = bubble.add_markdown_block("")
        self.scroll_to_bottom()

    def on_token(self, token):
        bubble = self.ensure_assistant_bubble()
        if self.current_response_view is None:
            self.current_response_view = bubble.add_markdown_block("")
            self._rendered_response = None
        self.current_response += token
        if not self._markdown_timer.isActive():
            self._markdown_timer.start()

    def on_thinking(self, token):
        if not token:
            return
        bubble = self.ensure_assistant_bubble()
        if self.current_thinking_panel is None:
            self.current_thinking = ""
            self._rendered_thinking = None
            self.current_thinking_panel = bubble.add_panel(
                "Réflexion du modèle", expanded=True, max_height=None
            )
        self.current_thinking += token
        self._thinking_recorded = False
        if not self._markdown_timer.isActive():
            self._markdown_timer.start()

    def _record_current_response(self):
        if self.current_response and not self._response_recorded:
            self.current_conversation["messages"].append({
                "role": "assistant",
                "content": self.current_response,
            })
            self._response_recorded = True

    def _record_current_thinking(self):
        if self.current_thinking and not self._thinking_recorded:
            self.current_conversation["messages"].append({
                "role": "thinking",
                "content": self.current_thinking,
            })
            self._thinking_recorded = True

    def _flush_live_markdown(self):
        """Rend les flux à intervalle régulier plutôt qu'à chaque token."""
        changed = False
        if (
                self.current_response_view is not None
                and self.current_response != self._rendered_response
        ):
            render_markdown(self.current_response_view, self.current_response)
            self._rendered_response = self.current_response
            changed = True

        if (
                self.current_thinking_panel is not None
                and self.current_thinking != self._rendered_thinking
        ):
            self.current_thinking_panel.set_markdown(self.current_thinking)
            self._rendered_thinking = self.current_thinking
            changed = True

        if changed:
            self.scroll_to_bottom()

    def on_tool_event(self, state, name, details):
        self._flush_live_markdown()
        self._record_current_response()
        self._record_current_thinking()
        if name == "plot_chart" and isinstance(details, dict):
            payload = details.get("result", {})
            chart_data = payload.get("chart") if isinstance(payload, dict) else None
            if chart_data and state == "Résultat":
                self.ensure_assistant_bubble().add_chart(chart_data)
                self.current_conversation["messages"].append({
                    "role": "chart",
                    "data": chart_data,
                })
                self.current_thinking_panel = None
                self.current_thinking = ""
                self._thinking_recorded = False
                self.scroll_to_bottom()
                return
        if name == "create_3d_model" and isinstance(details, dict):
            payload = details.get("result", {})
            model_data = payload.get("model") if isinstance(payload, dict) else None
            if model_data and state == "Résultat":
                try:
                    self.ensure_assistant_bubble().add_3d_model(model_data)
                    self.current_conversation["messages"].append({
                        "role": "model3d",
                        "data": model_data,
                    })
                except Exception as exc:
                    self.add_system_panel("Affichage 3D impossible", str(exc), expanded=True)
                    self.current_conversation["messages"].append({
                        "role": "system",
                        "title": "Affichage 3D impossible",
                        "details": str(exc),
                        "expanded": True,
                    })
                self.current_thinking_panel = None
                self.current_thinking = ""
                self._thinking_recorded = False
                self.scroll_to_bottom()
                return
        title = f"{state} - {name}"
        self.add_system_panel(title, details)
        self.current_conversation["messages"].append({
            "role": "system",
            "title": title,
            "details": (
                json.dumps(details, ensure_ascii=False, indent=2)
                if isinstance(details, (dict, list)) else str(details or "")
            ),
        })
        # Un nouvel appel d'outil peut être suivi d'un nouveau cycle de réflexion.
        self.current_thinking_panel = None
        self.current_thinking = ""
        self._thinking_recorded = False

    def on_finished(self):
        self._markdown_timer.stop()
        self._flush_live_markdown()
        self._record_current_response()
        self._record_current_thinking()
        self.send_button.setDisabled(False)
        self.attach_button.setDisabled(False)
        self.status.setText("●  Prêt")
        self.status.setStyleSheet("color: #70D9A6;")
        fallback_response = False
        if self.current_assistant_bubble is None:
            self.add_message("Traitement terminé.", "assistant")
            fallback_response = True
        elif not self.current_response and not self.current_assistant_bubble.markdown_views:
            self.current_assistant_bubble.add_markdown_block("Traitement terminé.")
            fallback_response = True
        if fallback_response:
            self.current_conversation["messages"].append({
                "role": "assistant",
                "content": "Traitement terminé.",
            })
        self._persist_current_conversation()

    def on_failed(self, error):
        self._markdown_timer.stop()
        self._flush_live_markdown()
        self._record_current_response()
        self._record_current_thinking()
        self.add_system_panel("Erreur système - JARVIS", error, expanded=True)
        self.current_conversation["messages"].append({
            "role": "system",
            "title": "Erreur système - JARVIS",
            "details": error,
            "expanded": True,
        })
        self.status.setText("●  Erreur")
        self.status.setStyleSheet("color: #FF6B68;")
        self.send_button.setDisabled(False)
        self.attach_button.setDisabled(False)
        self._persist_current_conversation()

    def _persist_current_conversation(self):
        try:
            self.conversation_store.save(self.current_conversation)
        except sqlite3.Error as exc:
            QMessageBox.warning(
                self, "Historique indisponible",
                f"La conversation n'a pas pu être sauvegardée : {exc}",
            )
            return
        self._refresh_conversation_list()

    def cleanup_worker(self):
        self.worker = None
        self.worker_thread = None
        self.history_list.setDisabled(False)
        self.new_conversation_button.setDisabled(False)

    def closeEvent(self, event):
        if self.worker_thread and self.worker_thread.isRunning():
            QMessageBox.information(
                self, "JARVIS en cours",
                "Attendez la fin de la tâche avant de fermer JARVIS."
            )
            event.ignore()
            return
        event.accept()
