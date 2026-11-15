import math

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

class InlineChart(QWidget):
    """Graphique Qt avec axes numériques proportionnels et info-bulles."""

    def __init__(self, data, parent=None):
        super().__init__(parent)

        self.data = data if isinstance(data, dict) else {}

        self.setMinimumHeight(480)
        self.setMaximumHeight(480)

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )

        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setMouseTracking(True)

        self._hover_index = None
        self._chart_points = []
        self._plot_rect = None

    # --------------------------------------------------
    # CALCUL DES GRADUATIONS INTELLIGENTES
    # --------------------------------------------------

    @staticmethod
    def nice_scale(minimum, maximum, target_ticks=6):
        if minimum == maximum:
            minimum -= 1
            maximum += 1

        rough_step = (maximum - minimum) / target_ticks

        magnitude = 10 ** math.floor(math.log10(rough_step))
        normalized = rough_step / magnitude

        if normalized <= 1:
            nice_step = 1
        elif normalized <= 2:
            nice_step = 2
        elif normalized <= 2.5:
            nice_step = 2.5
        elif normalized <= 5:
            nice_step = 5
        else:
            nice_step = 10

        step = nice_step * magnitude

        low = math.floor(minimum / step) * step
        high = math.ceil(maximum / step) * step

        if high <= low:
            high = low + step

        ticks = []
        current = low

        for _ in range(100):
            if current > high + step * 0.000001:
                break

            # Évite les petites erreurs de flottants
            ticks.append(round(current, 12))
            current += step

        return low, high, step, ticks

    # --------------------------------------------------
    # RENDU
    # --------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter()

        if not painter.begin(self):
            return

        try:
            painter.setRenderHint(
                QPainter.RenderHint.Antialiasing, True
            )

            painter.fillRect(self.rect(), QColor("#06111A"))

            width = self.width()
            height = self.height()

            if width < 120 or height < 120:
                return

            labels = self.data.get("x_values", [])
            y_values = self.data.get("y_values", [])

            if (
                not isinstance(labels, list)
                or not isinstance(y_values, list)
                or not y_values
                or len(labels) != len(y_values)
                or len(y_values) > 100
            ):
                painter.setPen(QColor("#D7F8FF"))
                painter.drawText(12, 28, "Données du graphique invalides")
                self._chart_points = []
                return

            try:
                y_numeric = [float(v) for v in y_values]

                if not all(math.isfinite(v) for v in y_numeric):
                    raise ValueError()

                x_numeric = [float(v) for v in labels]

                if not all(math.isfinite(v) for v in x_numeric):
                    raise ValueError()

                numeric_x = True

            except (TypeError, ValueError, OverflowError):
                numeric_x = False
                x_numeric = []

            if not all(math.isfinite(v) for v in y_numeric):
                painter.setPen(QColor("#D7F8FF"))
                painter.drawText(12, 28, "Valeurs Y invalides")
                self._chart_points = []
                return

            # --------------------------------------------------
            # DIMENSIONS
            # --------------------------------------------------

            left = 65
            top = 45
            right = width - 20
            bottom = height - 65

            plot_width = max(1, right - left)
            plot_height = max(1, bottom - top)

            self._plot_rect = (left, top, right, bottom)

            # --------------------------------------------------
            # TITRE
            # --------------------------------------------------

            painter.setPen(QColor("#D7F8FF"))
            painter.setFont(
                QFont("Segoe UI", 10, QFont.Weight.DemiBold)
            )

            painter.drawText(
                16, 25,
                str(self.data.get("title", "Graphique"))[:120]
            )

            # --------------------------------------------------
            # AXES NUMÉRIQUES
            # --------------------------------------------------

            # Y : toujours numérique
            y_min = min(y_numeric)
            y_max = max(y_numeric)

            # Inclure zéro pour les graphiques en barres
            chart_type = self.data.get("chart_type", "line")

            if chart_type == "bar":
                y_min = min(0.0, y_min)
                y_max = max(0.0, y_max)

            y_low, y_high, y_step, y_ticks = self.nice_scale(
                y_min, y_max, 6
            )

            # X : numérique si possible
            if numeric_x:
                x_min = min(x_numeric)
                x_max = max(x_numeric)

                x_low, x_high, x_step, x_ticks = self.nice_scale(
                    x_min, x_max, 8
                )

            else:
                x_min = 0
                x_max = max(1, len(labels) - 1)

                x_low = 0
                x_high = x_max
                x_step = 1
                x_ticks = list(range(len(labels)))

            # --------------------------------------------------
            # TRANSFORMATION DES COORDONNÉES
            # --------------------------------------------------

            def point(index, value):
                if numeric_x:
                    x_value = x_numeric[index]
                else:
                    x_value = index

                x = left + (
                    (x_value - x_low) / (x_high - x_low)
                ) * plot_width

                y = bottom - (
                    (value - y_low) / (y_high - y_low)
                ) * plot_height

                return int(round(x)), int(round(y))

            # --------------------------------------------------
            # QUADRILLAGE HORIZONTAL : Y
            # --------------------------------------------------

            painter.setFont(QFont("Segoe UI", 8))

            for tick in y_ticks:
                y = bottom - (
                    (tick - y_low) / (y_high - y_low)
                ) * plot_height

                painter.setPen(
                    QPen(QColor("#176078"), 1)
                )

                painter.drawLine(
                    left, int(y), right, int(y)
                )

                painter.setPen(QColor("#79A8B5"))

                painter.drawText(
                    3, int(y + 4),
                    left - 12, 16,
                    Qt.AlignmentFlag.AlignRight,
                    f"{tick:g}"
                )

            # --------------------------------------------------
            # QUADRILLAGE VERTICAL : X
            # --------------------------------------------------

            for tick in x_ticks:
                x = left + (
                    (tick - x_low) / (x_high - x_low)
                ) * plot_width

                painter.setPen(
                    QPen(QColor("#176078"), 1)
                )

                painter.drawLine(
                    int(x), top, int(x), bottom
                )

                painter.setPen(QColor("#79A8B5"))

                if numeric_x:
                    label = f"{tick:g}"
                else:
                    label = str(labels[int(tick)])[:10]

                painter.drawText(
                    int(x) - 30,
                    bottom + 5,
                    60, 16,
                    Qt.AlignmentFlag.AlignHCenter,
                    label
                )

            # --------------------------------------------------
            # AXES PRINCIPAUX
            # --------------------------------------------------

            painter.setPen(
                QPen(QColor("#79A8B5"), 1.5)
            )

            painter.drawLine(left, bottom, right, bottom)
            painter.drawLine(left, top, left, bottom)

            # --------------------------------------------------
            # DONNÉES
            # --------------------------------------------------

            points = [
                point(index, value)
                for index, value in enumerate(y_numeric)
            ]

            self._chart_points = [
                (x, y, index)
                for index, (x, y) in enumerate(points)
            ]

            # --------------------------------------------------
            # GRAPHIQUE EN BARRES
            # --------------------------------------------------

            if chart_type == "bar":

                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor("#00C8F0"))

                zero_y = bottom - (
                    (0.0 - y_low) / (y_high - y_low)
                ) * plot_height

                if numeric_x:
                    # Largeur basée sur l'espacement réel des X
                    if len(x_numeric) > 1:
                        distances = [
                            abs(b - a)
                            for a, b in zip(
                                sorted(set(x_numeric)),
                                sorted(set(x_numeric))[1:]
                            )
                        ]

                        bar_spacing = min(distances) if distances else x_high - x_low
                    else:
                        bar_spacing = (x_high - x_low) * 0.1

                    slot = (
                        bar_spacing / (x_high - x_low)
                    ) * plot_width

                else:
                    slot = plot_width / max(1, len(y_numeric))

                for index, value in enumerate(y_numeric):
                    x, y = points[index]

                    bar_width = max(
                        2, int(slot * 0.64)
                    )

                    bar_height = max(
                        2, abs(int(zero_y) - y)
                    )

                    painter.drawRoundedRect(
                        int(x - bar_width / 2),
                        int(min(y, zero_y)),
                        bar_width,
                        bar_height,
                        4, 4
                    )

            # --------------------------------------------------
            # GRAPHIQUE LINÉAIRE
            # --------------------------------------------------

            else:
                painter.setPen(
                    QPen(QColor("#28D9F5"), 3)
                )

                for first, second in zip(
                    points, points[1:]
                ):
                    painter.drawLine(
                        first[0], first[1],
                        second[0], second[1]
                    )

                painter.setBrush(QColor("#E4FCFF"))
                painter.setPen(
                    QPen(QColor("#28D9F5"), 1)
                )

                for x, y in points:
                    painter.drawEllipse(
                        x - 4, y - 4, 8, 8
                    )

            # --------------------------------------------------
            # RÉTICULE ET INFO-BULLE
            # --------------------------------------------------

            if self._hover_index is not None:
                index = self._hover_index

                if 0 <= index < len(points):
                    px, py = points[index]

                    # Réticule
                    painter.setPen(
                        QPen(
                            QColor("#28D9F5"),
                            1,
                            Qt.PenStyle.DashLine
                        )
                    )

                    painter.drawLine(px, top, px, bottom)
                    painter.drawLine(left, py, right, py)

                    # Point sélectionné
                    painter.setBrush(QColor("#FFFFFF"))
                    painter.setPen(
                        QPen(QColor("#28D9F5"), 2)
                    )

                    painter.drawEllipse(
                        px - 6, py - 6, 12, 12
                    )

                    # Bulle
                    bubble_width = 135
                    bubble_height = 52

                    bx = px + 14
                    by = py - bubble_height - 12

                    if bx + bubble_width > width - 5:
                        bx = px - bubble_width - 14

                    if by < top:
                        by = py + 14

                    bx = max(
                        5,
                        min(bx, width - bubble_width - 5)
                    )

                    by = max(
                        top,
                        min(by, bottom - bubble_height)
                    )

                    painter.setPen(
                        QPen(QColor("#28D9F5"), 1)
                    )

                    painter.setBrush(QColor("#0B202C"))

                    painter.drawRoundedRect(
                        int(bx), int(by),
                        bubble_width, bubble_height,
                        7, 7
                    )

                    # Coordonnées réelles
                    x_label = labels[index]

                    painter.setFont(
                        QFont(
                            "Segoe UI", 9,
                            QFont.Weight.Bold
                        )
                    )
                    painter.setPen(QColor("#91BAC5"))

                    painter.drawText(
                        int(bx + 9),
                        int(by + 19),
                        f"X: {str(x_label)[:20]}"
                    )

                    painter.drawText(
                        int(bx + 9),
                        int(by + 40),
                        f"Y: {y_numeric[index]:g}"
                    )

            # --------------------------------------------------
            # TITRES DES AXES
            # --------------------------------------------------

            painter.setPen(QColor("#91BAC5"))
            painter.setFont(QFont("Segoe UI", 8))

            if self.data.get("x_label"):
                painter.drawText(
                    left,
                    height - 32,
                    plot_width,
                    18,
                    Qt.AlignmentFlag.AlignHCenter,
                    str(self.data["x_label"])[:80]
                )

            if self.data.get("y_label"):
                painter.save()

                painter.translate(
                    12, top + plot_height / 2
                )

                painter.rotate(-90)

                painter.drawText(
                    int(-plot_height / 2),
                    0,
                    int(plot_height),
                    18,
                    Qt.AlignmentFlag.AlignHCenter,
                    str(self.data["y_label"])[:80]
                )

                painter.restore()

        except Exception:
            self._chart_points = []

            try:
                painter.fillRect(
                    self.rect(),
                    QColor("#06111A")
                )

                painter.setPen(QColor("#FF6B68"))

                painter.drawText(
                    12, 28,
                    "Erreur lors du rendu du graphique"
                )

            except Exception:
                pass

        finally:
            painter.end()

    # --------------------------------------------------
    # SURVOL SOURIS
    # --------------------------------------------------

    def mouseMoveEvent(self, event):
        if not self._chart_points:
            return

        mouse_x = event.position().x()
        mouse_y = event.position().y()

        closest_index = None
        closest_distance = 12 ** 2

        for x, y, index in self._chart_points:
            distance = (
                (mouse_x - x) ** 2
                + (mouse_y - y) ** 2
            )

            if distance < closest_distance:
                closest_distance = distance
                closest_index = index

        if closest_index != self._hover_index:
            self._hover_index = closest_index
            self.update()

    def leaveEvent(self, event):
        self._hover_index = None
        self.update()
        super().leaveEvent(event)
