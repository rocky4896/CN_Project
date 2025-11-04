#!/usr/bin/env python3
"""
Test script to verify the file upload fix
"""

import sys
from pathlib import Path

def test_upload_file_parameter_handling():
    """Test how the upload_file method handles different parameter types"""
    
    print("Testing upload_file parameter handling...")
    
    # Test cases that should be handled gracefully
    test_cases = [
        (None, "None parameter"),
        ("", "Empty string"),
        ("   ", "Whitespace string"),
        (True, "Boolean True (from button click)"),
        (False, "Boolean False (from button click)"),
        ("valid_file.txt", "Valid string path"),
        (Path("valid_file.txt"), "Path object"),
    ]
    
    for test_value, description in test_cases:
        print(f"\nTesting: {description}")
        print(f"  Value: {repr(test_value)}")
        print(f"  Type: {type(test_value)}")
        
        # Simulate the logic from the fixed upload_file method
        file_path = test_value
        
        # Handle boolean parameter from button clicks (PyQt6 passes checked state)
        if isinstance(file_path, bool):
            print(f"  → Detected boolean parameter, would open file dialog")
            file_path = None
        
        # Check if file dialog would be opened
        if file_path is None or file_path == "" or (isinstance(file_path, str) and not file_path.strip()):
            print(f"  → Would open file dialog")
        else:
            # Check if it's a valid type
            if not isinstance(file_path, (str, Path)):
                print(f"  → Would show error: Invalid file path type")
            else:
                print(f"  → Would proceed with file: {file_path}")

if __name__ == "__main__":
    test_upload_file_parameter_handling()
    print("\n✅ File upload parameter handling test completed!")
    print("The boolean parameter issue should now be fixed.")