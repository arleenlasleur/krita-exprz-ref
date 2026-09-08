import os
from krita import Krita, Extension, DockWidget, DockWidgetFactory, DockWidgetFactoryBase
from PyQt5.QtCore import Qt, QPointF, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene, QFileDialog, QSpinBox, QLabel, QPushButton
from PyQt5.QtGui import QPixmap, QTransform

class ExactReferenceWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # GUI
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(1, 1, 1, 1)
        self.layout.setSpacing(2)
        self.toolbarLayout = QHBoxLayout()
        self.toolbarLayout.setContentsMargins(0, 0, 0, 0)
        self.toolbarLayout.setSpacing(2)

        # DPI controls
        self.srcLabel = QLabel("Src DPI:", self)
        self.srcDpiBox = QSpinBox(self)
        self.srcDpiBox.setRange(1, 999)
        self.srcDpiBox.setValue(72)
        self.srcDpiBox.setFixedWidth(75) # Keep input field compact
        self.tgtLabel = QLabel("Targ DPI:", self)
        self.tgtDpiBox = QSpinBox(self)
        self.tgtDpiBox.setRange(1, 999)
        self.tgtDpiBox.setValue(72)
        self.tgtDpiBox.setFixedWidth(75) # Keep input field compact

        # Control buttons setup
        self.loadBtn = QPushButton("Load", self)
        self.pasteBtn = QPushButton("Paste", self)
        self.realignBtn = QPushButton("Realign", self)
        self.clearBtn = QPushButton("Clear", self)

        # Add to layout
        self.toolbarLayout.addWidget(self.srcLabel)
        self.toolbarLayout.addWidget(self.srcDpiBox)
        self.toolbarLayout.addWidget(self.tgtLabel)
        self.toolbarLayout.addWidget(self.tgtDpiBox)
        self.toolbarLayout.addWidget(self.loadBtn)
        self.toolbarLayout.addWidget(self.pasteBtn)
        self.toolbarLayout.addWidget(self.realignBtn)
        self.toolbarLayout.addWidget(self.clearBtn)
        self.layout.addLayout(self.toolbarLayout)

        # Graphics View and Scene Setup
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene, self)
        self.view.setStyleSheet("background-color: #222; border: 1px solid #444;")
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.layout.addWidget(self.view)

        # Init
        self.pixmap_item = None
        self.originalPixmap = QPixmap()
        
        # Manual Panning Variables
        self.manual_offset = QPointF(0, 0)
        self.last_mouse_pos = QPointF(0, 0)
        self.is_dragging = False
        
        # UI signals
        self.srcDpiBox.valueChanged.connect(self.update_transform)
        self.tgtDpiBox.valueChanged.connect(self.update_transform)
        self.loadBtn.clicked.connect(self.load_reference_image)
        self.pasteBtn.clicked.connect(self.load_from_clipboard)
        self.realignBtn.clicked.connect(self.force_realign)
        self.clearBtn.clicked.connect(self.clear_reference)
        
        # Mouse input
        self.view.mousePressEvent = self.view_mouse_press
        self.view.mouseMoveEvent = self.view_mouse_move
        self.view.mouseReleaseEvent = self.view_mouse_release

    def view_mouse_press(self, event):
        if event.button() == Qt.LeftButton and self.pixmap_item:
            self.is_dragging = True
            self.last_mouse_pos = event.pos()
            event.accept()

    def view_mouse_move(self, event):
        if self.is_dragging and self.pixmap_item:
            delta = event.pos() - self.last_mouse_pos
            self.manual_offset += QPointF(delta.x(), delta.y())
            self.last_mouse_pos = event.pos()
            self.update_transform()
            event.accept()

    def view_mouse_release(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = False
            event.accept()

    def load_reference_image(self):
        filePath, _ = QFileDialog.getOpenFileName(self, "Select reference", "", "Images (*.png *.jpg *.jpeg)")
        if filePath:
            self.set_reference_pixmap(QPixmap(filePath))

    def load_from_clipboard(self):
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        
        if mime_data.hasImage():
            image = clipboard.image()
            pixmap = QPixmap.fromImage(image)
            if not pixmap.isNull():
                self.set_reference_pixmap(pixmap)
        else:
            if mime_data.hasUrls():
                for url in mime_data.urls():
                    filePath = str(url.toLocalFile())
                    if os.path.exists(filePath) and filePath.lower().endswith(('.png', '.jpg', '.jpeg')):
                        self.set_reference_pixmap(QPixmap(filePath))
                        break

    def set_reference_pixmap(self, pixmap):
        self.originalPixmap = pixmap
        self.scene.clear()
        if not self.originalPixmap.isNull():
            self.pixmap_item = self.scene.addPixmap(self.originalPixmap)
            self.pixmap_item.setTransformOriginPoint(0, 0)
            self.manual_offset = QPointF(0, 0)
            self.update_transform()

    def clear_reference(self):
        self.originalPixmap = QPixmap()
        self.scene.clear()
        self.pixmap_item = None
        self.manual_offset = QPointF(0, 0)

    def force_realign(self):
        self.manual_offset = QPointF(0, 0)
        self.view.setTransform(QTransform())
        self.update_transform()

    def update_transform(self):
        if self.originalPixmap.isNull() or not self.pixmap_item:
            return
            
        window = Krita.instance().activeWindow()
        if not window: return
        view = window.activeView()
        if not view: return
        
        try:
            canvas = view.canvas()
            if canvas is None: return
            doc = Krita.instance().activeDocument()
            if not doc: return
            
            zoom = canvas.zoomLevel()
            rotation = canvas.rotation()
            is_mirrored = canvas.mirror()
            flake_to_canvas = view.flakeToCanvasTransform()
        except (AttributeError, RuntimeError):
            return

        src_dpi = max(1, self.srcDpiBox.value())
        tgt_dpi = max(1, self.tgtDpiBox.value())
        dpi_scale = tgt_dpi / src_dpi
        final_scale = zoom * dpi_scale

        doc_center_flake = QPointF(doc.width() / 2.0, doc.height() / 2.0)
        pan_offset = flake_to_canvas.map(doc_center_flake)

        self.view.setTransform(QTransform())
        t = QTransform()
        
        t.translate(self.view.width() / 2.0, self.view.height() / 2.0)
        t.translate(self.manual_offset.x(), self.manual_offset.y())
        
        dx = pan_offset.x()
        dy = pan_offset.y()
        if is_mirrored:
            dx = -dx
            
        t.translate(dx, dy)
        
        if is_mirrored:
            t.scale(-1, 1)
            
        t.rotate(rotation)
        t.scale(final_scale, final_scale)
        t.translate(-self.originalPixmap.width() / 2.0, -self.originalPixmap.height() / 2.0)
        
        self.pixmap_item.setTransform(t)

class ExactReferenceDocker(DockWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Exact Area Reference")
        self.setObjectName("exact_prz_ref_docker")
        
        self.refWidget = ExactReferenceWidget(self)
        self.setWidget(self.refWidget)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.safe_sync)
        self.timer.start(25)

    def safe_sync(self):
        if hasattr(self, 'refWidget') and self.refWidget:
            self.refWidget.update_transform()

    def canvasChanged(self, canvas):
        self.safe_sync()

    def closeEvent(self, event):
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
        super().closeEvent(event)

class ExactReferencePlugin(Extension):
    def __init__(self, parent):
        super().__init__(parent)
    def setup(self): pass
    def createActions(self, window): pass

Krita.instance().addDockWidgetFactory(
    DockWidgetFactory(
        "exact_prz_ref_docker",
        DockWidgetFactoryBase.DockRight,
        ExactReferenceDocker
    )
)

Krita.instance().addExtension(ExactReferencePlugin(Krita.instance()))
