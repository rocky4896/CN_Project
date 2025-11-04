#!/usr/bin/env python3
"""
Simple launcher for the new tabbed UI
Run this from the gui directory to test the interface
"""

import sys

def main():
    """Launch the tabbed UI for testing"""
    try:
        from PyQt6.QtWidgets import QApplication
        from main_client import ClientMainWindow
        
        print("🚀 Launching LAN Meeting System with Tabbed UI...")
        print("=" * 50)
        
        app = QApplication(sys.argv)
        
        # Create the main window
        window = ClientMainWindow()
        
        # Show the window
        window.show()
        
        print("✅ Tabbed UI loaded successfully!")
        print()
        print("📋 New Interface Features:")
        print("   📹 Video Meeting - Main video conferencing")
        print("   🖥️ Screen Share - Screen sharing controls")
        print("   💬 Chat - Group messaging")
        print("   📁 File Transfer - Upload/download files")
        print("   👥 Participants - User management")
        print()
        print("💡 Click the sidebar buttons to switch between tabs!")
        print("🔌 To connect to a server, use the connection dialog")
        print()
        
        return app.exec()
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Install dependencies:")
        print("   pip install PyQt6")
        print("   pip install -r requirements.txt")
        return 1
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        print("💡 Make sure you're in the gui directory")
        return 1

if __name__ == "__main__":
    sys.exit(main())