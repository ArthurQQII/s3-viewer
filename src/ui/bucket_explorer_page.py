from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QTableWidget,
                             QTableWidgetItem, QHeaderView, QMessageBox,
                             QFileDialog, QDialog, QPlainTextEdit, QProgressDialog,
                             QMenu, QSlider)
from PyQt6.QtCore import pyqtSignal, Qt, QUrl, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
import os
from datetime import datetime
import tempfile
import mimetypes
import json
import webbrowser
from src.utils.aws_utils import (get_s3_client, list_objects, get_object_metadata, 
                               download_file, generate_presigned_url)
from src.ui.loading_animation import LoadingAnimation
from PyQt6.QtWidgets import QApplication

class ObjectLoaderThread(QThread):
    """Thread for loading objects in the background"""
    objects_loaded = pyqtSignal(list, bool, bool)  # objects, is_complete, is_first_batch
    error_occurred = pyqtSignal(str)
    
    def __init__(self, s3_client, bucket, prefix, continuation_token=None):
        super().__init__()
        self.s3_client = s3_client
        self.bucket = bucket
        self.prefix = prefix
        self.continuation_token = continuation_token
        self.is_running = True
        self.max_objects_per_batch = 100
    
    def run(self):
        try:
            # Load objects with continuation token if provided
            response = list_objects(
                self.s3_client,
                self.bucket,
                self.prefix,
                delimiter='/' if not self.prefix.endswith('/') else None,  # Only use delimiter for root level
                continuation_token=self.continuation_token
            )
            
            # Process objects
            objects = []
            
            # Add folders (CommonPrefixes)
            if 'CommonPrefixes' in response:
                for prefix in response['CommonPrefixes']:
                    folder_name = prefix['Prefix']
                    objects.append({
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
                    if key != self.prefix:
                        # Get content type
                        try:
                            head_response = get_object_metadata(self.s3_client, self.bucket, key)
                            content_type = head_response.get('ContentType', 'N/A')
                        except:
                            content_type = 'N/A'
                        
                        objects.append({
                            'Key': key,
                            'Size': obj['Size'],
                            'LastModified': obj['LastModified'],
                            'ContentType': content_type,
                            'is_folder': False
                        })
                    
                    # If we have enough objects for the first batch, emit them immediately
                    if not self.continuation_token and len(objects) >= self.max_objects_per_batch:
                        self.objects_loaded.emit(objects[:self.max_objects_per_batch], False, True)
                        objects = objects[self.max_objects_per_batch:]
            
            # Check if there are more objects to load
            is_complete = 'NextContinuationToken' not in response
            
            # Emit any remaining objects
            if objects:
                self.objects_loaded.emit(objects, is_complete, not self.continuation_token)
            
            # If there are more objects and the thread is still running, continue loading
            if not is_complete and self.is_running:
                next_token = response['NextContinuationToken']
                # Create a new thread to load the next batch
                next_loader = ObjectLoaderThread(self.s3_client, self.bucket, self.prefix, next_token)
                next_loader.objects_loaded.connect(self.on_next_batch_loaded)
                next_loader.error_occurred.connect(self.error_occurred)
                next_loader.start()
                
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def on_next_batch_loaded(self, objects, is_complete, is_first_batch):
        """Handle objects loaded from the next batch"""
        self.objects_loaded.emit(objects, is_complete, False)  # Never first batch for continuation
    
    def stop(self):
        """Stop the thread"""
        self.is_running = False

class BucketExplorerPage(QWidget):
    back_to_buckets = pyqtSignal()  # Signal for returning to bucket list
    invalid_credentials = pyqtSignal()  # Signal for invalid credentials
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.s3_client = None
        self.current_bucket = None
        self.current_prefix = ""
        self.total_objects = []
        self.filtered_objects = []  # Store filtered objects
        self.current_page = 1
        self.page_size = 100
        self.total_pages = 1
        self.total_items = 0
        self.sort_column = 0
        self.sort_order = Qt.SortOrder.AscendingOrder
        self.loader_thread = None
        self.is_loading_complete = False
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface"""
        layout = QVBoxLayout()
        
        # Top bar with back button and breadcrumb
        top_bar = QHBoxLayout()
        
        # Back button on the left
        self.back_button = QPushButton("← Back to Buckets")
        self.back_button.clicked.connect(lambda: self.back_to_buckets.emit())
        self.back_button.setMaximumWidth(150)
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
        
        # Search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name or file type (e.g. .mp4, .jpg)")
        self.search_input.textChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.search_input)
        
        # Clear search button
        self.clear_search_button = QPushButton("Clear")
        self.clear_search_button.clicked.connect(self.clear_search)
        self.clear_search_button.setVisible(False)
        search_layout.addWidget(self.clear_search_button)
        
        layout.addLayout(search_layout)
        
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
        self.clear_data()  # Clear previous data
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
            QApplication.processEvents()
            
            # Disable search and sorting during loading
            self.search_input.setEnabled(False)
            self.object_table.horizontalHeader().setSectionsClickable(False)
            
            # Stop any existing loader thread
            if self.loader_thread and self.loader_thread.isRunning():
                self.loader_thread.stop()
                self.loader_thread.wait()
            
            # Reset state
            self.total_objects = []
            self.filtered_objects = []
            self.is_loading_complete = False
            self.current_page = 1
            
            # Create and start the loader thread
            self.loader_thread = ObjectLoaderThread(self.s3_client, self.current_bucket, self.current_prefix)
            self.loader_thread.objects_loaded.connect(self.on_objects_loaded)
            self.loader_thread.error_occurred.connect(self.on_loader_error)
            self.loader_thread.start()
            
            # Update UI with initial empty state
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
            self.invalid_credentials.emit()
            return
    
    def on_objects_loaded(self, objects, is_complete, is_first_batch):
        """Handle objects loaded from the background thread"""
        # Add new objects to the total list
        self.total_objects.extend(objects)
        
        # Only update filtered objects if no search is active
        if not self.search_input.text():
            self.filtered_objects = self.total_objects
        
        # Update loading state
        self.is_loading_complete = is_complete
        
        # Update UI
        self.total_items = len(self.filtered_objects)
        self.total_pages = (self.total_items + self.page_size - 1) // self.page_size
        
        # Update table and pagination
        self.update_object_table()
        self.update_pagination_info()
        
        # Update loading animation text
        if is_complete:
            self.loading_animation.setText(f"Loaded {len(self.total_objects)} objects")
            self.loading_animation.setVisible(False)
            
            # Re-enable search and sorting
            self.search_input.setEnabled(True)
            self.object_table.horizontalHeader().setSectionsClickable(True)
            
            # Apply current search filter if any
            if self.search_input.text():
                self.filter_objects(self.search_input.text())
        else:
            if is_first_batch:
                self.loading_animation.setText(f"Loaded first {len(objects)} objects, loading more in background...")
            else:
                self.loading_animation.setText(f"Loaded {len(self.total_objects)} objects so far...")
            self.loading_animation.setVisible(True)
        
        # Enable UI interaction after first batch
        if is_first_batch:
            self.object_table.setEnabled(True)
            self.prev_button.setEnabled(self.current_page > 1)
            self.next_button.setEnabled(self.current_page < self.total_pages)
        
        QApplication.processEvents()
    
    def on_loader_error(self, error_message):
        """Handle error from the loader thread"""
        QMessageBox.warning(
            self,
            "Loading Error",
            f"Error loading objects: {error_message}"
        )
        self.loading_animation.setVisible(False)
        QApplication.processEvents()  # Force UI update
    
    def update_object_table(self):
        """Update the object table with current page data"""
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = start_idx + self.page_size
        current_objects = self.filtered_objects[start_idx:end_idx]
        
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
                obj = self.filtered_objects[(self.current_page - 1) * self.page_size + row]
                self.preview_object(obj)
    
    def download_file(self):
        """Download the selected file"""
        selected_items = self.object_table.selectedItems()
        if not selected_items:
            return
        
        row = selected_items[0].row()
        obj = self.filtered_objects[(self.current_page - 1) * self.page_size + row]
        
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
        obj = self.filtered_objects[(self.current_page - 1) * self.page_size + row]
        
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
            # Clear all data before going back to bucket list
            self.clear_data()
            self.back_to_buckets.emit()
    
    def clear_data(self):
        """Clear all stored data when leaving bucket"""
        # Stop any running thread
        if self.loader_thread and self.loader_thread.isRunning():
            self.loader_thread.stop()
            self.loader_thread.wait()
        
        # Clear data
        self.current_bucket = None
        self.current_prefix = ""
        self.total_objects = []
        self.filtered_objects = []
        self.current_page = 1
        self.total_pages = 1
        self.total_items = 0
        self.is_loading_complete = False
        
        # Clear UI
        self.object_table.setRowCount(0)
        self.search_input.clear()
        self.update_pagination_info()
        self.loading_animation.setVisible(False)
    
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
        obj = self.filtered_objects[(self.current_page - 1) * self.page_size + row]
        
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
        
        if content_type.startswith('video/'):
            try:
                # Generate pre-signed URL with 1-hour expiration
                url = generate_presigned_url(self.s3_client, self.current_bucket, obj['Key'])
                
                # Open URL in default browser
                webbrowser.open(url)
                
                # Show information message
                QMessageBox.information(
                    self,
                    "Video Preview",
                    "The video will open in your default web browser.\n"
                    "The link will expire in 1 hour."
                )
                return
                
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Preview Failed",
                    f"Failed to generate video preview URL: {str(e)}"
                )
                return
        
        # For non-video content types, create preview dialog
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
        # Only allow sorting when loading is complete
        if not self.is_loading_complete:
            return
            
        if self.sort_column == column:
            self.sort_order = Qt.SortOrder.DescendingOrder if self.sort_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
        else:
            self.sort_column = column
            self.sort_order = Qt.SortOrder.AscendingOrder
        
        self.sort_objects()
    
    def sort_objects(self):
        """Sort objects based on current sort column and order"""
        # Define sort key function based on column
        def get_sort_key(obj):
            if self.sort_column == 0:  # Name
                return obj['Key'].lower()
            elif self.sort_column == 1:  # Size
                return obj['Size'] or 0
            elif self.sort_column == 2:  # Last Modified
                # Convert to naive datetime by removing timezone info
                last_modified = obj['LastModified']
                if last_modified is None:
                    return datetime.min
                if last_modified.tzinfo:
                    # Convert to UTC then remove timezone info
                    return last_modified.astimezone().replace(tzinfo=None)
                return last_modified
            elif self.sort_column == 3:  # Content Type
                return obj['ContentType'].lower()
            return obj['Key'].lower()
        
        # Sort objects
        self.filtered_objects.sort(key=get_sort_key, reverse=(self.sort_order == Qt.SortOrder.DescendingOrder))
        self.update_object_table()
        self.update_pagination_info()
    
    def on_search_changed(self, search_text):
        """Handle search text changes"""
        # Only allow search when loading is complete
        if not self.is_loading_complete:
            return
            
        self.clear_search_button.setVisible(bool(search_text))
        self.filter_objects(search_text)
    
    def clear_search(self):
        """Clear the search input"""
        self.search_input.clear()
    
    def filter_objects(self, search_text):
        """Filter objects based on search text"""
        if not search_text:
            self.filtered_objects = self.total_objects
        else:
            search_text = search_text.lower()
            self.filtered_objects = [
                obj for obj in self.total_objects
                if (search_text in os.path.basename(obj['Key']).lower() or  # Match filename
                    search_text in obj['ContentType'].lower() or  # Match content type
                    (search_text.startswith('.') and  # Match file extension
                     os.path.basename(obj['Key']).lower().endswith(search_text)))
            ]
        
        # Reset to first page and update UI
        self.current_page = 1
        self.total_items = len(self.filtered_objects)
        self.total_pages = (self.total_items + self.page_size - 1) // self.page_size
        self.update_object_table()
        self.update_pagination_info() 