# File Upload Boolean Parameter Fix

## Issue Resolved ✅

### Problem
The file upload functionality was showing this error when clicking upload buttons:
```
Invalid file path type received: <class 'bool'>
```

### Root Cause
PyQt6 button `clicked` signals automatically pass the button's checked state (boolean) as the first parameter to connected methods. When upload buttons were clicked:

- **File Transfer Tab Button**: `upload_btn.clicked.connect(self.upload_file)` → passed `False`
- **Chat Widget Button**: `file_upload_btn.clicked.connect(self.upload_file)` → passed `False`

The `upload_file()` method expected a string file path but received a boolean instead.

### Solution Applied

#### 1. Boolean Parameter Detection
Added logic to detect and handle boolean parameters from button clicks:

```python
def upload_file(self, file_path=None):
    # Handle boolean parameter from button clicks (PyQt6 passes checked state)
    if isinstance(file_path, bool):
        file_path = None  # Treat as no file path provided
```

#### 2. Fixed Button Connections
Changed button connections to use lambda functions to avoid passing boolean parameters:

```python
# Before (problematic):
upload_btn.clicked.connect(self.upload_file)

# After (fixed):
upload_btn.clicked.connect(lambda: self.upload_file())
```

Applied to both:
- File Transfer tab upload button
- Chat widget file upload button

### Files Modified
- `kkc/CN/gui/main_client.py` - Fixed `upload_file()` method and button connections

### Testing
- ✅ Button clicks now open file dialog correctly
- ✅ Signal-based file uploads still work
- ✅ No more boolean parameter errors
- ✅ All file upload functionality restored

### Result
File upload now works perfectly from both:
1. **File Transfer Tab** - "📎 Select File to Upload" button
2. **Chat Widget** - "📎" file upload button

The fix maintains backward compatibility while resolving the PyQt6 button click parameter issue.