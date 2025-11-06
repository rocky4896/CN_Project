#!/usr/bin/env python3
"""
Test script to verify the leave button functionality
"""

import sys
import time
from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import QTimer
from main_client import ClientMainWindow

class LeaveButtonTester(QWidget):
    def __init__(self):
        super().__init__()
        self.client = None
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.status_label = QLabel("Click 'Start Client' to begin test")
        layout.addWidget(self.status_label)
        
        start_btn = QPushButton("Start Client")
        start_btn.clicked.connect(self.start_client)
        layout.addWidget(start_btn)
        
        self.leave_btn = QPushButton("Test Leave Button")
        self.leave_btn.clicked.connect(self.test_leave_button)
        self.leave_btn.setEnabled(False)
        layout.addWidget(self.leave_btn)
        
        close_btn = QPushButton("Close Tester")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        self.setWindowTitle("Leave Button Tester")
        self.resize(300, 150)
    
    def start_client(self):
        """Start the client with automatic connection."""
        try:
            self.client = ClientMainWindow()
            
            # Auto-connect to localhost
            conn_info = {
                'host': 'localhost',
                'port': 9000,
                'username': 'TestUser_LeaveButton',
                'join_with_video': False,
                'join_with_audio': False
            }
            
            self.client.connect_to_server(conn_info)
            self.client.show()
            
            self.status_label.setText("Client started and connecting...")
            self.leave_btn.setEnabled(True)
            
            # Check connection status after a delay
            QTimer.singleShot(3000, self.check_connection)
            
        except Exception as e:
            self.status_label.setText(f"Error starting client: {e}")
    
    def check_connection(self):
        """Check if client is connected."""
        if self.client and self.client.connected:
            self.status_label.setText("✅ Client connected! You can now test the leave button.")
        else:
            self.status_label.setText("❌ Client failed to connect. Check server is running.")
    
    def test_leave_button(self):
        """Test the leave button functionality."""
        if self.client and self.client.connected:
            self.status_label.setText("🚪 Testing leave button...")
            
            # Call the leave button handler
            self.client.handle_leave_button_click()
            
            # Check if disconnection worked after a delay
            QTimer.singleShot(2000, self.check_disconnection)
        else:
            self.status_label.setText("❌ No connected client to test")
    
    def check_disconnection(self):
        """Check if client disconnected properly."""
        if self.client:
            if not self.client.connected:
                self.status_label.setText("✅ Leave button worked! Client disconnected properly.")
            else:
                self.status_label.setText("❌ Leave button failed! Client still connected.")
        else:
            self.status_label.setText("❌ Client object not found")

def main():
    app = QApplication(sys.argv)
    tester = LeaveButtonTester()
    tester.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())