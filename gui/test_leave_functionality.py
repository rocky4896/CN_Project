#!/usr/bin/env python3
"""
Test script to verify the leave button functionality by programmatically triggering it
"""

import sys
import time
import asyncio
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from main_client import ClientMainWindow

def test_leave_button():
    """Test the leave button functionality."""
    print("🧪 Starting Leave Button Test")
    print("=" * 50)
    
    app = QApplication(sys.argv)
    
    # Create client
    client = ClientMainWindow()
    
    # Auto-connect configuration
    conn_info = {
        'host': 'localhost',
        'port': 9000,
        'username': 'LeaveTest_User',
        'join_with_video': False,
        'join_with_audio': False
    }
    
    print("📡 Connecting to server...")
    client.connect_to_server(conn_info)
    client.show()
    
    def check_connection_and_test():
        """Check connection and test leave button after delay."""
        if client.connected:
            print("✅ Connected successfully!")
            print("🚪 Testing leave button in 2 seconds...")
            
            def trigger_leave():
                print("🔄 Triggering leave button...")
                client.handle_leave_button_click()
                
                def check_result():
                    if not client.connected:
                        print("✅ SUCCESS: Leave button worked! Client disconnected properly.")
                        print("🎯 The meeting ended cleanly without needing to close GUI or terminal.")
                    else:
                        print("❌ FAILED: Client is still connected after leave button.")
                    
                    # Close the application after test
                    QTimer.singleShot(1000, app.quit)
                
                # Check result after 2 seconds
                QTimer.singleShot(2000, check_result)
            
            # Trigger leave button after 2 seconds
            QTimer.singleShot(2000, trigger_leave)
        else:
            print("❌ Failed to connect to server")
            print("💡 Make sure the server is running: py main_server.py")
            QTimer.singleShot(1000, app.quit)
    
    # Check connection after 3 seconds
    QTimer.singleShot(3000, check_connection_and_test)
    
    # Run the application
    return app.exec()

if __name__ == "__main__":
    sys.exit(test_leave_button())