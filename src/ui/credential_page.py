from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, 
                              QComboBox, QPushButton, QMessageBox)
from PyQt6.QtCore import pyqtSignal, Qt
from src.utils.aws_utils import load_aws_profiles

class CredentialPage(QWidget):
    credentials_selected = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_aws_profiles()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Select AWS Profile")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin: 20px;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Profile selector
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(300)
        layout.addWidget(self.profile_combo, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Continue button
        self.continue_btn = QPushButton("Continue")
        self.continue_btn.setMinimumWidth(200)
        self.continue_btn.clicked.connect(self.on_continue_clicked)
        layout.addWidget(self.continue_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Help text
        help_text = QLabel(
            "No profiles found? Configure AWS CLI using:\n"
            "aws configure --profile your-profile-name"
        )
        help_text.setStyleSheet("color: gray; margin: 20px;")
        layout.addWidget(help_text, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.setLayout(layout)
    
    def load_aws_profiles(self):
        """Load AWS profiles from credentials and config files"""
        try:
            profiles = load_aws_profiles()
            
            # Add profiles to combo box
            self.profile_combo.addItems(profiles)
            
            # Select default profile if available
            default_index = self.profile_combo.findText('default')
            if default_index >= 0:
                self.profile_combo.setCurrentIndex(default_index)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load AWS profiles: {str(e)}"
            )
    
    def on_continue_clicked(self):
        profile = self.profile_combo.currentText()
        if not profile:
            QMessageBox.warning(
                self,
                "No Profile Selected",
                "Please select an AWS profile to continue."
            )
            return
        
        self.credentials_selected.emit(profile) 