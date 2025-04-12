from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QTableWidget,
                             QTableWidgetItem, QHeaderView, QMessageBox,
                             QFileDialog, QDialog, QPlainTextEdit, QProgressDialog,
                             QMenu)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPixmap, QImage
import os
from datetime import datetime
import tempfile
import mimetypes
import json
from src.utils.aws_utils import get_s3_client, list_objects, get_object_metadata, download_file

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
        self.page_size = 1000
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
        self.current_prefix = prefix
        self.load_objects()
    
    def load_objects(self):
        """Load objects from the current bucket and prefix"""
        try:
            # List objects with delimiter for proper folder structure
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
            self.object_table.setItem(i, 3, QTableWidgetItem(content_type))
        
        # Update pagination buttons
        self.prev_button.setEnabled(self.current_page > 1)
        self.next_button.setEnabled(end_idx < len(self.total_objects))
    
    def format_size(self, size_bytes):
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def show_context_menu(self, position):
        """Show context menu for right-click actions"""
        menu = QMenu()
        selected_items = self.object_table.selectedItems()
        
        if selected_items:
            row = selected_items[0].row()
            obj = self.total_objects[row]
            
            if obj['is_folder']:
                download_action = menu.addAction("Download Folder")
                download_action.triggered.connect(self.download_folder)
            else:
                download_action = menu.addAction("Download")
                download_action.triggered.connect(self.download_file)
        
        menu.exec(self.object_table.viewport().mapToGlobal(position))
    
    def download_file(self):
        """Download a single file"""
        selected_items = self.object_table.selectedItems()
        if not selected_items:
            return
        
        row = selected_items[0].row()
        obj = self.total_objects[row]
        
        if obj['is_folder']:
            return
        
        # Get save location from user
        file_name = obj['Key'].split('/')[-1]
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save File",
            file_name
        )
        
        if save_path:
            try:
                download_file(self.s3_client, self.current_bucket, obj['Key'], save_path)
                QMessageBox.information(
                    self,
                    "Success",
                    f"File downloaded successfully to {save_path}"
                )
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
    
    def download_folder(self):
        """Download the entire folder"""
        selected_items = self.object_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select a folder to download."
            )
            return
        
        row = selected_items[0].row()
        obj = self.total_objects[row]
        
        if not obj['is_folder']:
            QMessageBox.warning(
                self,
                "Invalid Selection",
                "Please select a folder to download."
            )
            return
        
        # Get save location from user
        folder_name = obj['Key'][len(self.current_prefix):].rstrip('/')
        save_path = QFileDialog.getExistingDirectory(
            self,
            "Save Folder",
            folder_name
        )
        
        if save_path:
            try:
                # Create a progress dialog
                progress = QProgressDialog("Downloading folder...", "Cancel", 0, 100, self)
                progress.setWindowModality(Qt.WindowModality.WindowModal)
                progress.setMinimumDuration(0)
                progress.setValue(0)
                
                # Get all objects in the folder
                folder_prefix = obj['Key']
                paginator = self.s3_client.get_paginator('list_objects_v2')
                all_objects = []
                
                for page in paginator.paginate(Bucket=self.current_bucket, Prefix=folder_prefix):
                    if 'Contents' in page:
                        all_objects.extend(page['Contents'])
                
                total_objects = len(all_objects)
                if total_objects == 0:
                    QMessageBox.information(
                        self,
                        "Empty Folder",
                        "The selected folder is empty."
                    )
                    return
                
                # Create the base folder
                folder_name = os.path.basename(obj['Key'].rstrip('/'))
                base_folder = os.path.join(save_path, folder_name)
                os.makedirs(base_folder, exist_ok=True)
                
                # Download each object
                for i, s3_obj in enumerate(all_objects):
                    if progress.wasCanceled():
                        break
                    
                    # Update progress
                    progress.setValue(int((i / total_objects) * 100))
                    progress.setLabelText(f"Downloading {s3_obj['Key']}...")
                    
                    # Create local path (preserving folder structure)
                    rel_path = s3_obj['Key'][len(folder_prefix):]  # Get path relative to folder
                    local_path = os.path.join(base_folder, rel_path.lstrip('/'))
                    
                    # Create directory if needed
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)
                    
                    # Download file
                    download_file(self.s3_client, self.current_bucket, s3_obj['Key'], local_path)
                
                progress.setValue(100)
                
                QMessageBox.information(
                    self,
                    "Success",
                    f"Folder downloaded successfully to {base_folder}"
                )
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
    
    def update_pagination_info(self):
        """Update pagination information display"""
        self.page_info.setText(f"Page {self.current_page} of {self.total_pages} ({self.total_items} items)")
        self.prev_button.setEnabled(self.current_page > 1)
        self.next_button.setEnabled(self.current_page < self.total_pages)
    
    def go_back(self):
        """Go back to parent folder"""
        if self.current_prefix:
            self.current_prefix = os.path.dirname(self.current_prefix.rstrip('/'))
            if self.current_prefix:
                self.current_prefix += '/'
            self.update_breadcrumb()
            self.load_objects()
    
    def previous_page(self):
        """Go to previous page"""
        if self.current_page > 1:
            self.current_page -= 1
            self.load_objects()
    
    def next_page(self):
        """Go to next page"""
        if (self.current_page * self.page_size) < len(self.total_objects):
            self.current_page += 1
            self.load_objects()
    
    def on_object_double_clicked(self, item):
        """Handle object selection"""
        row = item.row()
        obj = self.total_objects[row]
        
        if obj['is_folder']:
            self.current_prefix = obj['Key']
            self.update_breadcrumb()
            self.load_objects()
        else:
            self.preview_object(obj)
    
    def preview_object(self, obj):
        """Preview the selected object"""
        # Get file extension and mime type
        file_name = obj['Key']
        mime_type, _ = mimetypes.guess_type(file_name)
        
        if not mime_type:
            QMessageBox.information(
                self,
                "Preview Unavailable",
                "Preview is not available for this file type."
            )
            return
        
        temp_file = None
        try:
            # Create a temporary file to store the downloaded content
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            temp_file.close()  # Close the file before downloading
            
            download_file(self.s3_client, self.current_bucket, obj['Key'], temp_file.name)
            
            # Create preview dialog
            preview_dialog = QDialog(self)
            preview_dialog.setWindowTitle(f"Preview: {os.path.basename(file_name)}")
            preview_dialog.resize(800, 600)
            
            dialog_layout = QVBoxLayout()
            
            if mime_type.startswith('image/'):
                # Handle image preview
                image_label = QLabel()
                pixmap = QPixmap(temp_file.name)
                scaled_pixmap = pixmap.scaled(780, 580, Qt.AspectRatioMode.KeepAspectRatio)
                image_label.setPixmap(scaled_pixmap)
                dialog_layout.addWidget(image_label)
            
            elif mime_type == 'application/pdf':
                # For PDF, show a message that it needs to be downloaded
                msg_label = QLabel("PDF files need to be downloaded to view.")
                dialog_layout.addWidget(msg_label)
            
            elif mime_type.startswith('text/') or mime_type in ['application/json']:
                # Handle text preview
                try:
                    with open(temp_file.name, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if mime_type == 'application/json':
                            # Pretty print JSON
                            try:
                                parsed = json.loads(content)
                                content = json.dumps(parsed, indent=2)
                            except:
                                pass
                        text_edit = QPlainTextEdit()
                        text_edit.setPlainText(content)
                        text_edit.setReadOnly(True)
                        dialog_layout.addWidget(text_edit)
                except UnicodeDecodeError:
                    QMessageBox.warning(
                        self,
                        "Preview Error",
                        "Unable to preview this text file. It might be binary or encoded."
                    )
                    preview_dialog.close()
                    return
            
            else:
                QMessageBox.information(
                    self,
                    "Preview Unavailable",
                    "Preview is not available for this file type."
                )
                preview_dialog.close()
                return
            
            # Add close button
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(preview_dialog.close)
            dialog_layout.addWidget(close_btn)
            
            preview_dialog.setLayout(dialog_layout)
            preview_dialog.exec()
            
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
            # Clean up temporary file
            if temp_file:
                try:
                    os.unlink(temp_file.name)
                except:
                    pass
    
    def on_header_clicked(self, column):
        """Handle column header click for sorting"""
        if column == self.sort_column:
            # Toggle sort order if clicking the same column
            self.sort_order = Qt.SortOrder.DescendingOrder if self.sort_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
        else:
            # Set new sort column and default to ascending
            self.sort_column = column
            self.sort_order = Qt.SortOrder.AscendingOrder
        
        self.sort_objects()
        self.update_object_table()
    
    def sort_objects(self):
        """Sort objects based on current column and order"""
        reverse = self.sort_order == Qt.SortOrder.DescendingOrder
        
        if self.sort_column == 0:  # Name
            self.total_objects.sort(
                key=lambda x: x['Key'].lower(),
                reverse=reverse
            )
        elif self.sort_column == 1:  # Size
            self.total_objects.sort(
                key=lambda x: x['Size'],
                reverse=reverse
            )
        elif self.sort_column == 2:  # Last Modified
            self.total_objects.sort(
                key=lambda x: x['LastModified'].timestamp() if x['LastModified'] else 0,
                reverse=reverse
            )
        elif self.sort_column == 3:  # Content Type
            self.total_objects.sort(
                key=lambda x: x['ContentType'].lower(),
                reverse=reverse
            )

        self.update_object_table()
        self.update_pagination_info() 