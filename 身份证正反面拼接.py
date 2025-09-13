import sys
import os
import hashlib
import wmi
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QWidget, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, QMimeData, QBuffer, QIODevice
from PyQt5.QtGui import QPixmap, QImage, QTransform, QFont
from PIL import Image
import io

class ImagePreview(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setText("拖放图片到这里或点击上传")
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                min-height: 300px;
            }
        """)
        self.original_pixmap = None
        self.rotation_angle = 0
        self.original_size = None
        
    def setPixmap(self, pixmap):
        self.original_pixmap = pixmap
        self.original_size = pixmap.size()
        self.rotation_angle = 0
        self.update_display()
        
    def rotate(self, angle):
        if self.original_pixmap is not None:
            self.rotation_angle = (self.rotation_angle + angle) % 360
            self.update_display()
            
    def update_display(self):
        if self.original_pixmap is None:
            return
            
        transform = QTransform().rotate(self.rotation_angle)
        rotated_pixmap = self.original_pixmap.transformed(transform, Qt.SmoothTransformation)
        
        # 保持原始比例缩放
        scaled_pixmap = rotated_pixmap.scaled(
            self.width(), 
            self.height(), 
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        super().setPixmap(scaled_pixmap)
            
    def get_image(self):
        if self.original_pixmap is None:
            return None
            
        # 获取旋转后的图像
        transform = QTransform().rotate(self.rotation_angle)
        rotated_pixmap = self.original_pixmap.transformed(transform, Qt.SmoothTransformation)
        
        # 转换为QImage
        qimage = rotated_pixmap.toImage()
        
        # 将QImage转换为PIL Image
        buffer = QBuffer()
        buffer.open(QIODevice.ReadWrite)
        qimage.save(buffer, "PNG")
        
        pil_image = Image.open(io.BytesIO(buffer.data()))
        buffer.close()
        
        return pil_image
    
    def resizeEvent(self, event):
        self.update_display()
        super().resizeEvent(event)


class IDCardMerger(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("身份证正反面拼接")
        
        # 设置窗体大小并居中
        self.resize(1000, 800)
        self.center_window()
        
        # 创建主部件和布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_widget.setLayout(main_layout)
        
        # 创建预览区域
        self.front_preview = ImagePreview()
        self.back_preview = ImagePreview()
        
        # 创建按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.front_upload_btn = QPushButton("上传正面")
        self.front_upload_btn.setFixedHeight(40)
        self.front_upload_btn.clicked.connect(lambda: self.upload_image(self.front_preview))
        
        self.back_upload_btn = QPushButton("上传反面")
        self.back_upload_btn.setFixedHeight(40)
        self.back_upload_btn.clicked.connect(lambda: self.upload_image(self.back_preview))
        
        self.front_rotate_btn = QPushButton("旋转正面")
        self.front_rotate_btn.setFixedHeight(40)
        self.front_rotate_btn.clicked.connect(lambda: self.front_preview.rotate(90))
        
        self.back_rotate_btn = QPushButton("旋转反面")
        self.back_rotate_btn.setFixedHeight(40)
        self.back_rotate_btn.clicked.connect(lambda: self.back_preview.rotate(90))
        
        self.merge_btn = QPushButton("合并保存")
        self.merge_btn.setFixedHeight(40)
        self.merge_btn.clicked.connect(self.merge_and_save)
        
        button_layout.addWidget(self.front_upload_btn)
        button_layout.addWidget(self.front_rotate_btn)
        button_layout.addWidget(self.back_upload_btn)
        button_layout.addWidget(self.back_rotate_btn)
        button_layout.addWidget(self.merge_btn)
        
        # 添加到主布局
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        
        front_label = QLabel("身份证正面")
        front_label.setFont(title_font)
        back_label = QLabel("身份证反面")
        back_label.setFont(title_font)
        
        main_layout.addWidget(front_label)
        main_layout.addWidget(self.front_preview)
        main_layout.addWidget(back_label)
        main_layout.addWidget(self.back_preview)
        main_layout.addLayout(button_layout)
        
        # 添加底部版权信息
        copyright_frame = QWidget()
        copyright_frame.setStyleSheet("background-color: yellow;")
        copyright_layout = QHBoxLayout()
        copyright_frame.setLayout(copyright_layout)
        
        copyright_text = "速光网络软件开发 关注抖音号：dubaishun12 获取更多软件"
        copyright_label = QLabel(copyright_text)
        copyright_label.setStyleSheet("background-color: yellow;")
        copyright_font = QFont("微软雅黑", 10)
        copyright_label.setFont(copyright_font)
        
        copyright_layout.addStretch()
        copyright_layout.addWidget(copyright_label)
        copyright_layout.addStretch()
        
        main_layout.addWidget(copyright_frame)
        
        # 启用拖放
        self.setAcceptDrops(True)
        self.front_preview.setAcceptDrops(True)
        self.back_preview.setAcceptDrops(True)
    
    def center_window(self):
        frame = self.frameGeometry()
        center_point = QApplication.desktop().availableGeometry().center()
        frame.moveCenter(center_point)
        self.move(frame.topLeft())
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            
            # 判断拖放到哪个预览区域
            pos = event.pos()
            front_rect = self.front_preview.geometry()
            back_rect = self.back_preview.geometry()
            
            if front_rect.contains(pos):
                self.load_image_to_preview(file_path, self.front_preview)
            elif back_rect.contains(pos):
                self.load_image_to_preview(file_path, self.back_preview)
                
    def upload_image(self, preview_widget):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_path:
            self.load_image_to_preview(file_path, preview_widget)
            
    def load_image_to_preview(self, file_path, preview_widget):
        try:
            pixmap = QPixmap(file_path)
            if pixmap.isNull():
                raise ValueError("无法加载图片")
                
            preview_widget.setPixmap(pixmap)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法加载图片: {str(e)}")
            
    def merge_and_save(self):
        try:
            front_image = self.front_preview.get_image()
            back_image = self.back_preview.get_image()
            
            if front_image is None and back_image is None:
                QMessageBox.warning(self, "警告", "请至少上传一张图片")
                return
                
            save_path, _ = QFileDialog.getSaveFileName(
                self, "保存图片", "", "图片文件 (*.png *.jpg *.jpeg)"
            )
            
            if not save_path:  # 用户取消了保存
                return
                
            # 如果只有一张图片，直接保存
            if front_image is None or back_image is None:
                image_to_save = front_image if front_image is not None else back_image
                image_to_save.save(save_path, quality=95)
                QMessageBox.information(self, "成功", "图片保存成功")
                return
                
            # 合并两张图片 - 以正面图片宽度为准
            front_width = front_image.width
            front_height = front_image.height
            
            # 计算反面图片的新高度（保持比例）
            back_ratio = back_image.height / back_image.width
            new_back_height = int(front_width * back_ratio)
            
            # 调整图片大小
            front_image = front_image.resize((front_width, front_height))
            back_image = back_image.resize((front_width, new_back_height))
            
            # 创建新图像
            total_height = front_height + new_back_height
            merged_image = Image.new('RGB', (front_width, total_height))
            
            merged_image.paste(front_image, (0, 0))
            merged_image.paste(back_image, (0, front_height))
            
            # 保存高质量图片
            merged_image.save(save_path, quality=95)
            #QMessageBox.information(self, "成功", f"图片合并保存成功\n尺寸: {front_width}x{total_height}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"操作失败: {str(e)}")


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = IDCardMerger()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        QMessageBox.critical(None, "错误", f"程序启动失败: {str(e)}")
        sys.exit(1)