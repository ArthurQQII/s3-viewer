from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QTableWidget,
                             QTableWidgetItem, QHeaderView, QMessageBox)
from PyQt6.QtCore import pyqtSignal, Qt
from src.utils.aws_utils import create_aws_session, get_s3_client, list_buckets

class BucketListPage(QWidget):
    bucket_selected = pyqtSignal(str)
    invalid_credentials = pyqtSignal()  # Signal for invalid credentials
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.session = None
        self.s3_client = None
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("S3 Buckets")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        header_layout.addWidget(title)
        
        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search buckets...")
        self.search_box.textChanged.connect(self.filter_buckets)
        header_layout.addWidget(self.search_box)
        
        layout.addLayout(header_layout)
        
        # Bucket table
        self.bucket_table = QTableWidget()
        self.bucket_table.setColumnCount(2)
        self.bucket_table.setHorizontalHeaderLabels(["Bucket Name", "Created Date"])
        self.bucket_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.bucket_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.bucket_table.itemDoubleClicked.connect(self.on_bucket_double_clicked)
        layout.addWidget(self.bucket_table)
        
        # Navigation buttons
        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("Previous")
        self.next_btn = QPushButton("Next")
        self.prev_btn.clicked.connect(self.previous_page)
        self.next_btn.clicked.connect(self.next_page)
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.next_btn)
        layout.addLayout(nav_layout)
        
        self.setLayout(layout)
        
        # Initialize pagination
        self.current_page = 1
        self.items_per_page = 20
        self.total_buckets = []
    
    def set_profile(self, profile_name):
        """Set the AWS profile and load buckets"""
        try:
            self.session = create_aws_session(profile_name)
            self.s3_client = get_s3_client(self.session)
            self.load_buckets()
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
    
    def load_buckets(self):
        """Load all buckets from S3"""
        try:
            self.total_buckets = list_buckets(self.s3_client)
            self.update_bucket_table()
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
    
    def update_bucket_table(self):
        """Update the bucket table with current page data"""
        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = start_idx + self.items_per_page
        current_buckets = self.total_buckets[start_idx:end_idx]
        
        self.bucket_table.setRowCount(len(current_buckets))
        for i, bucket in enumerate(current_buckets):
            self.bucket_table.setItem(i, 0, QTableWidgetItem(bucket['Name']))
            self.bucket_table.setItem(i, 1, QTableWidgetItem(str(bucket['CreationDate'])))
        
        # Update navigation buttons
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(end_idx < len(self.total_buckets))
    
    def filter_buckets(self):
        """Filter buckets based on search text"""
        search_text = self.search_box.text().lower()
        if not search_text:
            self.load_buckets()
            return
        
        filtered_buckets = [
            bucket for bucket in self.total_buckets
            if search_text in bucket['Name'].lower()
        ]
        self.total_buckets = filtered_buckets
        self.current_page = 1
        self.update_bucket_table()
    
    def previous_page(self):
        """Go to previous page"""
        if self.current_page > 1:
            self.current_page -= 1
            self.update_bucket_table()
    
    def next_page(self):
        """Go to next page"""
        if (self.current_page * self.items_per_page) < len(self.total_buckets):
            self.current_page += 1
            self.update_bucket_table()
    
    def on_bucket_double_clicked(self, item):
        """Handle bucket selection"""
        bucket_name = self.bucket_table.item(item.row(), 0).text()
        self.bucket_selected.emit(bucket_name) 