from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from typing import Optional

from PyQt6.QtCore import QPoint, QPointF, QRect, QRectF, Qt
from PyQt6.QtGui import QAction, QColor, QPainter, QPainterPath, QPen, QPolygonF
from PyQt6.QtWidgets import (
    QApplication,
    QColorDialog,
    QLabel,
    QMainWindow,
    QScrollArea,
    QToolBar,
    QVBoxLayout,
    QWidget,
)


class Shape(ABC):
    MIN_SIZE = 10.0

    def __init__(self, center: QPoint | QPointF):
        self.center = QPointF(center)
        self.w = 80.0
        self.h = 80.0
        self.selected = False
        self.fill = QColor("#cde3ff")
        self.border = QColor("#1f3a60")

    def set_selected(self, value: bool) -> None:
        self.selected = value

    def is_selected(self) -> bool:
        return self.selected

    def set_fill(self, color: QColor) -> None:
        self.fill = QColor(color)

    def pen(self) -> QPen:
        return QPen(QColor("#d64545") if self.selected else self.border, 2)

    def set_size(self, w: float, h: float, bounds: QRect) -> None:
        self.w = max(self.MIN_SIZE, w)
        self.h = max(self.MIN_SIZE, h)
        self.keep_inside(bounds)

    def resize(self, delta: float, bounds: QRect) -> None:
        self.set_size(self.w + delta, self.h + delta, bounds)

    def move(self, dx: float, dy: float, bounds: QRect) -> None:
        self.center += QPointF(dx, dy)
        self.keep_inside(bounds)

    def keep_inside(self, bounds: QRect) -> None:
        if bounds.isNull():
            return

        self._clamp_size_to_bounds(bounds)
        self._clamp_position_to_bounds(bounds)

    def _clamp_size_to_bounds(self, bounds: QRect) -> None:
        max_w, max_h = self.max_size_for_bounds(bounds)
        self.w = max(self.MIN_SIZE, min(self.w, max_w))
        self.h = max(self.MIN_SIZE, min(self.h, max_h))

    def _clamp_position_to_bounds(self, bounds: QRect) -> None:
        left, top, right, bottom = self.extents()
        dx = 0.0
        dy = 0.0

        if left < 0:
            dx = -left
        elif right > bounds.width():
            dx = bounds.width() - right

        if top < 0:
            dy = -top
        elif bottom > bounds.height():
            dy = bounds.height() - bottom

        self.center += QPointF(dx, dy)

    @abstractmethod
    def extents(self) -> tuple[float, float, float, float]:
        pass

    @abstractmethod
    def max_size_for_bounds(self, bounds: QRect) -> tuple[float, float]:
        pass

    @abstractmethod
    def bounding_rect(self) -> QRectF:
        pass

    @abstractmethod
    def draw(self, painter: QPainter) -> None:
        pass

    @abstractmethod
    def contains(self, point: QPoint) -> bool:
        pass


class Circle(Shape):
    def __init__(self, center: QPoint | QPointF):
        super().__init__(center)
        self.w = self.h = 90.0

    def extents(self) -> tuple[float, float, float, float]:
        r = self.w / 2
        return self.center.x() - r, self.center.y() - r, self.center.x() + r, self.center.y() + r

    def max_size_for_bounds(self, bounds: QRect) -> tuple[float, float]:
        max_d = min(bounds.width(), bounds.height())
        return max_d, max_d

    def bounding_rect(self) -> QRectF:
        return QRectF(self.center.x() - self.w / 2, self.center.y() - self.h / 2, self.w, self.h)

    def draw(self, painter: QPainter) -> None:
        painter.setPen(self.pen())
        painter.setBrush(self.fill)
        painter.drawEllipse(self.bounding_rect())

    def contains(self, point: QPoint) -> bool:
        dx = point.x() - self.center.x()
        dy = point.y() - self.center.y()
        r = self.w / 2
        return dx * dx + dy * dy <= r * r


class Rectangle(Shape):
    def extents(self) -> tuple[float, float, float, float]:
        return (
            self.center.x() - self.w / 2,
            self.center.y() - self.h / 2,
            self.center.x() + self.w / 2,
            self.center.y() + self.h / 2,
        )

    def max_size_for_bounds(self, bounds: QRect) -> tuple[float, float]:
        return float(bounds.width()), float(bounds.height())

    def bounding_rect(self) -> QRectF:
        return QRectF(self.center.x() - self.w / 2, self.center.y() - self.h / 2, self.w, self.h)

    def draw(self, painter: QPainter) -> None:
        painter.setPen(self.pen())
        painter.setBrush(self.fill)
        painter.drawRect(self.bounding_rect())

    def contains(self, point: QPoint) -> bool:
        return self.bounding_rect().contains(QPointF(point))


class Ellipse(Shape):
    def extents(self) -> tuple[float, float, float, float]:
        return (
            self.center.x() - self.w / 2,
            self.center.y() - self.h / 2,
            self.center.x() + self.w / 2,
            self.center.y() + self.h / 2,
        )

    def max_size_for_bounds(self, bounds: QRect) -> tuple[float, float]:
        # делаем высоту меньше ширины
        return float(bounds.width()), float(bounds.height()) * 0.6

    def bounding_rect(self) -> QRectF:
        return QRectF(
            self.center.x() - self.w / 2,
            self.center.y() - self.h / 2,
            self.w,
            self.h,
        )

    def draw(self, painter: QPainter) -> None:
        painter.setPen(self.pen())
        painter.setBrush(self.fill)

        # защита от круга: если размеры равны — искажаем
        w = self.w
        h = self.h if self.h != self.w else self.w * 0.6

        rect = QRectF(
            self.center.x() - w / 2,
            self.center.y() - h / 2,
            w,
            h,
        )

        painter.drawEllipse(rect)

    def contains(self, point: QPoint) -> bool:
        rx = self.w / 2
        ry = self.h / 2 if self.h != self.w else (self.w * 0.6) / 2

        if rx <= 0 or ry <= 0:
            return False

        dx = (point.x() - self.center.x()) / rx
        dy = (point.y() - self.center.y()) / ry
        return dx * dx + dy * dy <= 1.0


class Triangle(Shape):
    def __init__(self, center: QPoint | QPointF):
        super().__init__(center)
        self.w = 100.0
        self.h = 90.0

    def _points(self) -> QPolygonF:
        top = QPointF(self.center.x(), self.center.y() - self.h / 2)
        left = QPointF(self.center.x() - self.w / 2, self.center.y() + self.h / 2)
        right = QPointF(self.center.x() + self.w / 2, self.center.y() + self.h / 2)
        return QPolygonF([top, left, right])

    def extents(self) -> tuple[float, float, float, float]:
        return (
            self.center.x() - self.w / 2,
            self.center.y() - self.h / 2,
            self.center.x() + self.w / 2,
            self.center.y() + self.h / 2,
        )

    def max_size_for_bounds(self, bounds: QRect) -> tuple[float, float]:
        return float(bounds.width()), float(bounds.height())

    def bounding_rect(self) -> QRectF:
        return QRectF(self.center.x() - self.w / 2, self.center.y() - self.h / 2, self.w, self.h)

    def draw(self, painter: QPainter) -> None:
        painter.setPen(self.pen())
        painter.setBrush(self.fill)
        painter.drawPolygon(self._points())

    def contains(self, point: QPoint) -> bool:
        path = QPainterPath()
        path.addPolygon(self._points())
        return path.contains(QPointF(point))


class Line(Shape):
    def __init__(self, center: QPoint | QPointF):
        super().__init__(center)
        self.w = 120.0
        self.h = 0.0

    def extents(self) -> tuple[float, float, float, float]:
        half = self.w / 2
        return self.center.x() - half, self.center.y() - 2, self.center.x() + half, self.center.y() + 2

    def max_size_for_bounds(self, bounds: QRect) -> tuple[float, float]:
        return float(bounds.width()), 4.0

    def _clamp_size_to_bounds(self, bounds: QRect) -> None:
        max_w, _ = self.max_size_for_bounds(bounds)
        self.w = max(20.0, min(self.w, max_w))
        self.h = 0.0

    def set_size(self, w: float, h: float, bounds: QRect) -> None:
        self.w = max(20.0, w)
        self.h = 0.0
        self.keep_inside(bounds)

    def resize(self, delta: float, bounds: QRect) -> None:
        self.set_size(self.w + delta, 0, bounds)

    def bounding_rect(self) -> QRectF:
        return QRectF(self.center.x() - self.w / 2, self.center.y() - 2, self.w, 4)

    def draw(self, painter: QPainter) -> None:
        painter.setPen(self.pen())
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(
            int(self.center.x() - self.w / 2),
            int(self.center.y()),
            int(self.center.x() + self.w / 2),
            int(self.center.y()),
        )

    def contains(self, point: QPoint) -> bool:
        x1 = self.center.x() - self.w / 2
        x2 = self.center.x() + self.w / 2
        px, py = point.x(), point.y()
        if px < min(x1, x2) - 4 or px > max(x1, x2) + 4:
            return False
        return abs(py - self.center.y()) <= 5


class ShapeStorage:
    def __init__(self):
        self.items: list[Shape] = []

    def add(self, shape: Shape) -> None:
        self.items.append(shape)

    def all(self) -> list[Shape]:
        return self.items

    def clear_selection(self) -> None:
        for s in self.items:
            s.set_selected(False)

    def selected(self) -> list[Shape]:
        return [s for s in self.items if s.is_selected()]

    def remove_selected(self) -> None:
        self.items = [s for s in self.items if not s.is_selected()]

    def hit_test(self, point: QPoint) -> Optional[Shape]:
        for s in reversed(self.items):
            if s.contains(point):
                return s
        return None


class Canvas(QWidget):
    def __init__(self, storage: ShapeStorage, status: QLabel):
        super().__init__()
        self.storage = storage
        self.status = status
        self.current_tool = "circle"
        self.current_color = QColor("#cde3ff")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def shape_factory(self, kind: str, center: QPoint) -> Shape:
        if kind == "circle":
            return Circle(center)
        if kind == "rect":
            return Rectangle(center)
        if kind == "ellipse":
            return Ellipse(center)
        if kind == "triangle":
            return Triangle(center)
        if kind == "line":
            return Line(center)
        return Circle(center)

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor("#fafafa"))
        for s in self.storage.all():
            s.draw(painter)

    def mousePressEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return

        ctrl = bool(e.modifiers() & Qt.KeyboardModifier.ControlModifier)
        point = e.position().toPoint()
        shape = self.storage.hit_test(point)

        if shape:
            if not ctrl:
                self.storage.clear_selection()
            shape.set_selected(not shape.is_selected())
        else:
            if not ctrl:
                self.storage.clear_selection()
            new_shape = self.shape_factory(self.current_tool, point)
            new_shape.set_fill(self.current_color)
            new_shape.keep_inside(self.rect())
            self.storage.add(new_shape)

        self.update_status()
        self.update()

    def keyPressEvent(self, e):
        bounds = self.rect()
        selected = self.storage.selected()

        if e.key() == Qt.Key.Key_Delete:
            self.storage.remove_selected()

        elif e.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            move_step = 5
            if e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                move_step = 15

            if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
                delta = 10 if e.key() in (Qt.Key.Key_Right, Qt.Key.Key_Down) else -10
                for s in selected:
                    s.resize(delta, bounds)
            else:
                dx = dy = 0
                if e.key() == Qt.Key.Key_Left:
                    dx = -move_step
                elif e.key() == Qt.Key.Key_Right:
                    dx = move_step
                elif e.key() == Qt.Key.Key_Up:
                    dy = -move_step
                elif e.key() == Qt.Key.Key_Down:
                    dy = move_step
                for s in selected:
                    s.move(dx, dy, bounds)

        elif e.key() in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            for s in selected:
                s.resize(10, bounds)

        elif e.key() == Qt.Key.Key_Minus:
            for s in selected:
                s.resize(-10, bounds)

        elif e.key() == Qt.Key.Key_C:
            self.change_selected_color()

        self.update_status()
        self.update()

    def change_selected_color(self):
        color = QColorDialog.getColor(self.current_color, self, "Выбор цвета")
        if color.isValid():
            self.current_color = color
            for s in self.storage.selected():
                s.set_fill(color)

    def update_status(self):
        tool_names = {
            "circle": "круг",
            "rect": "прямоугольник",
            "ellipse": "эллипс",
            "triangle": "треугольник",
            "line": "отрезок",
        }
        self.status.setText(
            f"Всего: {len(self.storage.all())} | Выделено: {len(self.storage.selected())} | "
            f"Инструмент: {tool_names.get(self.current_tool, self.current_tool)}"
        )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ЛР4 — Визуальный редактор векторных объектов (PyQt6)")
        self.resize(1000, 700)

        self.status = QLabel()
        self.storage = ShapeStorage()
        self.canvas = Canvas(self.storage, self.status)

        self.canvas.setMinimumSize(3000, 2000)

        scroll_area = QScrollArea()
        scroll_area.setWidget(self.canvas)
        scroll_area.setWidgetResizable(False)

        layout = QVBoxLayout()
        layout.addWidget(self.status)
        layout.addWidget(scroll_area)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.create_toolbar()
        self.create_menu()
        self.canvas.update_status()

    def create_action(self, text: str, tool_name: str):
        action = QAction(text, self)
        action.triggered.connect(lambda: self.set_tool(tool_name))
        return action

    def set_tool(self, name: str):
        self.canvas.current_tool = name
        self.canvas.update_status()
        self.canvas.setFocus()

    def create_toolbar(self):
        toolbar = QToolBar("Инструменты")
        self.addToolBar(toolbar)

        toolbar.addAction(self.create_action("Круг", "circle"))
        toolbar.addAction(self.create_action("Прямоугольник", "rect"))
        toolbar.addAction(self.create_action("Эллипс", "ellipse"))
        toolbar.addAction(self.create_action("Треугольник", "triangle"))
        toolbar.addAction(self.create_action("Отрезок", "line"))

        color_action = QAction("Цвет", self)
        color_action.triggered.connect(self.canvas.change_selected_color)
        toolbar.addAction(color_action)

    def create_menu(self):
        shape_menu = self.menuBar().addMenu("Фигуры")
        shape_menu.addAction(self.create_action("Круг", "circle"))
        shape_menu.addAction(self.create_action("Прямоугольник", "rect"))
        shape_menu.addAction(self.create_action("Эллипс", "ellipse"))
        shape_menu.addAction(self.create_action("Треугольник", "triangle"))
        shape_menu.addAction(self.create_action("Отрезок", "line"))

        edit_menu = self.menuBar().addMenu("Правка")
        color_action = QAction("Изменить цвет выбранных", self)
        color_action.triggered.connect(self.canvas.change_selected_color)
        delete_action = QAction("Удалить выбранные", self)
        delete_action.triggered.connect(self.delete_selected)
        edit_menu.addAction(color_action)
        edit_menu.addAction(delete_action)

    def delete_selected(self):
        self.storage.remove_selected()
        self.canvas.update_status()
        self.canvas.update()
        self.canvas.setFocus()


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()