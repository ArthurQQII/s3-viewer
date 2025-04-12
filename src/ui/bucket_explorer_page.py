from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QTableWidget,
                             QTableWidgetItem, QHeaderView, QMessageBox,
                             QFileDialog, QDialog, QPlainTextEdit, QProgressDialog,
                             QMenu, QSlider)
from PyQt6.QtCore import pyqtSignal, Qt, QUrl
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
import os
from datetime import datetime
import tempfile
import mimetypes
import json
from src.utils.aws_utils import get_s3_client, list_objects, get_object_metadata, download_file
from src.ui.loading_animation import LoadingAnimation
from PyQt6.QtWidgets import QApplication

class BucketExplorerPage(QWidget):
    back_to_buckets = pyqtSignal()  # Signal for returning to bucket list
    invalid_credentials = pyqtSignal()  # Signal for invalid credentials
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.s3_client = None
        self.current_bucket = None
        self.current_prefix = ""
        self.total_objects = []
        self.current_page = 1
        self.page_size = 100  # Changed from 1000 to 100 items per page
        self.total_pages = 1
        self.total_items = 0
        self.sort_column = 0  # Default sort column
        self.sort_order = Qt.SortOrder.AscendingOrder  # Default sort order
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface"""
        layout = QVBoxLayout()
        
        # Top bar with back button and breadcrumb
        top_bar = QHBoxLayout()
        
        # Back button on the left
        self.back_button = QPushButton("← Back to Buckets")
        self.back_button.clicked.connect(lambda: self.back_to_buckets.emit())
        self.back_button.setMaximumWidth(150)  # Limit width
        top_bar.addWidget(self.back_button)
        
        # Add some spacing
        top_bar.addSpacing(20)
        
        # Breadcrumb navigation
        self.breadcrumb_layout = QHBoxLayout()
        self.breadcrumb_layout.addWidget(QLabel("Path:"))
        self.breadcrumb_layout.addWidget(QLabel("root"))
        self.breadcrumb_layout.addStretch()
        top_bar.addLayout(self.breadcrumb_layout)
        
        layout.addLayout(top_bar)
        
        # Object table
        self.object_table = QTableWidget()
        self.object_table.setColumnCount(4)
        self.object_table.setHorizontalHeaderLabels(["Name", "Size", "Last Modified", "Content Type"])
        self.object_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.object_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.object_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.object_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.object_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.object_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.object_table.customContextMenuRequested.connect(self.show_context_menu)
        self.object_table.itemDoubleClicked.connect(self.on_object_double_clicked)
        self.object_table.horizontalHeader().sectionClicked.connect(self.on_header_clicked)  # Add sorting
        layout.addWidget(self.object_table)
        
        # Pagination controls
        pagination_layout = QHBoxLayout()
        self.prev_button = QPushButton("Previous")
        self.next_button = QPushButton("Next")
        self.page_info = QLabel("Page 1 of 1 (0 items)")
        self.prev_button.clicked.connect(self.previous_page)
        self.next_button.clicked.connect(self.next_page)
        pagination_layout.addWidget(self.prev_button)
        pagination_layout.addWidget(self.page_info)
        pagination_layout.addWidget(self.next_button)
        pagination_layout.addStretch()
        layout.addLayout(pagination_layout)
        
        # Add loading animation
        self.loading_animation = LoadingAnimation(self, "Loading objects...")
        self.loading_animation.setVisible(False)
        layout.addWidget(self.loading_animation)
        
        self.setLayout(layout)
    
    def set_bucket(self, bucket_name):
        """Set the current bucket and load its contents"""
        self.current_bucket = bucket_name
        self.current_prefix = ""
        self.update_breadcrumb()
        self.load_objects()
    
    def set_session(self, session):
        """Set the AWS session"""
        try:
            self.loading_animation.setText("Setting up AWS session...")
            self.loading_animation.setVisible(True)
            self.s3_client = get_s3_client(session)
            if self.current_bucket:
                self.load_objects()
        except Exception as e:
            QMessageBox.warning(
                self,
                "Invalid Credentials",
                "Your AWS credentials have expired or are invalid.\n\n"
                "Please re-login using AWS CLI:\n"
                "aws configure --profile your-profile-name\n\n"
                "Or refresh your credentials if using temporary credentials."
            )
            # Emit signal to return to credential page
            self.invalid_credentials.emit()
            return
        finally:
            self.loading_animation.setVisible(False)
    
    def update_breadcrumb(self):
        """Update the breadcrumb navigation with clickable parts"""
        # Clear existing breadcrumb
        while self.breadcrumb_layout.count():
            item = self.breadcrumb_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add bucket
        bucket_btn = QPushButton(self.current_bucket)
        bucket_btn.setStyleSheet("border: none; text-align: left; padding: 0px;")
        bucket_btn.clicked.connect(lambda: self.navigate_to(""))
        self.breadcrumb_layout.addWidget(bucket_btn)
        
        # Add separator
        if self.current_prefix:
            self.breadcrumb_layout.addWidget(QLabel("/"))
        
        # Add path parts
        current_path = ""
        if self.current_prefix:
            parts = self.current_prefix.rstrip('/').split('/')
            for i, part in enumerate(parts):
                if part:  # Skip empty parts
                    current_path += part + '/'
                    path_btn = QPushButton(part)
                    path_btn.setStyleSheet("border: none; text-align: left; padding: 0px;")
                    # Create a new function to avoid lambda capture issues
                    def make_click_handler(p):
                        return lambda: self.navigate_to(p)
                    path_btn.clicked.connect(make_click_handler(current_path))
                    self.breadcrumb_layout.addWidget(path_btn)
                    if i < len(parts) - 1:
                        self.breadcrumb_layout.addWidget(QLabel("/"))
        
        self.breadcrumb_layout.addStretch()
    
    def navigate_to(self, prefix):
        """Navigate to a specific prefix when clicking breadcrumb"""
        self.loading_animation.setText(f"Navigating to {prefix}...")
        self.loading_animation.setVisible(True)
        self.current_prefix = prefix
        self.load_objects()
    
    def load_objects(self):
        """Load objects from the current bucket and prefix"""
        try:
            self.loading_animation.setText(f"Loading objects from {self.current_bucket}/{self.current_prefix}")
            self.loading_animation.setVisible(True)
            QApplication.processEvents()  # Force UI update
            
            response = list_objects(self.s3_client, self.current_bucket, self.current_prefix)
            
            self.total_objects = []
            
            # Add folders (CommonPrefixes)
            if 'CommonPrefixes' in response:
                for prefix in response['CommonPrefixes']:
                    folder_name = prefix['Prefix']
                    self.total_objects.append({
                        'Key': folder_name,
                        'Size': 0,
                        'LastModified': None,
                        'ContentType': 'folder',
                        'is_folder': True
                    })
            
            # Add files
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    # Skip the current prefix itself
                    if key != self.current_prefix:
                        # Get content type
                        try:
                            head_response = get_object_metadata(self.s3_client, self.current_bucket, key)
                            content_type = head_response.get('ContentType', 'N/A')
                        except:
                            content_type = 'N/A'
                        
                        self.total_objects.append({
                            'Key': key,
                            'Size': obj['Size'],
                            'LastModified': obj['LastModified'],
                            'ContentType': content_type,
                            'is_folder': False
                        })
            
            # Update total items and pages
            self.total_items = len(self.total_objects)
            self.total_pages = (self.total_items + self.page_size - 1) // self.page_size
            self.current_page = 1  # Reset to first page when entering a new folder
            
            self.sort_objects()
            self.update_object_table()
            self.update_pagination_info()
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Invalid Credentials",
                "Your AWS credentials have expired or are invalid.\n\n"
                "Please re-login using AWS CLI:\n"
                "aws configure --profile your-profile-name\n\n"
                "Or refresh your credentials if using temporary credentials."
            )
            # Emit signal to return to credential page
            self.invalid_credentials.emit()
            return
        finally:
            self.loading_animation.setVisible(False)
            QApplication.processEvents()  # Force UI update
    
    def update_object_table(self):
        """Update the object table with current page data"""
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = start_idx + self.page_size
        current_objects = self.total_objects[start_idx:end_idx]
        
        self.object_table.setRowCount(len(current_objects))
        for i, obj in enumerate(current_objects):
            # Name column
            name = obj['Key'][len(self.current_prefix):].rstrip('/')
            if obj['is_folder']:
                name = f"📁 {name}"
            else:
                name = f"📄 {name}"
            self.object_table.setItem(i, 0, QTableWidgetItem(name))
            
            # Size column
            if obj['Size']:
                size = self.format_size(obj['Size'])
            else:
                size = ""
            self.object_table.setItem(i, 1, QTableWidgetItem(size))
            
            # Last Modified column
            if obj['LastModified']:
                modified = obj['LastModified'].strftime('%Y-%m-%d %H:%M:%S')
            else:
                modified = ""
            self.object_table.setItem(i, 2, QTableWidgetItem(modified))
            
            # Content Type column
            content_type = obj['ContentType']
            if content_type == 'folder':
                content_type = 'Directory'
            self.object_table.setItem(i, 3, QTableWidgetItem(content_type))
    
    def format_size(self, size_bytes):
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    
    def format_time(self, ms):
        """Format milliseconds into MM:SS format"""
        s = ms // 1000
        m = s // 60
        s = s % 60
        return f"{m:02d}:{s:02d}"
    
    def show_context_menu(self, position):
        """Show context menu for object actions"""
        menu = QMenu()
        download_action = menu.addAction("Download")
        preview_action = menu.addAction("Preview")
        
        action = menu.exec(self.object_table.mapToGlobal(position))
        
        if action == download_action:
            self.download_file()
        elif action == preview_action:
            selected_items = self.object_table.selectedItems()
            if selected_items:
                row = selected_items[0].row()
                obj = self.total_objects[(self.current_page - 1) * self.page_size + row]
                self.preview_object(obj)
    
    def download_file(self):
        """Download the selected file"""
        selected_items = self.object_table.selectedItems()
        if not selected_items:
            return
        
        row = selected_items[0].row()
        obj = self.total_objects[(self.current_page - 1) * self.page_size + row]
        
        if obj['is_folder']:
            self.download_folder()
            return
        
        # Get file name from key
        file_name = os.path.basename(obj['Key'])
        
        # Ask user where to save the file
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save File",
            file_name,
            "All Files (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            self.loading_animation.setText(f"Downloading {file_name}...")
            self.loading_animation.setVisible(True)
            QApplication.processEvents()  # Force UI update
            
            # Download the file
            download_file(self.s3_client, self.current_bucket, obj['Key'], file_path)
            
            QMessageBox.information(
                self,
                "Download Complete",
                f"File downloaded successfully to:\n{file_path}"
            )
        except Exception as e:
            QMessageBox.warning(
                self,
                "Download Failed",
                f"Failed to download file: {str(e)}"
            )
        finally:
            self.loading_animation.setVisible(False)
            QApplication.processEvents()  # Force UI update
    
    def download_folder(self):
        """Download the selected folder"""
        selected_items = self.object_table.selectedItems()
        if not selected_items:
            return
        
        row = selected_items[0].row()
        obj = self.total_objects[(self.current_page - 1) * self.page_size + row]
        
        if not obj['is_folder']:
            self.download_file()
            return
        
        # Get folder name from key
        folder_name = os.path.basename(obj['Key'].rstrip('/'))
        
        # Ask user where to save the folder
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Directory to Save Folder",
            os.path.expanduser("~")
        )
        
        if not folder_path:
            return
        
        # Create folder path
        save_path = os.path.join(folder_path, folder_name)
        os.makedirs(save_path, exist_ok=True)
        
        try:
            self.loading_animation.setText(f"Downloading folder {folder_name}...")
            self.loading_animation.setVisible(True)
            QApplication.processEvents()  # Force UI update
            
            # List all objects in the folder
            prefix = obj['Key']
            response = list_objects(self.s3_client, self.current_bucket, prefix)
            
            if 'Contents' not in response:
                QMessageBox.information(
                    self,
                    "Download Complete",
                    f"Folder downloaded successfully to:\n{save_path}"
                )
                return
            
            # Count total files
            total_files = len(response['Contents'])
            downloaded_files = 0
            
            # Download each file
            for obj in response['Contents']:
                key = obj['Key']
                file_name = os.path.basename(key)
                local_path = os.path.join(save_path, file_name)
                
                # Skip if it's a folder
                if key.endswith('/'):
                    continue
                
                # Update loading animation text
                self.loading_animation.setText(f"Downloading {file_name} ({downloaded_files + 1}/{total_files})...")
                QApplication.processEvents()  # Force UI update
                
                # Download the file
                download_file(self.s3_client, self.current_bucket, key, local_path)
                
                # Update progress
                downloaded_files += 1
            
            QMessageBox.information(
                self,
                "Download Complete",
                f"Folder downloaded successfully to:\n{save_path}"
            )
        except Exception as e:
            QMessageBox.warning(
                self,
                "Download Failed",
                f"Failed to download folder: {str(e)}"
            )
        finally:
            self.loading_animation.setVisible(False)
            QApplication.processEvents()  # Force UI update
    
    def update_pagination_info(self):
        """Update pagination information display"""
        self.page_info.setText(f"Page {self.current_page} of {self.total_pages} ({self.total_items} items)")
        self.prev_button.setEnabled(self.current_page > 1)
        self.next_button.setEnabled(self.current_page < self.total_pages)
    
    def go_back(self):
        """Go back to the parent folder"""
        if self.current_prefix:
            parent_prefix = os.path.dirname(self.current_prefix.rstrip('/'))
            if parent_prefix:
                parent_prefix += '/'
            self.current_prefix = parent_prefix
            self.load_objects()
        else:
            self.back_to_buckets.emit()
    
    def previous_page(self):
        """Go to the previous page"""
        if self.current_page > 1:
            self.loading_animation.setText(f"Loading page {self.current_page - 1}...")
            self.loading_animation.setVisible(True)
            self.current_page -= 1
            self.update_object_table()
            self.update_pagination_info()
            self.loading_animation.setVisible(False)
    
    def next_page(self):
        """Go to the next page"""
        if self.current_page < self.total_pages:
            self.loading_animation.setText(f"Loading page {self.current_page + 1}...")
            self.loading_animation.setVisible(True)
            self.current_page += 1
            self.update_object_table()
            self.update_pagination_info()
            self.loading_animation.setVisible(False)
    
    def on_object_double_clicked(self, item):
        """Handle object double-click"""
        row = item.row()
        obj = self.total_objects[(self.current_page - 1) * self.page_size + row]
        
        if obj['is_folder']:
            # Navigate into folder
            self.current_prefix = obj['Key']
            self.load_objects()
        else:
            # Preview file
            self.preview_object(obj)
    
    def preview_object(self, obj):
        """Preview the selected object"""
        if obj['is_folder']:
            return

        content_type = obj['ContentType']
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Preview: {os.path.basename(obj['Key'])}")
        dialog.setMinimumSize(800, 600)
        
        layout = QVBoxLayout()
        
        content_type_label = QLabel(f"Content Type: {content_type}")
        layout.addWidget(content_type_label)
        
        if content_type.startswith('image/'):
            # Image preview
            try:
                # Download to temp file
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_path = temp_file.name
                
                download_file(self.s3_client, self.current_bucket, obj['Key'], temp_path)
                
                # Load image
                pixmap = QPixmap(temp_path)
                
                # Scale to fit dialog
                scaled_pixmap = pixmap.scaled(
                    dialog.width() - 40,
                    dialog.height() - 100,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                # Display image
                image_label = QLabel()
                image_label.setPixmap(scaled_pixmap)
                image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(image_label)
                
                # Clean up temp file
                os.unlink(temp_path)
            except Exception as e:
                error_label = QLabel(f"Failed to load image: {str(e)}")
                layout.addWidget(error_label)
        elif content_type.startswith('video/'):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(obj['Key'])[1]) as temp_file:
                    temp_path = temp_file.name
                
                download_file(self.s3_client, self.current_bucket, obj['Key'], temp_path)
                
                video_widget = QVideoWidget()
                layout.addWidget(video_widget)
                
                media_player = QMediaPlayer()
                audio_output = QAudioOutput()
                media_player.setAudioOutput(audio_output)
                media_player.setVideoOutput(video_widget)
                media_player.setSource(QUrl.fromLocalFile(temp_path))
                
                # Add controls
                controls_layout = QHBoxLayout()
                
                play_button = QPushButton("Play")
                play_button.clicked.connect(media_player.play)
                controls_layout.addWidget(play_button)
                
                pause_button = QPushButton("Pause")
                pause_button.clicked.connect(media_player.pause)
                controls_layout.addWidget(pause_button)
                
                stop_button = QPushButton("Stop")
                stop_button.clicked.connect(media_player.stop)
                controls_layout.addWidget(stop_button)
                
                # Add rewind button
                rewind_button = QPushButton("⏪ -10s")
                rewind_button.clicked.connect(lambda: media_player.setPosition(max(0, media_player.position() - 10000)))
                controls_layout.addWidget(rewind_button)
                
                # Add forward button
                forward_button = QPushButton("⏩ +10s")
                forward_button.clicked.connect(lambda: media_player.setPosition(media_player.position() + 10000))
                controls_layout.addWidget(forward_button)
                
                # Add position slider and time labels
                slider_layout = QHBoxLayout()
                
                # Current time label
                current_time_label = QLabel("00:00")
                slider_layout.addWidget(current_time_label)
                
                # Position slider
                position_slider = QSlider(Qt.Orientation.Horizontal)
                position_slider.setRange(0, 0)  # Will be updated when duration is available
                position_slider.sliderMoved.connect(media_player.setPosition)
                slider_layout.addWidget(position_slider)
                
                # Duration label
                duration_label = QLabel("00:00")
                slider_layout.addWidget(duration_label)
                
                # Update slider and labels when duration is available
                def update_duration(duration):
                    position_slider.setRange(0, duration)
                    duration_label.setText(self.format_time(duration))
                
                def update_position(position):
                    if not position_slider.isSliderDown():
                        position_slider.setValue(position)
                    current_time_label.setText(self.format_time(position))
                
                media_player.durationChanged.connect(update_duration)
                media_player.positionChanged.connect(update_position)
                
                controls_layout.addLayout(slider_layout)
                layout.addLayout(controls_layout)
                
                def cleanup():
                    media_player.stop()
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                
                dialog.finished.connect(cleanup)
                
            except Exception as e:
                error_label = QLabel(f"Failed to load video: {str(e)}")
                layout.addWidget(error_label)
        elif content_type.startswith('text/') or content_type == 'application/json':
            # Text preview
            try:
                # Download to temp file
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_path = temp_file.name
                
                download_file(self.s3_client, self.current_bucket, obj['Key'], temp_path)
                
                # Load text
                with open(temp_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                # Display text
                text_edit = QPlainTextEdit()
                text_edit.setPlainText(text)
                text_edit.setReadOnly(True)
                layout.addWidget(text_edit)
                
                # Clean up temp file
                os.unlink(temp_path)
            except Exception as e:
                error_label = QLabel(f"Failed to load text: {str(e)}")
                layout.addWidget(error_label)
        else:
            # Unsupported content type
            unsupported_label = QLabel(f"Preview not supported for content type: {content_type}")
            layout.addWidget(unsupported_label)
        
        # Add close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def on_header_clicked(self, column):
        """Handle header click for sorting"""
        if self.sort_column == column:
            # Toggle sort order
            self.sort_order = Qt.SortOrder.DescendingOrder if self.sort_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
        else:
            # Set new sort column
            self.sort_column = column
            self.sort_order = Qt.SortOrder.AscendingOrder
        
        self.sort_objects()
        self.update_object_table()
    
    def sort_objects(self):
        """Sort objects based on current sort column and order"""
        # Define sort key function based on column
        def get_sort_key(obj):
            if self.sort_column == 0:  # Name
                return obj['Key'].lower()
            elif self.sort_column == 1:  # Size
                return obj['Size'] or 0
            elif self.sort_column == 2:  # Last Modified
                return obj['LastModified'] or datetime.min
            elif self.sort_column == 3:  # Content Type
                return obj['ContentType'].lower()
            return obj['Key'].lower()
        
        # Sort objects
        self.total_objects.sort(key=get_sort_key, reverse=(self.sort_order == Qt.SortOrder.DescendingOrder))
        self.update_object_table()
        self.update_pagination_info() 