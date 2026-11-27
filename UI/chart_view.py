import math

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

class InlineChart(QWidget):
    """Graphique Qt avec axes numériques proportionnels et info-bulles."""

    @staticmethod
    def _smooth_path(points):
        path = QPainterPath()
        if not points:
            return path

        path.moveTo(*points[0])
        if len(points) == 1:
            return path

        def tangents(values):
            secants = [
                values[index + 1] - values[index]
                for index in range(len(values) - 1)
            ]
            if len(secants) == 1:
                return [secants[0], secants[0]]

            def endpoint(first, second):
                slope = (3 * first - second) / 2
                if slope * first <= 0:
                    return 0
                if first * second < 0 and abs(slope) > abs(3 * first):
                    return 3 * first
                return slope

            result = [endpoint(secants[0], secants[1])]
            for previous, following in zip(secants, secants[1:]):
                if previous * following <= 0:
                    result.append(0)
                else:
                    result.append(2 * previous * following / (previous + following))
            result.append(endpoint(secants[-1], secants[-2]))
            return result

        x_values = [point[0] for point in points]
        y_values = [point[1] for point in points]
        x_tangents = tangents(x_values)
        y_tangents = tangents(y_values)

        for index in range(len(points) - 1):
            first_x, first_y = points[index]
            second_x, second_y = points[index + 1]
            path.cubicTo(
                first_x + x_tangents[index] / 3,
                first_y + y_tangents[index] / 3,
                second_x - x_tangents[index + 1] / 3,
                second_y - y_tangents[index + 1] / 3,
                second_x,
                second_y,
            )
        return path

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
        self._hover_series_index = None
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
            x_display_labels = self.data.get("x_display_labels", labels)
            raw_series = self.data.get("series")

            if (
                not isinstance(labels, list)
                or not isinstance(x_display_labels, list)
                or len(x_display_labels) != len(labels)
                or not labels
                or len(labels) > 100
            ):
                painter.setPen(QColor("#D7F8FF"))
                painter.drawText(12, 28, "Données du graphique invalides")
                self._chart_points = []
                return

            if raw_series is None:
                raw_series = [{
                    "name": "",
                    "y_values": y_values,
                    "y_display_labels": self.data.get("y_display_labels", y_values),
                }]
            if not isinstance(raw_series, list) or not 1 <= len(raw_series) <= 8:
                painter.setPen(QColor("#D7F8FF"))
                painter.drawText(12, 28, "Données du graphique invalides")
                self._chart_points = []
                return

            series_data = []
            try:
                for index, item in enumerate(raw_series):
                    if not isinstance(item, dict):
                        raise ValueError()
                    values = item.get("y_values")
                    display_labels = item.get("y_display_labels", values)
                    if (
                        not isinstance(values, list)
                        or not isinstance(display_labels, list)
                        or len(values) != len(labels)
                        or len(display_labels) != len(values)
                    ):
                        raise ValueError()
                    numeric_values = [float(value) for value in values]
                    if not all(math.isfinite(value) for value in numeric_values):
                        raise ValueError()
                    series_data.append({
                        "name": str(item.get("name") or f"Série {index + 1}")[:40],
                        "values": numeric_values,
                        "display_labels": display_labels,
                    })
            except (TypeError, ValueError, OverflowError):
                painter.setPen(QColor("#D7F8FF"))
                painter.drawText(12, 28, "Valeurs Y invalides")
                self._chart_points = []
                return

            y_numeric = [value for item in series_data for value in item["values"]]
            y_display_labels = [
                label for item in series_data for label in item["display_labels"]
            ]
            x_numeric = []
            axis_type = self.data.get("x_axis_type")
            if axis_type == "category":
                numeric_x = False
            else:
                try:
                    x_numeric = [float(v) for v in labels]

                    if not all(math.isfinite(v) for v in x_numeric):
                        raise ValueError()

                    numeric_x = axis_type == "numeric" or axis_type is None

                except (TypeError, ValueError, OverflowError):
                    numeric_x = False
                    x_numeric = []

            # --------------------------------------------------
            # DIMENSIONS
            # --------------------------------------------------

            left = 65
            right = width - 20
            bottom = height - 65
            plot_width = max(1, right - left)
            legend_columns = max(1, min(4, plot_width // 150))
            legend_rows = (
                math.ceil(len(series_data) / legend_columns)
                if len(series_data) > 1 else 0
            )
            top = 45 + legend_rows * 18

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

            def tick_label(tick, values, display_labels):
                for value, label in zip(values, display_labels):
                    if math.isclose(tick, value, rel_tol=1e-10, abs_tol=1e-10):
                        return str(label)[:10]
                return f"{tick:g}"

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
                    tick_label(tick, y_numeric, y_display_labels)
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
                    label = tick_label(tick, x_numeric, x_display_labels)
                else:
                    label = str(x_display_labels[int(tick)])[:10]

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

            points_by_series = [
                [
                    point(index, value)
                    for index, value in enumerate(item["values"])
                ]
                for item in series_data
            ]
            self._chart_points = [
                (x, y, index, series_index)
                for series_index, points in enumerate(points_by_series)
                for index, (x, y) in enumerate(points)
            ]
            colors = [
                QColor(color) for color in (
                    "#28D9F5", "#FF9F43", "#A78BFA", "#4ADE80",
                    "#FB7185", "#FACC15", "#60A5FA", "#2DD4BF",
                )
            ]
            if len(series_data) > 1:
                painter.setFont(QFont("Segoe UI", 8))
                for index, item in enumerate(series_data):
                    column = index % legend_columns
                    row = index // legend_columns
                    legend_x = left + column * (plot_width // legend_columns)
                    legend_y = 44 + row * 18
                    painter.setPen(QPen(colors[index], 3))
                    painter.drawLine(legend_x, legend_y - 3, legend_x + 16, legend_y - 3)
                    painter.setPen(QColor("#A6D3DC"))
                    label = item["name"]
                    painter.drawText(legend_x + 21, legend_y, label[:20])

            # --------------------------------------------------
            # GRAPHIQUE EN BARRES
            # --------------------------------------------------

            if chart_type == "bar":

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
                    slot = plot_width / max(1, len(labels))

                group_width = slot * 0.72
                bar_width = max(2, int(group_width / len(series_data)))
                painter.setPen(Qt.PenStyle.NoPen)
                for series_index, (item, points) in enumerate(
                    zip(series_data, points_by_series)
                ):
                    painter.setBrush(colors[series_index])
                    for index, value in enumerate(item["values"]):
                        x, y = points[index]
                        offset = (
                            series_index - (len(series_data) - 1) / 2
                        ) * bar_width
                        bar_height = max(2, abs(int(zero_y) - y))
                        painter.drawRoundedRect(
                            int(x - bar_width / 2 + offset),
                            int(min(y, zero_y)),
                            bar_width,
                            bar_height,
                            3, 3
                        )

            # --------------------------------------------------
            # GRAPHIQUE LINÉAIRE
            # --------------------------------------------------

            else:
                for series_index, points in enumerate(points_by_series):
                    color = colors[series_index]
                    painter.setPen(QPen(color, 3))
                    painter.drawPath(self._smooth_path(points))
                    painter.setBrush(QColor("#E4FCFF"))
                    painter.setPen(QPen(color, 1))
                    for x, y in points:
                        painter.drawEllipse(x - 4, y - 4, 8, 8)

            # --------------------------------------------------
            # RÉTICULE ET INFO-BULLE
            # --------------------------------------------------

            if self._hover_index is not None:
                index = self._hover_index
                series_index = self._hover_series_index or 0
                points = points_by_series[series_index]

                if 0 <= index < len(points):
                    px, py = points[index]
                    color = colors[series_index]

                    # Réticule
                    painter.setPen(
                        QPen(
                            color,
                            1,
                            Qt.PenStyle.DashLine
                        )
                    )

                    painter.drawLine(px, top, px, bottom)
                    painter.drawLine(left, py, right, py)

                    # Point sélectionné
                    painter.setBrush(QColor("#FFFFFF"))
                    painter.setPen(
                        QPen(color, 2)
                    )

                    painter.drawEllipse(
                        px - 6, py - 6, 12, 12
                    )

                    # Bulle
                    bubble_width = 175
                    bubble_height = 68 if len(series_data) > 1 else 52

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
                        QPen(color, 1)
                    )

                    painter.setBrush(QColor("#0B202C"))

                    painter.drawRoundedRect(
                        int(bx), int(by),
                        bubble_width, bubble_height,
                        7, 7
                    )

                    x_label = x_display_labels[index]

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

                    value_y = by + 40
                    if len(series_data) > 1:
                        painter.setPen(color)
                        painter.drawText(
                            int(bx + 9), int(value_y),
                            series_data[series_index]["name"][:24]
                        )
                        painter.setPen(QColor("#91BAC5"))
                        value_y += 20
                    painter.drawText(
                        int(bx + 9),
                        int(value_y),
                        f"Y: {series_data[series_index]['display_labels'][index]}"
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

        closest_series_index = None
        for x, y, index, series_index in self._chart_points:
            distance = (
                (mouse_x - x) ** 2
                + (mouse_y - y) ** 2
            )

            if distance < closest_distance:
                closest_distance = distance
                closest_index = index
                closest_series_index = series_index

        if (
            closest_index != self._hover_index
            or closest_series_index != self._hover_series_index
        ):
            self._hover_index = closest_index
            self._hover_series_index = closest_series_index
            self.update()

    def leaveEvent(self, event):
        self._hover_index = None
        self._hover_series_index = None
        self.update()
        super().leaveEvent(event)
