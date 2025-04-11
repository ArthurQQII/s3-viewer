from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, 
                             QComboBox, QPushButton, QMessageBox)
from PyQt6.QtCore import pyqtSignal, Qt
import os
import configparser
from pathlib import Path

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
        profiles = set()
        
        # Get home directory
        home = str(Path.home())
        
        # Load from credentials file
        creds_path = os.path.join(home, '.aws', 'credentials')
        if os.path.exists(creds_path):
            config = configparser.ConfigParser()
            config.read(creds_path)
            profiles.update(config.sections())
        
        # Load from config file
        config_path = os.path.join(home, '.aws', 'config')
        if os.path.exists(config_path):
            config = configparser.ConfigParser()
            config.read(config_path)
            for section in config.sections():
                if section.startswith('profile '):
                    profiles.add(section[8:])  # Remove 'profile ' prefix
        
        # Add profiles to combo box
        self.profile_combo.addItems(sorted(profiles))
        
        # Select default profile if available
        default_index = self.profile_combo.findText('default')
        if default_index >= 0:
            self.profile_combo.setCurrentIndex(default_index)
    
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