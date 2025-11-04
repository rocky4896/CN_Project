#!/usr/bin/env python3
"""Test import of main_client"""

try:
    from main_client import ClientMainWindow
    print("✅ Import successful - no errors found")
except Exception as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()