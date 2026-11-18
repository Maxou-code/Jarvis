from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (QFileDialog, QFrame, QHBoxLayout, QLabel, QMessageBox,
                             QPushButton, QSizePolicy, QVBoxLayout, QWidget)

from Core.paths import safe_path

class OffscreenSTLView(QLabel):
    """Rendu VTK hors écran, dimensionné selon l'espace Qt disponible."""

    def __init__(self, mesh, parent=None):
        super().__init__(parent)

        import pyvista as pv

        self._closed = False
        self._last = None
        self._render_size = None

        self.pl = pv.Plotter(
            off_screen=True,
            window_size=(640, 480)
        )

        self.pl.set_background("#050B12")

        self._mesh_actor = self.pl.add_mesh(
            mesh,
            color="#103746",
            show_edges=True,
            edge_color="#087C9A",
            line_width=2.2,
            smooth_shading=False,
            ambient=0.55,
            diffuse=0.45,
            specular=0.0,
            lighting=True
        )

        self._edges_visible = True
        self.pl.view_isometric()
        self.pl.reset_camera()

        self.setMinimumSize(0, 0)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            "background:#050B12; border:none;"
        )

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Temporisation du redimensionnement
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(60)
        self._resize_timer.timeout.connect(
            self._resize_render_target
        )

        # Premier dimensionnement après insertion dans le layout
        QTimer.singleShot(0, self._resize_render_target)

    # --------------------------------------------------
    # DIMENSIONNEMENT DYNAMIQUE
    # --------------------------------------------------

    def _resize_render_target(self):
        if self._closed:
            return

        width = self.width()
        height = self.height()

        if width <= 1 or height <= 1:
            return

        new_size = (width, height)

        if new_size == self._render_size:
            self.refresh()
            return

        try:
            # Adapter réellement la résolution VTK
            self.pl.window_size = new_size

            self._render_size = new_size

            self.pl.render()
            self.refresh()

        except Exception as exc:
            print(f"[VTK RESIZE] {exc}")

    # --------------------------------------------------
    # RENDU
    # --------------------------------------------------

    def refresh(self):
        if self._closed:
            return

        if self.width() <= 0 or self.height() <= 0:
            return

        try:
            img = self.pl.screenshot(return_img=True)

            h, w, _ = img.shape

            qimg = QImage(
                img.data,
                w,
                h,
                img.strides[0],
                QImage.Format.Format_RGB888
            ).copy()

            pixmap = QPixmap.fromImage(qimg)

            self.setPixmap(
                pixmap.scaled(
                    self.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )

        except Exception as exc:
            print(f"[VTK OFFSCREEN] {exc}")

    # --------------------------------------------------
    # CAMÉRA
    # --------------------------------------------------

    def reset_view(self):
        if self._closed:
            return

        self.pl.view_isometric()
        self.pl.reset_camera()
        self.pl.render()
        self.refresh()

    def set_edges_visible(self, visible):
        if self._closed:
            return
        self._edges_visible = bool(visible)
        self._mesh_actor.GetProperty().SetEdgeVisibility(self._edges_visible)
        self.pl.render()
        self.refresh()

    # --------------------------------------------------
    # ROTATION
    # --------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._last = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._last is None or self._closed:
            return

        delta = event.position() - self._last
        self._last = event.position()

        camera = self.pl.camera

        camera.Azimuth(-delta.x() * 0.5)
        camera.Elevation(delta.y() * 0.5)
        camera.OrthogonalizeViewUp()

        self.pl.render()
        self.refresh()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._last = None
            self.setCursor(Qt.CursorShape.ArrowCursor)

        super().mouseReleaseEvent(event)

    # --------------------------------------------------
    # ZOOM
    # --------------------------------------------------

    def wheelEvent(self, event):
        if self._closed:
            return

        delta = event.angleDelta().y()

        if delta == 0:
            return

        factor = 1.1 if delta > 0 else 1 / 1.1

        self.pl.camera.Zoom(factor)

        self.pl.render()
        self.refresh()

        event.accept()

    # --------------------------------------------------
    # REDIMENSIONNEMENT
    # --------------------------------------------------

    def resizeEvent(self, event):
        super().resizeEvent(event)

        if not self._closed:
            self._resize_timer.start()

    # --------------------------------------------------
    # FERMETURE
    # --------------------------------------------------

    def closeEvent(self, event):
        self.close_renderer()
        super().closeEvent(event)

    def close_renderer(self):
        if self._closed:
            return

        self._closed = True

        self._resize_timer.stop()

        try:
            self.pl.close()
        except Exception:
            pass
class Inline3DViewer(QFrame):
    """Visualiseur STL avec rendu VTK hors écran."""

    open_requested = pyqtSignal(object)

    def __init__(self, model_data, parent=None, show_open_button=True):
        super().__init__(parent)

        self.model_data = dict(model_data or {})
        self.model_path = safe_path(
            self.model_data.get("path", "")
        )

        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"Fichier STL introuvable : {self.model_path}"
            )

        self.setObjectName("inline3DViewer")
        self.setMinimumHeight(600)
        self.setMaximumHeight(600)

        self.setStyleSheet("""
            QFrame#inline3DViewer {
                background:#050B12;
                border:1px solid #174052;
                border-radius:8px;
            }

            QLabel {
                color:#B9DCE5;
                background:transparent;
                border:none;
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

            QPushButton#stlButton {
                background:#123D32;
                border-color:#27865F;
                color:#A5F0C7;
            }

            QPushButton#stlButton:hover {
                background:#195641;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 9, 10, 9)
        root.setSpacing(7)

        # En-tête
        top = QHBoxLayout()

        title = QLabel(
            self.model_data.get("title", "Modèle 3D")
        )
        title.setStyleSheet(
            "font-size:13px;font-weight:700;color:#D9F8FF;"
        )

        top.addWidget(title, 1)

        self.status_label = QLabel("STL • mm")
        self.status_label.setStyleSheet(
            "font-size:11px;color:#70D9A6;"
        )
        top.addWidget(self.status_label)

        if show_open_button:
            open_button = QPushButton("Ouvrir en grand")
            open_button.clicked.connect(
                lambda: self.open_requested.emit(self.model_data)
            )
            top.addWidget(open_button)

        reset_button = QPushButton("Réinitialiser la vue")
        reset_button.clicked.connect(self.reset_camera)
        top.addWidget(reset_button)

        self.edge_button = QPushButton("Afficher/Masquer Arrêtes")
        self.edge_button.setCheckable(True)
        self.edge_button.setChecked(True)
        self.edge_button.setToolTip("Afficher ou masquer les arêtes du maillage")
        self.edge_button.toggled.connect(self.set_edges_visible)
        top.addWidget(self.edge_button)

        export_button = QPushButton("↓  STL")
        export_button.setObjectName("stlButton")
        export_button.clicked.connect(self.export_stl)
        top.addWidget(export_button)

        root.addLayout(top)

        # Zone 3D
        self.viewer_host = QWidget(self)
        # self.viewer_host.setMinimumHeight(480)
        self.viewer_host.setStyleSheet(
            "background:#050B12;"
            "border:1px solid #153746;"
            "border-radius:8px;"
        )

        self.viewer_layout = QVBoxLayout(self.viewer_host)
        self.viewer_layout.setContentsMargins(0, 0, 0, 0)
        self.viewer_layout.setSpacing(0)

        root.addWidget(self.viewer_host, 1)

        # Initialisation du moteur
        self._mesh = None
        self.view = None

        try:
            import pyvista as pv

            self._mesh = pv.read(str(self.model_path))

            if isinstance(self._mesh, pv.MultiBlock):
                self._mesh = self._mesh.combine()

            if (
                self._mesh.n_points == 0
                or self._mesh.n_cells == 0
            ):
                raise ValueError(
                    "Le STL ne contient aucune géométrie exploitable."
                )

            # Rendu hors écran
            self.view = OffscreenSTLView(
                self._mesh,
                self.viewer_host
            )

            self.viewer_layout.addWidget(self.view)

            self.status_label.setText("STL • Rendu actif")

        except Exception as exc:
            self.edge_button.setDisabled(True)

            if self.view is not None:
                self.view.close_renderer()
                self.view = None

            fallback = QLabel(
                "Visualiseur 3D indisponible.\n\n"
                f"Détail : {exc}"
            )

            fallback.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )
            fallback.setWordWrap(True)

            self.viewer_layout.addWidget(fallback)

            self.status_label.setText(
                "STL généré • aperçu indisponible"
            )

    def reset_camera(self):
        if self.view is not None:
            try:
                self.view.reset_view()
            except Exception as exc:
                self.status_label.setToolTip(str(exc))

    def set_edges_visible(self, visible):
        if self.view is not None:
            try:
                self.view.set_edges_visible(visible)
            except Exception as exc:
                self.status_label.setToolTip(str(exc))

    def export_stl(self):
        destination, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter le modèle STL",
            str(Path.home() / self.model_path.name),
            "Fichier STL (*.stl)"
        )

        if not destination:
            return

        target = Path(destination)

        if target.suffix.lower() != ".stl":
            target = target.with_suffix(".stl")

        try:
            import shutil

            shutil.copy2(self.model_path, target)

            self.status_label.setText(
                f"Exporté : {target.name}"
            )

        except Exception as exc:
            QMessageBox.warning(
                self,
                "Export STL impossible",
                str(exc)
            )

    def closeEvent(self, event):
        self.close_renderer()
        super().closeEvent(event)

    def close_renderer(self):
        if self.view is not None:
            self.view.close_renderer()
            self.view = None
