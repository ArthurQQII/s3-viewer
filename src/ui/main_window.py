from PyQt6.QtWidgets import QMainWindow, QStackedWidget
from PyQt6.QtCore import Qt
from .credential_page import CredentialPage
from .bucket_list_page import BucketListPage
from .bucket_explorer_page import BucketExplorerPage

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("S3 Viewer")
        self.setMinimumSize(800, 600)
        
        # Create stacked widget for managing different pages
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        # Initialize pages
        self.credential_page = CredentialPage()
        self.bucket_list_page = BucketListPage()
        self.bucket_explorer_page = BucketExplorerPage()
        
        # Add pages to stacked widget
        self.stacked_widget.addWidget(self.credential_page)
        self.stacked_widget.addWidget(self.bucket_list_page)
        self.stacked_widget.addWidget(self.bucket_explorer_page)
        
        # Connect signals
        self.credential_page.credentials_selected.connect(self.on_credentials_selected)
        self.bucket_list_page.bucket_selected.connect(self.on_bucket_selected)
        self.bucket_explorer_page.back_to_buckets.connect(self.show_bucket_list)
        
        # Show credential page by default
        self.stacked_widget.setCurrentWidget(self.credential_page)
    
    def on_credentials_selected(self, profile_name):
        """Handle when credentials are selected"""
        self.bucket_list_page.set_profile(profile_name)
        self.stacked_widget.setCurrentWidget(self.bucket_list_page)
    
    def on_bucket_selected(self, bucket_name):
        """Handle when a bucket is selected"""
        self.bucket_explorer_page.set_session(self.bucket_list_page.session)
        self.bucket_explorer_page.set_bucket(bucket_name)
        self.stacked_widget.setCurrentWidget(self.bucket_explorer_page)
    
    def show_bucket_list(self):
        """Switch back to bucket list view"""
        self.stacked_widget.setCurrentWidget(self.bucket_list_page) 