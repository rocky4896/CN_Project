#!/usr/bin/env python3
"""
Test script for the new tabbed UI
Run this to see the new interface without connecting to a server
"""

import sys
import os

def main():
    """Main function to test the tabbed UI"""
    try:
        from PyQt6.QtWidgets import QApplication
        from main_client import ClientMainWindow
        
        print("🚀 Testing new tabbed UI...")
        
        app = QApplication(sys.argv)
        
        # Create the main window
        window = ClientMainWindow()
        
        # Show the window
        window.show()
        
        print("✅ Tabbed UI loaded successfully!")
        print("📋 Available tabs:")
        print("   📹 Video Meeting")
        print("   🖥️ Screen Share") 
        print("   💬 Chat")
        print("   📁 File Transfer")
        print("   👥 Participants")
        print()
        print("Click the sidebar buttons to switch between tabs!")
        
        return app.exec()
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure PyQt6 is installed: pip install PyQt6")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())