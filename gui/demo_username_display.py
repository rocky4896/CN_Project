#!/usr/bin/env python3
"""
Demo script to show username display functionality
This simulates what happens when a user connects with a username
"""

import sys
from PyQt6.QtWidgets import QApplication, QTimer
from main_client import ClientMainWindow

def demo_username_update():
    """Demo function to show username display"""
    
    app = QApplication(sys.argv)
    
    # Create the main window
    window = ClientMainWindow()
    window.show()
    
    print("🚀 Demo: Username Display in Tabbed UI")
    print("=" * 50)
    print("📋 Initial state: Title shows 'LAN Meeting'")
    print("⏳ Simulating user connection in 3 seconds...")
    
    def simulate_connection():
        """Simulate a user connecting with a username"""
        # Simulate setting username (normally done during connection)
        window.username = "John Doe"
        
        # Update the title (normally called when LOGIN_SUCCESS is received)
        window.update_title_with_username()
        
        print("✅ Simulated connection successful!")
        print(f"📝 Title now shows: '{window.title_label.text()}'")
        print(f"🪟 Window title: '{window.windowTitle()}'")
        print()
        print("💡 In real usage:")
        print("   1. User enters their name in connection dialog")
        print("   2. Client connects to server")
        print("   3. Server confirms login")
        print("   4. Title automatically updates to show username")
        
        # Simulate disconnection after 5 seconds
        QTimer.singleShot(5000, simulate_disconnection)
    
    def simulate_disconnection():
        """Simulate user disconnecting"""
        print("\n⏳ Simulating disconnection...")
        
        # Reset username (normally done in disconnect_from_server)
        window.username = None
        window.update_title_with_username()
        
        print("🔌 Disconnected!")
        print(f"📝 Title reset to: '{window.title_label.text()}'")
        print(f"🪟 Window title: '{window.windowTitle()}'")
    
    # Schedule the demo
    QTimer.singleShot(3000, simulate_connection)
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(demo_username_update())