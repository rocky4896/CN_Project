#!/usr/bin/env python3
"""
LAN Collaboration Client - Complete Implementation

Full-featured collaboration client implemented from scratch with:
- Complete PyQt6 GUI with video grid, chat, controls
- Multi-user video conferencing (UDP)
- Multi-user audio conferencing (UDP) 
- Screen sharing viewing (TCP)
- Group text chat (TCP)
- File sharing (TCP)
- Participant management
- Media controls (video/audio on/off)
- Screen sharing presenter and viewer
- Modern responsive interface

This is a complete standalone implementation with 2000+ lines.
"""

import sys
import os
import asyncio
import threading
import json
import time
import struct
import socket
import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from collections import deque
import traceback

# PyQt6 imports for comprehensive GUI
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QTextEdit, QTextBrowser, QLineEdit, 
    QListWidget, QListWidgetItem, QProgressBar, QFileDialog, QMessageBox, 
    QInputDialog, QSizePolicy, QMenu, QDialog, QTabWidget, QFrame,
    QScrollArea, QSplitter, QGroupBox, QCheckBox, QSpinBox, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QTreeWidget, QTreeWidgetItem,
    QSlider, QToolButton, QStatusBar, QMenuBar, QToolBar,
    QStackedWidget, QFormLayout, QDialogButtonBox
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QSize, QTimer, QMutex, QUrl, QObject,
    QPropertyAnimation, QEasingCurve, QRect, QPoint, QMimeData
)
from PyQt6.QtGui import (
    QImage, QPixmap, QFont, QPalette, QColor, QIcon, QPainter, 
    QBrush, QPen, QLinearGradient, QDrag, QCursor, QAction
)

# Audio/Video processing
try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False
    print("[WARNING] OpenCV not available. Video features disabled.")

try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False
    print("[WARNING] PyAudio not available. Audio features disabled.")

try:
    from opuslib import Encoder, Decoder
    HAS_OPUS = True
except ImportError:
    HAS_OPUS = False
    print("[WARNING] Opus not available. Audio encoding disabled.")

# Screen capture
try:
    import mss
    from PIL import Image as PILImage
    HAS_SCREEN_CAPTURE = True
except ImportError:
    HAS_SCREEN_CAPTURE = False
    print("[WARNING] Screen capture not available.")

# Protocol constants
class MessageTypes:
    # Client to Server
    LOGIN = 'login'
    HEARTBEAT = 'heartbeat'
    CHAT = 'chat'
    BROADCAST = 'broadcast'
    UNICAST = 'unicast'
    GET_HISTORY = 'get_history'
    GET_PARTICIPANTS = 'get_participants'
    FILE_OFFER = 'file_offer'
    FILE_REQUEST = 'file_request'
    PRESENT_START = 'present_start'
    PRESENT_STOP = 'present_stop'
    LOGOUT = 'logout'
    MEDIA_STATUS_UPDATE = 'media_status_update'
    
    # Server to Client
    LOGIN_SUCCESS = 'login_success'
    PARTICIPANT_LIST = 'participant_list'
    HISTORY = 'history'
    USER_JOINED = 'user_joined'
    USER_LEFT = 'user_left'
    HEARTBEAT_ACK = 'heartbeat_ack'
    FILE_UPLOAD_PORT = 'file_upload_port'
    FILE_DOWNLOAD_PORT = 'file_download_port'
    FILE_AVAILABLE = 'file_available'
    SCREEN_SHARE_PORTS = 'screen_share_ports'
    PRESENT_START_BROADCAST = 'present_start_broadcast'
    PRESENT_STOP_BROADCAST = 'present_stop_broadcast'
    UNICAST_SENT = 'unicast_sent'
    ERROR = 'error'

# Network Configuration
DEFAULT_TCP_PORT = 9000
DEFAULT_UDP_VIDEO_PORT = 10000
DEFAULT_UDP_AUDIO_PORT = 11000
HEARTBEAT_INTERVAL = 10
MAX_RETRY_ATTEMPTS = 3
RECONNECT_ATTEMPTS = 5
RECONNECT_DELAY_BASE = 2.0

# Video settings
DEFAULT_FPS = 15
DEFAULT_QUALITY = 70
DEFAULT_SCALE = 0.5
FRAME_HEADER_SIZE = 4
MAX_CHAT_HISTORY = 500

# Audio settings
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
AUDIO_CHUNK_SIZE = 1600
AUDIO_BYTES_PER_SAMPLE = 2

# GUI Configuration
WINDOW_MIN_WIDTH = 1200
WINDOW_MIN_HEIGHT = 800
VIDEO_GRID_COLS = 3
VIDEO_FRAME_WIDTH = 320
VIDEO_FRAME_HEIGHT = 240

# Protocol helper functions
def create_login_message(username: str) -> dict:
    return {
        "type": MessageTypes.LOGIN,
        "username": username,
        "timestamp": datetime.now().isoformat()
    }

def create_heartbeat_message() -> dict:
    return {
        "type": MessageTypes.HEARTBEAT,
        "timestamp": datetime.now().isoformat()
    }

def create_chat_message(text: str) -> dict:
    return {
        "type": MessageTypes.CHAT,
        "content": text,
        "timestamp": datetime.now().isoformat()
    }

def create_logout_message() -> dict:
    return {
        "type": MessageTypes.LOGOUT,
        "timestamp": datetime.now().isoformat()
    }

def create_file_offer_message(fid: str, filename: str, size: int) -> dict:
    return {
        "type": MessageTypes.FILE_OFFER,
        "fid": fid,
        "filename": filename,
        "size": size,
        "timestamp": datetime.now().isoformat()
    }

def create_file_request_message(fid: str) -> dict:
    return {
        "type": MessageTypes.FILE_REQUEST,
        "fid": fid,
        "timestamp": datetime.now().isoformat()
    }

def create_present_start_message(topic: str) -> dict:
    return {
        "type": MessageTypes.PRESENT_START,
        "topic": topic,
        "timestamp": datetime.now().isoformat()
    }

def create_present_stop_message() -> dict:
    return {
        "type": MessageTypes.PRESENT_STOP,
        "timestamp": datetime.now().isoformat()
    }# 
#============================================================================
# VIDEO FRAME WIDGET
# ============================================================================

class VideoFrame(QLabel):
    """Individual video frame widget with user info overlay."""
    
    def __init__(self, uid: int = None, username: str = "Unknown", parent=None):
        super().__init__(parent)
        self.uid = uid
        self.username = username
        self.is_local = uid is None
        self.video_enabled = False
        self.audio_enabled = False
        
        # Setup frame
        self.setFixedSize(VIDEO_FRAME_WIDTH, VIDEO_FRAME_HEIGHT)
        self.setStyleSheet("""
            QLabel {
                border: 2px solid #333333;
                border-radius: 8px;
                background-color: #000000;
                color: white;
            }
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setScaledContents(True)
        
        # Default content
        self.set_placeholder()
        
    def set_placeholder(self):
        """Set placeholder content when no video."""
        if self.is_local:
            text = "📹 Your Video\n(Camera Off)"
        else:
            text = f"📹 {self.username}\n(Camera Off)"
        
        self.setText(text)
        self.setStyleSheet("""
            QLabel {
                border: 2px solid #333333;
                border-radius: 8px;
                background-color: #000000;
                color: #888888;
                font-size: 12px;
            }
        """)
    
    def set_video_frame(self, frame: np.ndarray):
        """Set video frame from numpy array."""
        try:
            if frame is not None and frame.size > 0:
                # Convert BGR to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Create QImage
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                
                # Scale to fit frame
                scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
                    self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                )
                
                self.setPixmap(scaled_pixmap)
                self.video_enabled = True
                
                # Update border color for active video
                self.setStyleSheet("""
                    QLabel {
                        border: 2px solid #0078d4;
                        border-radius: 8px;
                        background-color: #000000;
                    }
                """)
            else:
                self.set_placeholder()
                
        except Exception as e:
            print(f"[ERROR] Video frame error: {e}")
            self.set_placeholder()
    
    def set_audio_status(self, enabled: bool):
        """Update audio status indicator."""
        self.audio_enabled = enabled# =========
#===================================================================
# VIDEO GRID WIDGET
# ============================================================================

class VideoGrid(QWidget):
    """Grid layout for video frames with dynamic sizing."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.video_frames = {}  # uid -> VideoFrame
        self.local_frame = None
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create local video frame
        self.create_local_frame()
        
        # Set background
        self.setStyleSheet("""
            QWidget {
                background-color: #000000;
            }
        """)
    
    def create_local_frame(self):
        """Create local video frame."""
        self.local_frame = VideoFrame(uid=None, username="You")
        self.local_frame.is_local = True
        self.grid_layout.addWidget(self.local_frame, 0, 0)
    
    def add_participant_frame(self, uid: int, username: str):
        """Add video frame for participant."""
        if uid not in self.video_frames:
            frame = VideoFrame(uid=uid, username=username)
            self.video_frames[uid] = frame
            self.update_grid_layout()
    
    def remove_participant_frame(self, uid: int):
        """Remove video frame for participant."""
        if uid in self.video_frames:
            frame = self.video_frames[uid]
            self.grid_layout.removeWidget(frame)
            frame.deleteLater()
            del self.video_frames[uid]
            self.update_grid_layout()
    
    def update_grid_layout(self):
        """Update grid layout based on number of participants."""
        # Clear layout
        for i in reversed(range(self.grid_layout.count())):
            self.grid_layout.itemAt(i).widget().setParent(None)
        
        # Calculate grid dimensions
        total_frames = 1 + len(self.video_frames)  # +1 for local frame
        cols = min(VIDEO_GRID_COLS, total_frames)
        rows = (total_frames + cols - 1) // cols
        
        # Add local frame first
        self.grid_layout.addWidget(self.local_frame, 0, 0)
        
        # Add participant frames
        row, col = 0, 1
        for uid, frame in self.video_frames.items():
            if col >= cols:
                row += 1
                col = 0
            
            self.grid_layout.addWidget(frame, row, col)
            col += 1
    
    def update_local_video(self, frame: np.ndarray):
        """Update local video frame."""
        if self.local_frame:
            self.local_frame.set_video_frame(frame)
    
    def update_participant_video(self, uid: int, frame: np.ndarray):
        """Update participant video frame."""
        if uid in self.video_frames:
            self.video_frames[uid].set_video_frame(frame)# 
#============================================================================
# CHAT WIDGET
# ============================================================================

class ChatWidget(QWidget):
    """Comprehensive chat widget with history, private messages, file sharing."""
    
    message_sent = pyqtSignal(str)  # Signal for sending messages
    file_share_requested = pyqtSignal(str)  # Signal for file sharing
    file_list_requested = pyqtSignal()  # Signal for requesting file list
    file_download_requested = pyqtSignal(str, str)  # Signal for downloading file (file_id, filename)
    private_message_sent = pyqtSignal(int, str)  # Signal for private messages
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.chat_history = []
        self.participants = {}  # uid -> participant_info
        self.setup_ui()
        
    def setup_ui(self):
        """Setup chat UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Chat display area
        self.chat_display = QTextBrowser()
        self.chat_display.setStyleSheet("""
            QTextBrowser {
                background-color: #000000;
                color: white;
                border: 1px solid #333333;
                border-radius: 5px;
                padding: 10px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.chat_display)
        
        # Input area
        input_frame = QFrame()
        input_frame.setStyleSheet("""
            QFrame {
                background-color: #333333;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(5, 5, 5, 5)
        
        # Message input
        self.message_input = QLineEdit()
        self.message_input.setStyleSheet("""
            QLineEdit {
                background-color: #000000;
                color: white;
                border: 1px solid #333333;
                border-radius: 3px;
                padding: 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #0078d4;
            }
        """)
        self.message_input.setPlaceholderText("Type a message...")
        self.message_input.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.message_input)
        
        # File upload button
        file_upload_btn = QPushButton("📎")
        file_upload_btn.setToolTip("Upload File")
        file_upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 10px;
                font-weight: bold;
                min-width: 35px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        file_upload_btn.clicked.connect(lambda: self.upload_file())
        input_layout.addWidget(file_upload_btn)
        
        # File download button
        file_download_btn = QPushButton("📥")
        file_download_btn.setToolTip("Download Files")
        file_download_btn.setStyleSheet("""
            QPushButton {
                background-color: #6f42c1;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 10px;
                font-weight: bold;
                min-width: 35px;
            }
            QPushButton:hover {
                background-color: #5a32a3;
            }
            QPushButton:pressed {
                background-color: #4c2a85;
            }
        """)
        file_download_btn.clicked.connect(self.show_file_list)
        input_layout.addWidget(file_download_btn)
        
        # Send button
        send_btn = QPushButton("Send")
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(send_btn)
        
        layout.addWidget(input_frame)
    
    def send_message(self):
        """Send chat message."""
        text = self.message_input.text().strip()
        if text:
            self.message_sent.emit(text)
            self.message_input.clear()
    
    def add_message(self, sender: str, text: str, timestamp: str = None, is_system: bool = False):
        """Add message to chat display."""
        if timestamp is None:
            timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Format message
        if is_system:
            html = f"""
            <div style="color: #ffd43b; font-style: italic; margin: 5px 0;">
                <span style="color: #888;">[{timestamp}]</span> {text}
            </div>
            """
        else:
            sender_color = "#0078d4" if sender == "You" else "#28a745"
            html = f"""
            <div style="margin: 8px 0;">
                <span style="color: #888;">[{timestamp}]</span>
                <span style="color: {sender_color}; font-weight: bold;">{sender}:</span>
                <span style="color: white;">{text}</span>
            </div>
            """
        
        self.chat_display.append(html)
        
        # Auto-scroll to bottom
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def add_private_message(self, sender: str, text: str, timestamp: str = None):
        """Add private message to chat display with special formatting."""
        if timestamp is None:
            timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Format private message with distinct styling
        html = f"""
        <div style="margin: 8px 0; background-color: #111111; border-left: 3px solid #9d4edd; padding: 8px; border-radius: 5px;">
            <span style="color: #888;">[{timestamp}]</span>
            <span style="color: #9d4edd; font-weight: bold;">🔒 {sender} (private):</span>
            <span style="color: #e0e0e0;">{text}</span>
        </div>
        """
        
        self.chat_display.append(html)
        
        # Auto-scroll to bottom
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_chat(self):
        """Clear chat display."""
        self.chat_display.clear()
    
    def upload_file(self):
        """Handle file upload."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select File to Upload", 
            "", 
            "All Files (*.*)"
        )
        
        # Ensure we have a valid file path before emitting
        if file_path and isinstance(file_path, str) and file_path.strip():
            self.file_share_requested.emit(file_path)
            self.add_message("System", f"Uploading file: {Path(file_path).name}", is_system=True)
    
    def show_file_list(self):
        """Show available files for download."""
        # This will be connected to a signal that requests the file list from server
        self.file_list_requested.emit()
    
    def show_file_download_dialog(self, files: List[dict]):
        """Show dialog with available files for download."""
        if not files:
            QMessageBox.information(self, "No Files", "No files are currently available for download.")
            return
        
        dialog = FileListDialog(files, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_file = dialog.get_selected_file()
            if selected_file:
                self.file_download_requested.emit(selected_file['file_id'], selected_file['filename'])#
# ============================================================================
# PARTICIPANTS WIDGET
# ============================================================================

class ParticipantsWidget(QWidget):
    """Participants list with controls and status indicators."""
    
    private_message_requested = pyqtSignal(int, str)  # uid, username
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.participants = {}  # uid -> participant_info
        self.setup_ui()
        
    def setup_ui(self):
        """Setup participants UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Header
        header = QLabel("👥 Participants")
        header.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                background-color: #333333;
                border-radius: 5px;
            }
        """)
        layout.addWidget(header)
        
        # Participants list
        self.participants_list = QListWidget()
        self.participants_list.setStyleSheet("""
            QListWidget {
                background-color: #000000;
                color: white;
                border: 1px solid #333333;
                border-radius: 5px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #333333;
            }
            QListWidget::item:hover {
                background-color: #333333;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
            }
        """)
        self.participants_list.itemDoubleClicked.connect(self.on_participant_double_click)
        layout.addWidget(self.participants_list)
    
    def update_participants(self, participants: dict):
        """Update participants list."""
        self.participants = participants
        self.refresh_list()
    
    def add_participant(self, uid: int, username: str):
        """Add participant to list."""
        self.participants[uid] = {
            'uid': uid,
            'username': username,
            'video_enabled': False,
            'audio_enabled': False,
            'screen_sharing': False
        }
        self.refresh_list()
    
    def remove_participant(self, uid: int):
        """Remove participant from list."""
        if uid in self.participants:
            del self.participants[uid]
            self.refresh_list()
    
    def refresh_list(self):
        """Refresh participants list display."""
        self.participants_list.clear()
        
        for uid, participant in self.participants.items():
            username = participant['username']
            
            # Status indicators
            video_icon = "📹" if participant.get('video_enabled', False) else "📷"
            audio_icon = "🎤" if participant.get('audio_enabled', False) else "🔇"
            
            # Create list item
            item_text = f"{video_icon} {audio_icon} {username}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, uid)
            
            self.participants_list.addItem(item)
    
    def on_participant_double_click(self, item):
        """Handle participant double click."""
        uid = item.data(Qt.ItemDataRole.UserRole)
        if uid in self.participants:
            username = self.participants[uid]['username']
            self.private_message_requested.emit(uid, username)# ======
#======================================================================
# MEDIA CONTROLS WIDGET
# ============================================================================

class MediaControlsWidget(QWidget):
    """Media controls for video, audio, screen sharing."""
    
    video_toggle_requested = pyqtSignal(bool)
    audio_toggle_requested = pyqtSignal(bool)
    screen_share_requested = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.video_enabled = False
        self.audio_enabled = False
        self.screen_sharing = False
        self.setup_ui()
        
    def setup_ui(self):
        """Setup media controls UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Video button
        self.video_btn = QPushButton("📹 Video")
        self.video_btn.setCheckable(True)
        self.video_btn.setStyleSheet(self.get_button_style("#dc3545"))  # Red when off
        self.video_btn.clicked.connect(self.toggle_video)
        layout.addWidget(self.video_btn)
        
        # Audio button
        self.audio_btn = QPushButton("🎤 Audio")
        self.audio_btn.setCheckable(True)
        self.audio_btn.setStyleSheet(self.get_button_style("#dc3545"))  # Red when off
        self.audio_btn.clicked.connect(self.toggle_audio)
        layout.addWidget(self.audio_btn)
        
        # Screen share button
        self.screen_btn = QPushButton("🖥️ Share")
        self.screen_btn.setCheckable(True)
        self.screen_btn.setStyleSheet(self.get_button_style("#6c757d"))  # Gray when off
        self.screen_btn.clicked.connect(self.toggle_screen_share)
        layout.addWidget(self.screen_btn)
        
        # Spacer
        layout.addStretch()
        
        # Disconnect button
        self.disconnect_btn = QPushButton("🚪 Leave")
        self.disconnect_btn.setStyleSheet(self.get_button_style("#dc3545"))
        layout.addWidget(self.disconnect_btn)
    
    def get_button_style(self, color: str) -> str:
        """Get button style with specified color."""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 15px;
                font-size: 12px;
                font-weight: bold;
                min-width: 80px;
            }}
            QPushButton:hover {{
                opacity: 0.8;
            }}
            QPushButton:pressed {{
                background-color: #555;
            }}
            QPushButton:checked {{
                background-color: #28a745;
            }}
        """
    
    def toggle_video(self):
        """Toggle video on/off."""
        self.video_enabled = not self.video_enabled
        self.video_btn.setChecked(self.video_enabled)
        self.video_btn.setText("📹 Video On" if self.video_enabled else "📹 Video Off")
        self.video_toggle_requested.emit(self.video_enabled)
    
    def toggle_audio(self):
        """Toggle audio on/off."""
        self.audio_enabled = not self.audio_enabled
        self.audio_btn.setChecked(self.audio_enabled)
        self.audio_btn.setText("🎤 Audio On" if self.audio_enabled else "🎤 Audio Off")
        self.audio_toggle_requested.emit(self.audio_enabled)
    
    def toggle_screen_share(self):
        """Toggle screen sharing on/off."""
        self.screen_sharing = not self.screen_sharing
        self.screen_btn.setChecked(self.screen_sharing)
        self.screen_btn.setText("🖥️ Sharing" if self.screen_sharing else "🖥️ Share")
        self.screen_share_requested.emit(self.screen_sharing)
    
    def connect_parent_signals(self):
        """Connect signals that require parent access."""
        if self.parent():
            self.disconnect_btn.clicked.connect(self.parent().disconnect_from_server)

# ============================================================================
# NETWORKING COMPONENTS
# ============================================================================

class NetworkThread(QThread):
    """Thread for handling network operations."""
    
    message_received = pyqtSignal(dict)
    connection_status_changed = pyqtSignal(bool, str)
    
    def __init__(self, host: str, port: int, username: str, parent=None):
        super().__init__(parent)
        self.host = host
        self.port = port
        self.username = username
        self.running = False
        self.connected = False
        self.reader = None
        self.writer = None
        self.uid = None
        
    def run(self):
        """Run network thread."""
        try:
            # Create new event loop for this thread
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Run async client
            self.loop.run_until_complete(self.async_client())
            
        except Exception as e:
            print(f"[ERROR] Network thread error: {e}")
            self.connection_status_changed.emit(False, f"Network error: {e}")
    
    async def async_client(self):
        """Async client implementation."""
        try:
            self.running = True
            
            # Connect to server
            if not await self.connect():
                return
            
            # Send login
            await self.send_login()
            
            # Start heartbeat
            heartbeat_task = asyncio.create_task(self.heartbeat_loop())
            
            # Listen for messages
            await self.listen_for_messages()
            
        except Exception as e:
            print(f"[ERROR] Async client error: {e}")
        finally:
            self.running = False
            if self.writer:
                self.writer.close()
                await self.writer.wait_closed()
    
    async def connect(self):
        """Connect to server."""
        try:
            print(f"[INFO] Attempting to connect to {self.host}:{self.port}")
            
            # Test basic connectivity first
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.settimeout(5)
            
            try:
                result = test_sock.connect_ex((self.host, self.port))
                test_sock.close()
                
                if result != 0:
                    raise ConnectionError(f"Cannot reach server at {self.host}:{self.port}")
            except Exception as e:
                test_sock.close()
                raise ConnectionError(f"Network error: {e}")
            
            # Now try async connection
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), 
                timeout=10
            )
            
            self.connected = True
            print(f"[INFO] Successfully connected to {self.host}:{self.port}")
            self.connection_status_changed.emit(True, "Connected")
            return True
            
        except asyncio.TimeoutError:
            error_msg = f"Connection timeout to {self.host}:{self.port}"
            print(f"[ERROR] {error_msg}")
            self.connection_status_changed.emit(False, error_msg)
            return False
        except Exception as e:
            error_msg = f"Connection failed: {e}"
            print(f"[ERROR] {error_msg}")
            self.connection_status_changed.emit(False, error_msg)
            return False
    
    async def send_login(self):
        """Send login message."""
        login_msg = create_login_message(self.username)
        await self.send_message(login_msg)
    
    async def heartbeat_loop(self):
        """Send periodic heartbeats."""
        while self.running and self.connected:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            if self.running and self.connected:
                heartbeat_msg = create_heartbeat_message()
                await self.send_message(heartbeat_msg)
    
    async def listen_for_messages(self):
        """Listen for incoming messages."""
        while self.running and self.connected:
            try:
                # Read message length (4 bytes)
                length_data = await self.reader.read(4)
                if not length_data or len(length_data) != 4:
                    print("[ERROR] Failed to read message length")
                    break
                
                message_length = struct.unpack('!I', length_data)[0]
                if message_length > 1024 * 1024:  # 1MB limit
                    print(f"[ERROR] Message too large: {message_length}")
                    break
                
                # Read message data
                message_data = await self.reader.readexactly(message_length)
                if not message_data:
                    print("[ERROR] Failed to read message data")
                    break
                
                message = json.loads(message_data.decode('utf-8'))
                self.message_received.emit(message)
                
            except Exception as e:
                print(f"[ERROR] Listen error: {e}")
                break
        
        self.connected = False
        self.connection_status_changed.emit(False, "Disconnected")
    
    async def send_message(self, message: dict):
        """Send message to server."""
        try:
            if self.writer and self.connected:
                message_data = json.dumps(message).encode('utf-8')
                length_data = struct.pack('!I', len(message_data))
                self.writer.write(length_data + message_data)
                await self.writer.drain()
        except Exception as e:
            print(f"[ERROR] Send message error: {e}")
    
    def send_message_sync(self, message: dict):
        """Send message synchronously (for GUI thread)."""
        if self.connected and hasattr(self, 'loop') and self.loop:
            # Schedule message sending in the network thread's event loop
            asyncio.run_coroutine_threadsafe(
                self.send_message(message), 
                self.loop
            )
    
    def disconnect(self):
        """Disconnect from server."""
        self.running = False
        self.connected = False


class VideoClient(QThread):
    """Video capture and streaming client."""
    
    frame_captured = pyqtSignal(np.ndarray)  # Local frame captured
    frame_received = pyqtSignal(int, np.ndarray)  # Remote frame received (uid, frame)
    video_disabled = pyqtSignal()  # Signal when video is disabled
    
    def __init__(self, server_host: str, server_port: int, parent=None):
        super().__init__(parent)
        self.server_host = server_host
        self.server_port = server_port
        self.running = False
        self.enabled = False
        self.cap = None
        self.socket = None
        self.uid = None
        self.sequence = 0
        
    def set_uid(self, uid: int):
        """Set user ID."""
        self.uid = uid
    
    def set_enabled(self, enabled: bool):
        """Enable/disable video capture."""
        was_enabled = self.enabled
        self.enabled = enabled
        
        if enabled:
            print("[DEBUG] Video enabled")
        else:
            print("[DEBUG] Video disabled")
            # Emit signal to clear local video display
            if was_enabled:  # Only emit if it was previously enabled
                self.video_disabled.emit()
    
    def run(self):
        """Run video capture loop."""
        if not HAS_OPENCV:
            return
        
        try:
            self.running = True
            
            # Initialize camera with retry logic
            for attempt in range(3):
                self.cap = cv2.VideoCapture(0)
                if self.cap.isOpened():
                    break
                else:
                    print(f"[WARNING] Camera open attempt {attempt + 1} failed")
                    if self.cap:
                        self.cap.release()
                    self.msleep(500)  # Wait before retry
            
            if not self.cap or not self.cap.isOpened():
                print("[ERROR] Could not open camera after 3 attempts")
                return
            
            # Set camera properties for smaller frames
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
            self.cap.set(cv2.CAP_PROP_FPS, DEFAULT_FPS)
            
            print("[DEBUG] Camera initialized successfully")
            
            # Initialize UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(0.1)  # Non-blocking with short timeout
            
            print(f"[DEBUG] Video client started, waiting for UID to be set...")
            
            while self.running:
                # Always capture frames to keep camera active (prevents segfault)
                if self.cap is not None:
                    ret, frame = self.cap.read()
                    if ret:
                        # Only emit and send frames if video is enabled
                        if self.enabled:
                            # Emit frame for local display
                            self.frame_captured.emit(frame)
                            
                            # Send frame to server if connected
                            if self.uid and self.socket:
                                self.send_frame(frame)
                        # If disabled, we still read frames but don't use them
                        # This keeps the camera active and prevents segfaults
                    else:
                        # Camera read failed
                        print("[WARNING] Camera read failed")
                        self.msleep(100)  # Wait a bit before trying again
                
                # Check for incoming video from server
                try:
                    data, addr = self.socket.recvfrom(65536)
                    self.handle_incoming_video(data)
                except socket.timeout:
                    pass  # No data received, continue
                except Exception:
                    pass  # Ignore other socket errors
                
                self.msleep(1000 // DEFAULT_FPS)  # Control FPS
                
        except Exception as e:
            print(f"[ERROR] Video client error: {e}")
        finally:
            # Safe cleanup to prevent segfaults
            if self.cap:
                try:
                    self.cap.release()
                    print("[DEBUG] Camera released safely")
                except Exception as e:
                    print(f"[WARNING] Camera release error: {e}")
                finally:
                    self.cap = None
            
            if self.socket:
                try:
                    self.socket.close()
                except Exception:
                    pass
                finally:
                    self.socket = None
            
            self.running = False
    
    def send_frame(self, frame: np.ndarray):
        """Send frame to server."""
        try:
            # Resize frame to ensure it's small enough
            small_frame = cv2.resize(frame, (320, 240))
            
            # Encode frame as JPEG with lower quality for smaller size
            _, encoded = cv2.imencode('.jpg', small_frame, [cv2.IMWRITE_JPEG_QUALITY, 30])  # Lower quality
            frame_data = encoded.tobytes()
            
            # Check if packet is too large (UDP limit is ~65KB, leave room for header)
            if len(frame_data) > 60000:
                # Further reduce quality if still too large
                _, encoded = cv2.imencode('.jpg', small_frame, [cv2.IMWRITE_JPEG_QUALITY, 15])
                frame_data = encoded.tobytes()
            
            # Create packet header (uid, sequence, frame_id, data_size)
            frame_id = self.sequence  # Use sequence as frame_id
            header = struct.pack('!IIII', self.uid, self.sequence, frame_id, len(frame_data))
            packet = header + frame_data
            
            # Send packet
            self.socket.sendto(packet, (self.server_host, self.server_port))
            self.sequence += 1
            
            if self.sequence % 30 == 0:  # Debug every 30 frames (2 seconds at 15fps)
                print(f"[DEBUG] Sent video frame {self.sequence} to {self.server_host}:{self.server_port}")
            
        except Exception as e:
            print(f"[ERROR] Send frame error: {e}")
    
    def handle_incoming_video(self, data: bytes):
        """Handle incoming video from server."""
        try:
            if len(data) < 16:
                return
            
            uid, sequence, frame_id, data_size = struct.unpack('!IIII', data[:16])
            
            # Don't process our own video
            if uid == self.uid:
                return
            
            video_data = data[16:]
            if len(video_data) != data_size:
                return
            
            # Decode video frame
            frame_array = np.frombuffer(video_data, dtype=np.uint8)
            frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
            
            if frame is not None:
                self.frame_received.emit(uid, frame)
                print(f"[DEBUG] Received video frame from UID {uid}")
                
        except Exception as e:
            print(f"[ERROR] Video receive error: {e}")
    
    def stop(self):
        """Stop video capture."""
        self.running = False
        self.enabled = False


class AudioClient(QThread):
    """Audio capture and streaming client."""
    
    def __init__(self, server_host: str, server_port: int, parent=None):
        super().__init__(parent)
        self.server_host = server_host
        self.server_port = server_port
        self.running = False
        self.enabled = False
        self.audio = None
        self.input_stream = None
        self.socket = None
        self.uid = None
        self.sequence = 0
        
    def set_uid(self, uid: int):
        """Set user ID."""
        self.uid = uid
    
    def set_enabled(self, enabled: bool):
        """Enable/disable audio capture."""
        self.enabled = enabled
    
    def run(self):
        """Run audio capture loop."""
        if not HAS_PYAUDIO:
            return
        
        try:
            self.running = True
            
            # Initialize PyAudio
            self.audio = pyaudio.PyAudio()
            
            # Open input stream
            self.input_stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=AUDIO_CHANNELS,
                rate=AUDIO_SAMPLE_RATE,
                input=True,
                frames_per_buffer=AUDIO_CHUNK_SIZE
            )
            
            # Initialize UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(0.01)  # Very short timeout for audio
            
            print(f"[DEBUG] Audio client started, waiting for UID to be set...")
            
            # Initialize output stream for playing received audio
            self.output_stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=AUDIO_CHANNELS,
                rate=AUDIO_SAMPLE_RATE,
                output=True,
                frames_per_buffer=AUDIO_CHUNK_SIZE
            )
            
            while self.running:
                # Capture and send audio if enabled
                if self.enabled:
                    # Read audio data
                    audio_data = self.input_stream.read(AUDIO_CHUNK_SIZE, exception_on_overflow=False)
                    
                    # Send to server if connected
                    if self.uid and self.socket:
                        self.send_audio(audio_data)
                
                # Check for incoming audio from server
                try:
                    data, addr = self.socket.recvfrom(4096)
                    self.handle_incoming_audio(data)
                except socket.timeout:
                    pass  # No data received, continue
                except Exception:
                    pass  # Ignore other socket errors
                
        except Exception as e:
            print(f"[ERROR] Audio client error: {e}")
        finally:
            if self.input_stream:
                self.input_stream.stop_stream()
                self.input_stream.close()
            if self.output_stream:
                self.output_stream.stop_stream()
                self.output_stream.close()
            if self.audio:
                self.audio.terminate()
            if self.socket:
                self.socket.close()
            self.running = False
    
    def send_audio(self, audio_data: bytes):
        """Send audio data to server."""
        try:
            # Create packet header
            header = struct.pack('!III', self.uid, self.sequence, len(audio_data))
            packet = header + audio_data
            
            # Send packet
            self.socket.sendto(packet, (self.server_host, self.server_port))
            self.sequence += 1
            
        except Exception as e:
            print(f"[ERROR] Send audio error: {e}")
    
    def handle_incoming_audio(self, data: bytes):
        """Handle incoming audio from server."""
        try:
            if len(data) < 12:
                return
            
            uid, sequence, data_size = struct.unpack('!III', data[:12])
            
            # Don't play our own audio back
            if uid == self.uid:
                return
            
            audio_data = data[12:]
            if len(audio_data) != data_size:
                return
            
            # Play audio data
            if self.output_stream:
                self.output_stream.write(audio_data)
                
        except Exception as e:
            print(f"[ERROR] Audio receive error: {e}")
    
    def stop(self):
        """Stop audio capture."""
        self.running = False
        self.enabled = False



# ============================================================================
# CONNECTION DIALOG
# ============================================================================

class ConnectionDialog(QDialog):
    """Connection dialog for server details and user info."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect to LAN Collaboration Server")
        self.setFixedSize(500, 400)
        self.setModal(True)
        
        # Use system default styling for better compatibility
        # No custom styling to avoid input field issues
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup connection dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel("🌐 LAN Collaboration Client")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #0078d4; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # Form
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        # Server IP with help
        ip_layout = QVBoxLayout()
        self.server_ip_input = QLineEdit("localhost")
        self.server_ip_input.setPlaceholderText("localhost, 192.168.1.100, etc.")
        self.server_ip_input.setEnabled(True)
        self.server_ip_input.setReadOnly(False)
        self.server_ip_input.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        ip_layout.addWidget(self.server_ip_input)
        
        # IP help text
        ip_help = QLabel("💡 Use 'localhost' for same machine, or server's IP address for remote connection")
        ip_help.setWordWrap(True)
        ip_layout.addWidget(ip_help)
        
        form_layout.addRow("Server IP:", ip_layout)
        
        # Server Port
        self.server_port_input = QLineEdit(str(DEFAULT_TCP_PORT))
        self.server_port_input.setEnabled(True)
        self.server_port_input.setReadOnly(False)
        self.server_port_input.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        form_layout.addRow("Server Port:", self.server_port_input)
        
        # Username
        self.username_input = QLineEdit(f"User_{int(time.time()) % 1000}")
        self.username_input.setEnabled(True)
        self.username_input.setReadOnly(False)
        self.username_input.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        form_layout.addRow("Your Name:", self.username_input)
        
        layout.addLayout(form_layout)
        
        # Quick IP buttons
        ip_buttons_layout = QHBoxLayout()
        
        localhost_btn = QPushButton("🏠 Localhost")
        localhost_btn.setToolTip("Connect to server on same machine")
        localhost_btn.clicked.connect(lambda: self.server_ip_input.setText("localhost"))

        ip_buttons_layout.addWidget(localhost_btn)
        
        local_ip_btn = QPushButton("🌐 Local IP")
        local_ip_btn.setToolTip("Use this machine's IP address")
        local_ip_btn.clicked.connect(self.set_local_ip)

        ip_buttons_layout.addWidget(local_ip_btn)
        
        ip_buttons_layout.addStretch()
        layout.addLayout(ip_buttons_layout)
        
        # Pre-connection settings
        settings_group = QGroupBox("Join Settings")

        settings_layout = QVBoxLayout(settings_group)
        
        self.join_with_video = QCheckBox("📹 Join with camera on")
        settings_layout.addWidget(self.join_with_video)
        
        self.join_with_audio = QCheckBox("🎤 Join with microphone on")
        settings_layout.addWidget(self.join_with_audio)
        
        layout.addWidget(settings_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        button_layout.addStretch()
        
        connect_btn = QPushButton("🚀 Connect")
        connect_btn.clicked.connect(self.accept)
        connect_btn.setDefault(True)
        button_layout.addWidget(connect_btn)
        
        layout.addLayout(button_layout)
    
    def set_local_ip(self):
        """Set the local IP address."""
        try:
            # Get local IP address
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            self.server_ip_input.setText(local_ip)
        except Exception:
            # Fallback method
            try:
                import subprocess
                result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
                if result.returncode == 0:
                    local_ip = result.stdout.strip().split()[0]
                    self.server_ip_input.setText(local_ip)
                else:
                    QMessageBox.warning(self, "IP Detection", "Could not detect local IP address")
            except Exception:
                QMessageBox.warning(self, "IP Detection", "Could not detect local IP address")
    
    def get_connection_info(self):
        """Get connection information."""
        return {
            'host': self.server_ip_input.text().strip(),
            'port': int(self.server_port_input.text().strip()),
            'username': self.username_input.text().strip(),
            'join_with_video': self.join_with_video.isChecked(),
            'join_with_audio': self.join_with_audio.isChecked()
        }


# ============================================================================
# FILE LIST DIALOG
# ============================================================================

class FileListDialog(QDialog):
    """Dialog for showing available files for download."""
    
    def __init__(self, files: List[dict], parent=None):
        super().__init__(parent)
        self.files = files
        self.selected_file = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup file list dialog UI."""
        self.setWindowTitle("Available Files")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("📁 Available Files for Download")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078d4; margin-bottom: 15px;")
        layout.addWidget(title)
        
        # File table
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(4)
        self.file_table.setHorizontalHeaderLabels(["Filename", "Size", "Uploader", "Upload Time"])
        
        # Style the table
        self.file_table.setStyleSheet("""
            QTableWidget {
                background-color: #000000;
                color: white;
                border: 1px solid #333333;
                border-radius: 5px;
                gridline-color: #333333;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #333333;
            }
            QTableWidget::item:selected {
                background-color: #0078d4;
            }
            QHeaderView::section {
                background-color: #333333;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        
        # Populate table
        self.file_table.setRowCount(len(self.files))
        for i, file_info in enumerate(self.files):
            # Filename
            filename_item = QTableWidgetItem(file_info['filename'])
            self.file_table.setItem(i, 0, filename_item)
            
            # Size (format bytes)
            size_bytes = file_info['size']
            if size_bytes < 1024:
                size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
            
            size_item = QTableWidgetItem(size_str)
            self.file_table.setItem(i, 1, size_item)
            
            # Uploader
            uploader_item = QTableWidgetItem(file_info['uploader'])
            self.file_table.setItem(i, 2, uploader_item)
            
            # Upload time
            timestamp = file_info['timestamp']
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime("%Y-%m-%d %H:%M")
            except:
                time_str = timestamp
            
            time_item = QTableWidgetItem(time_str)
            self.file_table.setItem(i, 3, time_item)
        
        # Resize columns
        header = self.file_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        # Selection mode
        self.file_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.file_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        layout.addWidget(self.file_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        button_layout.addStretch()
        
        download_btn = QPushButton("📥 Download Selected")
        download_btn.clicked.connect(self.download_selected)
        download_btn.setDefault(True)
        download_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        button_layout.addWidget(download_btn)
        
        layout.addLayout(button_layout)
    
    def download_selected(self):
        """Download the selected file."""
        current_row = self.file_table.currentRow()
        if current_row >= 0:
            self.selected_file = self.files[current_row]
            self.accept()
        else:
            QMessageBox.warning(self, "No Selection", "Please select a file to download.")
    
    def get_selected_file(self):
        """Get the selected file info."""
        return self.selected_file


# ============================================================================
# FILE UPLOAD THREAD
# ============================================================================

class FileUploadThread(QThread):
    """Thread for uploading files to server."""
    
    upload_progress = pyqtSignal(str, int)  # filename, progress percentage
    upload_finished = pyqtSignal(str)  # filename
    upload_error = pyqtSignal(str, str)  # filename, error_message
    
    def __init__(self, host: str, port: int, file_path: str, uploader: str, parent=None):
        super().__init__(parent)
        self.host = host
        self.port = port
        # Ensure file_path is a string
        self.file_path = str(file_path) if file_path else ""
        self.uploader = uploader
        self.filename = Path(self.file_path).name if self.file_path else "unknown"
        
    def run(self):
        """Run the upload process."""
        try:
            # Validate file path
            if not self.file_path or not isinstance(self.file_path, str):
                self.upload_error.emit(self.filename, "Invalid file path")
                return
                
            file_info = Path(self.file_path)
            if not file_info.exists():
                self.upload_error.emit(self.filename, "File not found")
                return
            
            file_size = file_info.stat().st_size
            
            # Connect to upload server
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.port))
            
            # Send file info
            upload_info = {
                'filename': self.filename,
                'size': file_size,
                'uploader': self.uploader
            }
            
            info_data = json.dumps(upload_info).encode('utf-8')
            info_size = struct.pack('!I', len(info_data))
            sock.send(info_size + info_data)
            
            # Wait for OK response
            response = sock.recv(1024)
            if not response.startswith(b'OK'):
                error_msg = response.decode('utf-8', errors='ignore')
                self.upload_error.emit(self.filename, error_msg)
                return
            
            # Upload file data
            sent = 0
            with open(self.file_path, 'rb') as f:
                while sent < file_size:
                    chunk_size = min(8192, file_size - sent)
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    sock.send(chunk)
                    sent += len(chunk)
                    
                    # Update progress
                    progress = int((sent / file_size) * 100)
                    self.upload_progress.emit(self.filename, progress)
            
            # Wait for final response
            final_response = sock.recv(1024)
            sock.close()
            
            if sent == file_size:
                self.upload_finished.emit(self.filename)
            else:
                self.upload_error.emit(self.filename, "Incomplete upload")
                
        except Exception as e:
            self.upload_error.emit(self.filename, str(e))


# ============================================================================
# FILE DOWNLOAD THREAD
# ============================================================================

class FileDownloadThread(QThread):
    """Thread for downloading files from server."""
    
    download_progress = pyqtSignal(str, int)  # filename, progress percentage
    download_finished = pyqtSignal(str, str)  # filename, save_path
    download_error = pyqtSignal(str, str)  # filename, error_message
    
    def __init__(self, host: str, port: int, file_id: str, save_path: str, parent=None):
        super().__init__(parent)
        self.host = host
        self.port = port
        self.file_id = file_id
        self.save_path = save_path
        self.filename = Path(save_path).name
        
    def run(self):
        """Run the download process."""
        try:
            # Connect to download server
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.port))
            
            # Send file ID
            file_id_data = self.file_id.encode('utf-8')
            id_size = struct.pack('!I', len(file_id_data))
            sock.send(id_size + file_id_data)
            
            # Read file info
            info_size_data = sock.recv(4)
            if not info_size_data:
                self.download_error.emit(self.filename, "Failed to receive file info")
                return
            
            info_size = struct.unpack('!I', info_size_data)[0]
            info_data = sock.recv(info_size)
            
            if info_data.startswith(b'ERROR'):
                error_msg = info_data.decode('utf-8')
                self.download_error.emit(self.filename, error_msg)
                return
            
            file_info = json.loads(info_data.decode('utf-8'))
            file_size = file_info['size']
            
            # Download file data
            received = 0
            with open(self.save_path, 'wb') as f:
                while received < file_size:
                    chunk_size = min(8192, file_size - received)
                    chunk = sock.recv(chunk_size)
                    if not chunk:
                        break
                    
                    f.write(chunk)
                    received += len(chunk)
                    
                    # Update progress
                    progress = int((received / file_size) * 100)
                    self.download_progress.emit(self.filename, progress)
            
            sock.close()
            
            if received == file_size:
                self.download_finished.emit(self.filename, self.save_path)
            else:
                self.download_error.emit(self.filename, "Incomplete download")
                
        except Exception as e:
            self.download_error.emit(self.filename, str(e))


# ============================================================================
# SCREEN SHARING COMPONENTS
# ============================================================================

class ScreenCaptureClient(QThread):
    """Captures screen and sends to server for sharing."""
    
    def __init__(self, server_host: str, server_port: int, parent=None):
        super().__init__(parent)
        self.server_host = server_host
        self.server_port = server_port
        self.running = False
        self.socket = None
        
    def run(self):
        """Run screen capture loop."""
        try:
            self.running = True
            
            # Connect to screen share server
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            
            # Send presenter type
            self.socket.send(struct.pack('!I', 1))  # 1 = presenter
            
            # Wait for OK response
            response = self.socket.recv(1024)
            if response != b'OK':
                print(f"[ERROR] Screen share server rejected connection: {response}")
                return
            
            print("[INFO] Screen sharing started - capturing screen")
            
            while self.running:
                try:
                    # Capture screen
                    screenshot = self.capture_screen()
                    if screenshot:
                        # Send frame size
                        frame_size = struct.pack('!I', len(screenshot))
                        self.socket.send(frame_size)
                        
                        # Send frame data
                        self.socket.send(screenshot)
                    
                    self.msleep(100)  # 10 FPS for screen sharing
                    
                except Exception as e:
                    print(f"[ERROR] Screen capture error: {e}")
                    break
                    
        except Exception as e:
            print(f"[ERROR] Screen capture client error: {e}")
        finally:
            if self.socket:
                self.socket.close()
            self.running = False
            print("[INFO] Screen sharing stopped")
    
    def capture_screen(self):
        """Capture the screen and return as compressed image."""
        try:
            if not HAS_OPENCV:
                return None
            
            # Use different methods based on platform
            if sys.platform == "darwin":  # macOS
                # Use screencapture command
                import subprocess
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    subprocess.run(['screencapture', '-x', tmp.name], check=True)
                    screenshot = cv2.imread(tmp.name)
                    os.unlink(tmp.name)
            else:
                # For other platforms, try using PIL if available
                try:
                    from PIL import ImageGrab
                    import numpy as np
                    pil_image = ImageGrab.grab()
                    screenshot = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                except ImportError:
                    print("[ERROR] Screen capture requires PIL/Pillow: pip install Pillow")
                    return None
                except Exception as e:
                    print(f"[ERROR] Screen capture failed: {e}")
                    return None
            
            if screenshot is not None:
                # Resize for better performance
                height, width = screenshot.shape[:2]
                new_width = min(1280, width)
                new_height = int(height * (new_width / width))
                screenshot = cv2.resize(screenshot, (new_width, new_height))
                
                # Compress as JPEG
                _, encoded = cv2.imencode('.jpg', screenshot, [cv2.IMWRITE_JPEG_QUALITY, 60])
                return encoded.tobytes()
            
        except Exception as e:
            print(f"[ERROR] Screen capture failed: {e}")
        
        return None
    
    def stop(self):
        """Stop screen capture."""
        self.running = False


class ScreenPreviewCapture(QThread):
    """Captures screen for preview display in the Screen Share tab."""
    
    preview_frame_ready = pyqtSignal(np.ndarray)  # Signal to emit captured frames
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = False
        
    def run(self):
        """Run preview capture loop."""
        try:
            self.running = True
            print("[DEBUG] Screen preview capture started")
            
            while self.running:
                try:
                    # Capture screen using the same method as ScreenCaptureClient
                    screenshot = self.capture_screen_for_preview()
                    if screenshot is not None:
                        self.preview_frame_ready.emit(screenshot)
                    
                    self.msleep(500)  # 2 FPS for preview (less frequent than actual sharing)
                    
                except Exception as e:
                    print(f"[ERROR] Preview capture error: {e}")
                    break
                    
        except Exception as e:
            print(f"[ERROR] Preview capture thread error: {e}")
        finally:
            self.running = False
            print("[DEBUG] Screen preview capture stopped")
    
    def capture_screen_for_preview(self):
        """Capture the screen and return as numpy array for preview."""
        try:
            if not HAS_OPENCV:
                return None
            
            # Use different methods based on platform
            if sys.platform == "darwin":  # macOS
                # Use screencapture command
                import subprocess
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    subprocess.run(['screencapture', '-x', tmp.name], check=True)
                    screenshot = cv2.imread(tmp.name)
                    os.unlink(tmp.name)
            else:
                # For other platforms, try using PIL if available
                try:
                    from PIL import ImageGrab
                    import numpy as np
                    pil_image = ImageGrab.grab()
                    screenshot = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                except ImportError:
                    print("[ERROR] Screen capture requires PIL/Pillow: pip install Pillow")
                    return None
                except Exception as e:
                    print(f"[ERROR] Screen capture failed: {e}")
                    return None
            
            if screenshot is not None:
                # Resize for preview (smaller than actual sharing)
                height, width = screenshot.shape[:2]
                new_width = min(640, width)  # Smaller for preview
                new_height = int(height * (new_width / width))
                screenshot = cv2.resize(screenshot, (new_width, new_height))
                return screenshot
            
        except Exception as e:
            print(f"[ERROR] Preview screen capture failed: {e}")
        
        return None
    
    def stop(self):
        """Stop preview capture."""
        self.running = False


class ScreenShareViewer(QMainWindow):
    """Dedicated window for viewing screen shares."""
    
    def __init__(self, server_host: str, server_port: int, presenter_name: str, parent=None):
        super().__init__(parent)
        self.server_host = server_host
        self.server_port = server_port
        self.presenter_name = presenter_name
        self.receiver_thread = None
        
        self.setup_ui()
        self.start_receiving()
    
    def setup_ui(self):
        """Setup the screen share viewer UI."""
        self.setWindowTitle(f"Screen Share - {self.presenter_name}")
        self.setMinimumSize(800, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Header
        header = QLabel(f"🖥️ {self.presenter_name} is sharing their screen")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px; background-color: #0078d4; color: white;")
        layout.addWidget(header)
        
        # Screen display area
        self.screen_display = QLabel()
        self.screen_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.screen_display.setStyleSheet("background-color: black; border: 1px solid #ccc;")
        self.screen_display.setText("Connecting to screen share...")
        layout.addWidget(self.screen_display)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        fullscreen_btn = QPushButton("🔍 Fullscreen")
        fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        button_layout.addWidget(fullscreen_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("❌ Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def start_receiving(self):
        """Start receiving screen share data."""
        self.receiver_thread = ScreenShareReceiver(self.server_host, self.server_port, self)
        self.receiver_thread.frame_received.connect(self.update_screen)
        self.receiver_thread.connection_error.connect(self.handle_connection_error)
        self.receiver_thread.start()
    
    def update_screen(self, frame_data: bytes):
        """Update the screen display with new frame."""
        try:
            # Decode frame
            frame_array = np.frombuffer(frame_data, dtype=np.uint8)
            frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
            
            if frame is not None:
                # Convert to Qt format
                height, width, channel = frame.shape
                bytes_per_line = 3 * width
                q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()
                
                # Scale to fit display
                pixmap = QPixmap.fromImage(q_image)
                scaled_pixmap = pixmap.scaled(
                    self.screen_display.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                self.screen_display.setPixmap(scaled_pixmap)
                
        except Exception as e:
            print(f"[ERROR] Screen display error: {e}")
    
    def handle_connection_error(self, error: str):
        """Handle connection errors."""
        self.screen_display.setText(f"Connection error: {error}")
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
    
    def closeEvent(self, event):
        """Handle window close event."""
        if self.receiver_thread:
            self.receiver_thread.stop()
            self.receiver_thread.wait()
        event.accept()


class ScreenShareReceiver(QThread):
    """Receives screen share data from server."""
    
    frame_received = pyqtSignal(bytes)
    connection_error = pyqtSignal(str)
    
    def __init__(self, server_host: str, server_port: int, parent=None):
        super().__init__(parent)
        self.server_host = server_host
        self.server_port = server_port
        self.running = False
        self.socket = None
    
    def run(self):
        """Run screen share receiver loop."""
        try:
            self.running = True
            
            # Connect to screen share server
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            
            # Send viewer type
            self.socket.send(struct.pack('!I', 2))  # 2 = viewer
            
            # Wait for OK response
            response = self.socket.recv(1024)
            if response != b'OK':
                self.connection_error.emit(f"Server rejected connection: {response}")
                return
            
            print("[INFO] Connected to screen share as viewer")
            
            while self.running:
                try:
                    # Read frame size
                    size_data = self.socket.recv(4)
                    if not size_data:
                        break
                    
                    frame_size = struct.unpack('!I', size_data)[0]
                    
                    # Read frame data
                    frame_data = b''
                    while len(frame_data) < frame_size:
                        chunk = self.socket.recv(min(8192, frame_size - len(frame_data)))
                        if not chunk:
                            break
                        frame_data += chunk
                    
                    if len(frame_data) == frame_size:
                        self.frame_received.emit(frame_data)
                    
                except Exception as e:
                    if self.running:
                        print(f"[ERROR] Screen receiver error: {e}")
                        self.connection_error.emit(str(e))
                    break
                    
        except Exception as e:
            self.connection_error.emit(str(e))
        finally:
            if self.socket:
                self.socket.close()
            self.running = False
    
    def stop(self):
        """Stop screen share receiver."""
        self.running = False


# ============================================================================
# MAIN CLIENT WINDOW
# ============================================================================

class ClientMainWindow(QMainWindow):
    """Main client window with comprehensive GUI."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LAN Collaboration Client")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        
        # Connection info
        self.host = None
        self.port = None
        self.username = None
        self.uid = None
        
        # Network components
        self.network_thread = None
        self.video_client = None
        self.audio_client = None
        
        # State
        self.connected = False
        self.participants = {}
        self.pending_upload = None  # File path waiting for upload port
        
        # Setup UI
        self.setup_ui()
        self.setup_menu_bar()
        self.setup_status_bar()
        
        # Apply black background theme
        print("[INFO] Applying black background theme")
        self.apply_dark_theme()
        
        # Show connection dialog
        self.show_connection_dialog()
    
    def setup_ui(self):
        """Setup tabbed UI with separate sections for each functionality."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout - horizontal split
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)
        
        # Left sidebar for navigation tabs
        sidebar = QFrame()
        sidebar.setFrameStyle(QFrame.Shape.StyledPanel)
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #000000;
                border-radius: 10px;
                border: 1px solid #333333;
            }
        """)
        
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setSpacing(5)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        
        # App title - will be updated with username when connected
        self.title_label = QLabel("🎥 LAN Meeting")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #0078d4;
                padding: 15px;
                background-color: #000000;
                border-radius: 12px;
                margin-bottom: 15px;
                border: 2px solid #0078d4;
            }
        """)
        sidebar_layout.addWidget(self.title_label)
        
        # Navigation buttons
        self.nav_buttons = {}
        nav_button_style = """
            QPushButton {
                background-color: #333333;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                text-align: left;
                font-size: 14px;
                margin: 2px;
            }
            QPushButton:hover {
                background-color: #444444;
            }
            QPushButton:checked {
                background-color: #0078d4;
                font-weight: bold;
            }
        """
        
        # Create navigation buttons for each functionality
        nav_buttons_data = [
            ("video_meet", "📹 Video Meeting", "video_meet_tab"),
            ("screen_share", "🖥️ Screen Share", "screen_share_tab"),
            ("chat", "💬 Chat", "chat_tab"),
            ("file_transfer", "📁 File Transfer", "file_transfer_tab"),
            ("participants", "👥 Participants", "participants_tab")
        ]
        
        for button_id, button_text, tab_name in nav_buttons_data:
            btn = QPushButton(button_text)
            btn.setCheckable(True)
            btn.setStyleSheet(nav_button_style)
            btn.clicked.connect(lambda checked, tab=tab_name: self.switch_to_tab(tab))
            self.nav_buttons[button_id] = btn
            sidebar_layout.addWidget(btn)
        
        # Set first button as active
        self.nav_buttons["video_meet"].setChecked(True)
        
        # Spacer to push disconnect button to bottom
        sidebar_layout.addStretch()
        
        # Disconnect button at bottom
        disconnect_btn = QPushButton("🚪 Leave Meeting")
        disconnect_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        disconnect_btn.clicked.connect(lambda: self.handle_leave_button_click())
        sidebar_layout.addWidget(disconnect_btn)
        
        main_layout.addWidget(sidebar)
        
        # Right side - Stacked widget for different tabs
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("""
            QStackedWidget {
                background-color: #000000;
                border-radius: 10px;
                border: 1px solid #333333;
            }
        """)
        
        # Create all tab content
        self.create_video_meeting_tab()
        self.create_screen_share_tab()
        self.create_chat_tab()
        self.create_file_transfer_tab()
        self.create_participants_tab()
        
        main_layout.addWidget(self.content_stack, 1)  # Takes remaining space

    def update_title_with_username(self):
        """Update the title label to show the connected username"""
        if self.username:
            self.title_label.setText(f"🎥 {self.username}")
            # Also update the window title
            self.setWindowTitle(f"LAN Meeting - {self.username}")
        else:
            self.title_label.setText("🎥 LAN Meeting")
            self.setWindowTitle("LAN Meeting System")

    def create_video_meeting_tab(self):
        """Create video meeting tab content - SAFE UI modification"""
        video_tab = QWidget()
        layout = QVBoxLayout(video_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header
        header = QLabel("📹 Video Meeting")
        header.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #0078d4;
                padding: 10px;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(header)
        
        # Video grid (reuse existing component)
        self.video_grid = VideoGrid()
        layout.addWidget(self.video_grid)
        
        # Media controls (reuse existing component)
        self.media_controls = MediaControlsWidget()
        # Keep all existing connections - IMPORTANT for functionality
        self.media_controls.video_toggle_requested.connect(self.toggle_video)
        self.media_controls.audio_toggle_requested.connect(self.toggle_audio)
        self.media_controls.screen_share_requested.connect(self.toggle_screen_share)
        layout.addWidget(self.media_controls)
        
        self.content_stack.addWidget(video_tab)
        self.video_meet_tab = video_tab

    def create_screen_share_tab(self):
        """Create screen share tab content - SAFE UI modification"""
        screen_tab = QWidget()
        layout = QVBoxLayout(screen_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header - Reduced size
        header = QLabel("🖥️ Screen Sharing")
        header.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #0078d4;
                padding: 5px;
                margin-bottom: 5px;
            }
        """)
        layout.addWidget(header)
        
        # Preview section
        preview_frame = QFrame()
        preview_frame.setStyleSheet("""
            QFrame {
                background-color: #000000;
                border: 2px dashed #3d3d3d;
                border-radius: 8px;
                min-height: 200px;
            }
        """)
        preview_layout = QVBoxLayout(preview_frame)
        
        # Store reference to preview label for updating
        self.screen_preview_label = QLabel("Screen sharing preview will appear here when you start sharing")
        self.screen_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.screen_preview_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                color: #888888;
                font-size: 16px;
                padding: 50px;
            }
        """)
        self.screen_preview_label.setScaledContents(True)  # Allow scaling of images
        preview_layout.addWidget(self.screen_preview_label)
        layout.addWidget(preview_frame)
        
        # Screen share controls - Below preview
        controls_frame = QFrame()
        controls_frame.setStyleSheet("""
            QFrame {
                background-color: #000000;
                border-radius: 8px;
                padding: 10px;
                margin-top: 10px;
            }
        """)
        controls_layout = QHBoxLayout(controls_frame)
        
        # Start screen share button
        self.start_share_btn = QPushButton("🖥️ Start Sharing")
        self.start_share_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 25px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.start_share_btn.clicked.connect(lambda: self.toggle_screen_share(True))  # Fixed: pass True to start sharing
        controls_layout.addWidget(self.start_share_btn)
        
        # Stop screen share button
        self.stop_share_btn = QPushButton("⏹️ Stop Sharing")
        self.stop_share_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 25px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        self.stop_share_btn.clicked.connect(lambda: self.toggle_screen_share(False))  # Fixed: pass False to stop sharing
        self.stop_share_btn.setEnabled(False)  # Initially disabled until sharing starts
        controls_layout.addWidget(self.stop_share_btn)
        
        controls_layout.addStretch()
        layout.addWidget(controls_frame)
        
        # Status area - Keep at reasonable size
        self.screen_share_status = QLabel("📱 Ready to share screen")
        self.screen_share_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.screen_share_status.setStyleSheet("""
            QLabel {
                background-color: #333333;
                color: #ffffff;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
                font-weight: bold;
                margin: 8px 0;
            }
        """)
        layout.addWidget(self.screen_share_status)
        
        # Instructions area - Keep as is
        instructions = QLabel("""
        📋 <b>Screen Sharing Instructions:</b><br><br>
        1. Click <b>"🖥️ Start Sharing"</b> to begin sharing your screen<br>
        2. Other participants will see your screen in real-time<br>
        3. Click <b>"⏹️ Stop Sharing"</b> when finished<br><br>
        💡 <i>Note: Screen sharing works with the same functionality as the Video Meeting tab</i>
        """)
        instructions.setAlignment(Qt.AlignmentFlag.AlignLeft)
        instructions.setWordWrap(True)
        instructions.setStyleSheet("""
            QLabel {
                background-color: #111111;
                color: #ffffff;
                border: 1px solid #333333;
                border-radius: 8px;
                padding: 20px;
                font-size: 14px;
                line-height: 1.5;
            }
        """)
        layout.addWidget(instructions)
        
        self.content_stack.addWidget(screen_tab)
        self.screen_share_tab = screen_tab

    def create_chat_tab(self):
        """Create chat tab content - SAFE UI modification"""
        chat_tab = QWidget()
        layout = QVBoxLayout(chat_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header
        header = QLabel("💬 Group Chat")
        header.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #0078d4;
                padding: 10px;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(header)
        
        # Chat widget (reuse existing component)
        self.chat_widget = ChatWidget()
        # Keep all existing connections - IMPORTANT for functionality
        self.chat_widget.message_sent.connect(self.send_chat_message)
        self.chat_widget.file_share_requested.connect(self.upload_file)
        self.chat_widget.file_list_requested.connect(self.request_file_list)
        self.chat_widget.file_download_requested.connect(self.download_file)
        layout.addWidget(self.chat_widget)
        
        self.content_stack.addWidget(chat_tab)
        self.chat_tab = chat_tab

    def create_file_transfer_tab(self):
        """Create file transfer tab content - SAFE UI modification"""
        file_tab = QWidget()
        layout = QVBoxLayout(file_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header
        header = QLabel("📁 File Transfer")
        header.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #0078d4;
                padding: 10px;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(header)
        
        # Upload section
        upload_frame = QFrame()
        upload_frame.setStyleSheet("""
            QFrame {
                background-color: #000000;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 10px;
            }
        """)
        upload_layout = QVBoxLayout(upload_frame)
        
        upload_label = QLabel("📤 Upload Files")
        upload_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white; margin-bottom: 10px;")
        upload_layout.addWidget(upload_label)
        
        upload_btn = QPushButton("📎 Select File to Upload")
        upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        upload_btn.clicked.connect(lambda: self.upload_file())  # Use lambda to avoid passing boolean parameter
        upload_layout.addWidget(upload_btn)
        
        layout.addWidget(upload_frame)
        
        # Download section
        download_frame = QFrame()
        download_frame.setStyleSheet("""
            QFrame {
                background-color: #000000;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        download_layout = QVBoxLayout(download_frame)
        
        download_label = QLabel("📥 Available Files")
        download_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white; margin-bottom: 10px;")
        download_layout.addWidget(download_label)
        
        # File list area
        self.file_list_area = QTextBrowser()
        self.file_list_area.setStyleSheet("""
            QTextBrowser {
                background-color: #000000;
                color: white;
                border: 1px solid #333333;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        self.file_list_area.setText("Click 'Refresh File List' to see available files")
        download_layout.addWidget(self.file_list_area)
        
        refresh_btn = QPushButton("🔄 Refresh File List")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #6f42c1;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a32a3;
            }
        """)
        refresh_btn.clicked.connect(self.request_file_list)  # Keep existing functionality
        download_layout.addWidget(refresh_btn)
        
        layout.addWidget(download_frame)
        
        self.content_stack.addWidget(file_tab)
        self.file_transfer_tab = file_tab

    def create_participants_tab(self):
        """Create participants tab content - SAFE UI modification"""
        participants_tab = QWidget()
        layout = QVBoxLayout(participants_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header
        header = QLabel("👥 Participants")
        header.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #0078d4;
                padding: 10px;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(header)
        
        # Participants widget (reuse existing component)
        self.participants_widget = ParticipantsWidget()
        # Keep existing connections - IMPORTANT for functionality
        self.participants_widget.private_message_requested.connect(self.send_private_message)
        layout.addWidget(self.participants_widget)
        
        self.content_stack.addWidget(participants_tab)
        self.participants_tab = participants_tab

    def update_file_list_display(self, files):
        """Update the file list display in the file transfer tab"""
        if not hasattr(self, 'file_list_area'):
            return
            
        if not files:
            self.file_list_area.setText("No files are currently available for download.")
            return
            
        # Format file list for display
        file_list_html = "<h3>📁 Available Files:</h3><br>"
        for file_info in files:
            filename = file_info.get('filename', 'Unknown')
            size = file_info.get('size', 0)
            uploader = file_info.get('uploader', 'Unknown')
            
            # Format file size
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            
            file_list_html += f"""
            <div style='background-color: #111111; padding: 10px; margin: 5px; border-radius: 5px;'>
                <b>📄 {filename}</b><br>
                <small>Size: {size_str} | Uploaded by: {uploader}</small>
            </div>
            """
        
        file_list_html += "<br><i>Use the dialog or chat interface to download files.</i>"
        self.file_list_area.setHtml(file_list_html)

    def switch_to_tab(self, tab_name):
        """Switch between tabs - SAFE UI method"""
        # Update button states
        for btn in self.nav_buttons.values():
            btn.setChecked(False)
        
        # Set active tab and button
        if tab_name == "video_meet_tab":
            self.content_stack.setCurrentWidget(self.video_meet_tab)
            self.nav_buttons["video_meet"].setChecked(True)
        elif tab_name == "screen_share_tab":
            self.content_stack.setCurrentWidget(self.screen_share_tab)
            self.nav_buttons["screen_share"].setChecked(True)
        elif tab_name == "chat_tab":
            self.content_stack.setCurrentWidget(self.chat_tab)
            self.nav_buttons["chat"].setChecked(True)
        elif tab_name == "file_transfer_tab":
            self.content_stack.setCurrentWidget(self.file_transfer_tab)
            self.nav_buttons["file_transfer"].setChecked(True)
        elif tab_name == "participants_tab":
            self.content_stack.setCurrentWidget(self.participants_tab)
            self.nav_buttons["participants"].setChecked(True)
    
    def setup_menu_bar(self):
        """Setup menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        connect_action = QAction("Connect...", self)
        connect_action.triggered.connect(self.show_connection_dialog)
        file_menu.addAction(connect_action)
        
        disconnect_action = QAction("Disconnect", self)
        disconnect_action.triggered.connect(self.disconnect_from_server)
        file_menu.addAction(disconnect_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
    
    def setup_status_bar(self):
        """Setup status bar."""
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")
        
        # Connection status
        self.connection_status = QLabel("⚫ Disconnected")
        self.connection_status.setStyleSheet("color: #dc3545; font-weight: bold;")
        self.status_bar.addPermanentWidget(self.connection_status)
    
    def setup_application_style(self):
        """Setup application-wide styling and compatibility."""
        # Set application properties for better rendering
        app = QApplication.instance()
        if app:
            # Enable high DPI scaling (Qt6 handles this automatically)
            try:
                # These attributes were deprecated in Qt6 but may still be available in some versions
                if hasattr(Qt.ApplicationAttribute, 'AA_EnableHighDpiScaling'):
                    app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
                if hasattr(Qt.ApplicationAttribute, 'AA_UseHighDpiPixmaps'):
                    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
            except AttributeError:
                # Qt6 handles high DPI automatically, so this is not needed
                pass
            
            # Set application style
            available_styles = app.style().objectName()
            print(f"[INFO] Available Qt style: {available_styles}")
            
            # Try to set a consistent style
            try:
                if sys.platform == "darwin":  # macOS
                    app.setStyle("macOS")
                elif sys.platform == "win32":  # Windows
                    app.setStyle("windowsvista")
                else:  # Linux
                    app.setStyle("fusion")
            except:
                print("[INFO] Using default system style")
        
        # Set font for better consistency
        font = QFont()
        font.setFamily("Segoe UI" if sys.platform == "win32" else "Arial")
        font.setPointSize(10)
        try:
            font.setWeight(QFont.Weight.Normal)
        except AttributeError:
            # Fallback for older PyQt6 versions
            font.setWeight(50)  # Normal weight
        self.setFont(font)
    
    def disable_all_styling(self):
        """Completely disable all custom styling."""
        # Override all setStyleSheet methods to do nothing
        def no_style(style_string):
            pass
        
        # Disable styling on this window
        self.setStyleSheet("")
        
        # Find and disable styling on all child widgets
        for widget in self.findChildren(QWidget):
            widget.setStyleSheet("")
    
    def apply_minimal_theme(self):
        """Apply minimal safe theme that definitely works."""
        # Use the same approach as the working minimal_client
        minimal_style = """
        QMainWindow {
            background-color: #2d2d2d;
            color: white;
        }
        QPushButton {
            background-color: #0078d4;
            color: white;
            border: none;
            padding: 8px 16px;
        }
        QPushButton:hover {
            background-color: #106ebe;
        }
        QLineEdit {
            background-color: white;
            color: black;
            border: 1px solid #ccc;
            padding: 4px;
        }
        QTextBrowser, QTextEdit {
            background-color: white;
            color: black;
            border: 1px solid #ccc;
        }
        QLabel {
            color: white;
        }
        QTabWidget::pane {
            border: 1px solid #ccc;
        }
        QTabBar::tab {
            background-color: #f0f0f0;
            padding: 8px;
        }
        QTabBar::tab:selected {
            background-color: white;
        }
        """
        self.setStyleSheet(minimal_style)
    
    def apply_dark_theme(self):
        """Apply comprehensive dark theme to the application."""
        try:
            # Set application-wide style
            app_style = """
        /* Main Application */
        QMainWindow {
            background-color: #000000;
            color: #ffffff;
            font-family: 'Segoe UI', 'Arial', sans-serif;
            font-size: 12px;
        }
        
        /* Menu Bar */
        QMenuBar {
            background-color: #000000;
            color: #ffffff;
            border-bottom: 1px solid #333333;
            padding: 2px;
        }
        QMenuBar::item {
            background-color: transparent;
            padding: 6px 12px;
            border-radius: 4px;
            margin: 2px;
        }
        QMenuBar::item:selected {
            background-color: #0078d4;
        }
        QMenuBar::item:pressed {
            background-color: #106ebe;
        }
        
        /* Menu */
        QMenu {
            background-color: #000000;
            color: #ffffff;
            border: 1px solid #333333;
            border-radius: 6px;
            padding: 4px;
        }
        QMenu::item {
            padding: 8px 16px;
            border-radius: 4px;
            margin: 1px;
        }
        QMenu::item:selected {
            background-color: #0078d4;
        }
        QMenu::separator {
            height: 1px;
            background-color: #333333;
            margin: 4px 8px;
        }
        
        /* Status Bar */
        QStatusBar {
            background-color: #000000;
            color: #ffffff;
            border-top: 1px solid #333333;
            padding: 4px;
        }
        
        /* Buttons */
        QPushButton {
            background-color: #0078d4;
            color: #ffffff;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: 500;
            min-height: 20px;
        }
        QPushButton:hover {
            background-color: #106ebe;
        }
        QPushButton:pressed {
            background-color: #005a9e;
        }
        QPushButton:disabled {
            background-color: #333333;
            color: #888888;
        }
        
        /* Input Fields */
        QLineEdit {
            background-color: #000000;
            color: #ffffff;
            border: 2px solid #333333;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 12px;
            selection-background-color: #0078d4;
        }
        QLineEdit:focus {
            border-color: #0078d4;
            background-color: #111111;
        }
        QLineEdit:disabled {
            background-color: #000000;
            color: #666666;
        }
        
        /* Text Areas */
        QTextEdit, QTextBrowser {
            background-color: #000000;
            color: #ffffff;
            border: 2px solid #333333;
            border-radius: 6px;
            padding: 8px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 11px;
            line-height: 1.4;
        }
        QTextEdit:focus, QTextBrowser:focus {
            border-color: #0078d4;
        }
        
        /* Lists */
        QListWidget {
            background-color: #000000;
            color: #ffffff;
            border: 2px solid #333333;
            border-radius: 6px;
            padding: 4px;
            outline: none;
        }
        QListWidget::item {
            padding: 8px 12px;
            border-radius: 4px;
            margin: 1px;
        }
        QListWidget::item:selected {
            background-color: #0078d4;
        }
        QListWidget::item:hover {
            background-color: #333333;
        }
        
        /* Tables */
        QTableWidget {
            background-color: #000000;
            color: #ffffff;
            border: 2px solid #333333;
            border-radius: 6px;
            gridline-color: #333333;
            outline: none;
        }
        QTableWidget::item {
            padding: 8px;
            border-bottom: 1px solid #333333;
        }
        QTableWidget::item:selected {
            background-color: #0078d4;
        }
        QHeaderView::section {
            background-color: #333333;
            color: #ffffff;
            padding: 8px 12px;
            border: none;
            font-weight: 600;
        }
        
        /* Tabs */
        QTabWidget::pane {
            border: 2px solid #333333;
            border-radius: 6px;
            background-color: #000000;
        }
        QTabBar::tab {
            background-color: #333333;
            color: #ffffff;
            padding: 8px 16px;
            margin: 2px;
            border-radius: 6px 6px 0px 0px;
            min-width: 80px;
        }
        QTabBar::tab:selected {
            background-color: #0078d4;
        }
        QTabBar::tab:hover {
            background-color: #444444;
        }
        
        /* Frames */
        QFrame {
            background-color: #000000;
            border: 1px solid #333333;
            border-radius: 6px;
        }
        
        /* Group Boxes */
        QGroupBox {
            color: #ffffff;
            font-weight: 600;
            border: 2px solid #333333;
            border-radius: 6px;
            margin-top: 12px;
            padding-top: 8px;
        }
        
        /* Check Boxes */
        QCheckBox {
            color: #ffffff;
            spacing: 8px;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border: 2px solid #3d3d3d;
            border-radius: 3px;
            background-color: #2d2d2d;
        }
        QCheckBox::indicator:checked {
            background-color: #0078d4;
            border-color: #0078d4;
        }
        
        /* Combo Boxes */
        QComboBox {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 2px solid #3d3d3d;
            border-radius: 6px;
            padding: 6px 12px;
            min-width: 100px;
        }
        QComboBox:focus {
            border-color: #0078d4;
        }
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        
        /* Progress Bars */
        QProgressBar {
            background-color: #3d3d3d;
            border: none;
            border-radius: 6px;
            text-align: center;
            color: #ffffff;
            font-weight: 600;
        }
        QProgressBar::chunk {
            background-color: #0078d4;
            border-radius: 6px;
        }
        
        /* Sliders */
        QSlider::groove:horizontal {
            background-color: #3d3d3d;
            height: 6px;
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background-color: #0078d4;
            width: 16px;
            height: 16px;
            border-radius: 8px;
            margin: -5px 0;
        }
        QSlider::handle:horizontal:hover {
            background-color: #106ebe;
        }
        
        /* Scroll Bars */
        QScrollBar:vertical {
            background-color: #2d2d2d;
            width: 12px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background-color: #5d5d5d;
            border-radius: 6px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #6d6d6d;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        
        /* Tool Tips */
        QToolTip {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #3d3d3d;
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 11px;
        }
        
        /* Labels */
        QLabel {
            color: #ffffff;
        }
        
        /* Dialogs */
        QDialog {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        """
        
            self.setStyleSheet(app_style)
            
        except Exception as e:
            print(f"[WARNING] Could not apply full theme: {e}")
            print("[INFO] Falling back to minimal theme")
            self.apply_minimal_theme()
            return
        
        # Also set application-wide palette for better compatibility
        try:
            palette = QPalette()
            palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
            palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
            palette.setColor(QPalette.ColorRole.Base, QColor(45, 45, 45))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(60, 60, 60))
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(45, 45, 45))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
            palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
            palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
            palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
            palette.setColor(QPalette.ColorRole.Link, QColor(0, 120, 212))
            palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 212))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
            
            self.setPalette(palette)
        except Exception as e:
            print(f"[WARNING] Could not set custom palette: {e}")
            # Fallback to basic styling only
    
    def show_connection_dialog(self):
        """Show ultra-simple connection dialog."""
        from simple_connection import SimpleConnectionDialog
        dialog = SimpleConnectionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            conn_info = dialog.get_connection_info()
            self.connect_to_server(conn_info)
    
    def connect_to_server(self, conn_info: dict):
        """Connect to server."""
        self.host = conn_info['host']
        self.port = conn_info['port']
        self.username = conn_info['username']
        
        # Validate connection info
        if not self.host or not self.port or not self.username:
            QMessageBox.warning(self, "Invalid Input", "Please provide valid server details and username.")
            return
        
        # Test basic connectivity first
        try:
            print(f"[INFO] Testing connection to {self.host}:{self.port}")
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.settimeout(5)
            result = test_sock.connect_ex((self.host, self.port))
            test_sock.close()
            
            if result != 0:
                QMessageBox.critical(
                    self, 
                    "Connection Failed", 
                    f"Cannot reach server at {self.host}:{self.port}\n\n"
                    f"Please check:\n"
                    f"• Server is running (python main_server.py)\n"
                    f"• IP address is correct\n"
                    f"• Firewall allows ports 9000, 10000, 11000\n"
                    f"• You're on the same network\n\n"
                    f"💡 Try running: python connection_test.py {self.host}"
                )
                return
                
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Network Error", 
                f"Network error: {e}\n\n"
                f"Please check your network connection."
            )
            return
        
        print(f"[INFO] Basic connectivity test passed")
        
        # Update window title
        self.setWindowTitle(f"LAN Collaboration Client - {self.username}")
        
        # Start network thread
        self.network_thread = NetworkThread(self.host, self.port, self.username, self)
        self.network_thread.message_received.connect(self.handle_message)
        self.network_thread.connection_status_changed.connect(self.on_connection_status_changed)
        self.network_thread.start()
        
        # Initialize media clients (but don't start them yet)
        self.video_client = VideoClient(self.host, DEFAULT_UDP_VIDEO_PORT, self)
        self.video_client.frame_captured.connect(self.video_grid.update_local_video)
        self.video_client.frame_received.connect(self.video_grid.update_participant_video)
        self.video_client.video_disabled.connect(self.clear_local_video)
        
        self.audio_client = AudioClient(self.host, DEFAULT_UDP_AUDIO_PORT, self)
        
        # Media clients will be started after successful login
        
        # Set initial media states
        if conn_info['join_with_video']:
            self.toggle_video(True)
        if conn_info['join_with_audio']:
            self.toggle_audio(True)
    
    def disconnect_from_server(self):
        """Disconnect from server."""
        print("[DEBUG] Leave button clicked - starting disconnect process")
        
        # Mark this as an intentional disconnect
        self._intentional_disconnect = True
        
        if self.network_thread and self.connected:
            # Send logout message to server before disconnecting
            print("[DEBUG] Sending LOGOUT message to server")
            logout_message = {
                'type': MessageTypes.LOGOUT,
                'timestamp': datetime.now().isoformat()
            }
            self.network_thread.send_message_sync(logout_message)
            
            # Give server time to process logout and notify other clients
            import time
            time.sleep(0.5)
        
        if self.network_thread:
            self.network_thread.disconnect()
            self.network_thread.wait()
            self.network_thread = None
        
        if self.video_client:
            self.video_client.stop()
            self.video_client.wait()
            self.video_client = None
        
        if self.audio_client:
            self.audio_client.stop()
            self.audio_client.wait()
            self.audio_client = None
        
        # Stop screen sharing
        if hasattr(self, 'screen_capture_client') and self.screen_capture_client:
            self.screen_capture_client.stop()
            self.screen_capture_client = None
        
        if hasattr(self, 'screen_viewer') and self.screen_viewer:
            self.screen_viewer.close()
            self.screen_viewer = None
        
        self.connected = False
        self.uid = None
        self.participants.clear()
        
        # Update UI
        self.participants_widget.update_participants({})
        self.chat_widget.clear_chat()
        
        # Reset titles
        self.username = None
        self.update_title_with_username()
        
        print("[DEBUG] Disconnect process completed - client fully disconnected")
        
        # Show connection dialog again or close application
        self.show_reconnect_options()
        
        # Clear the intentional disconnect flag
        if hasattr(self, '_intentional_disconnect'):
            delattr(self, '_intentional_disconnect')
    
    def handle_leave_button_click(self):
        """Handle leave button click with debug output."""
        print("[DEBUG] 🚪 Leave button clicked!")
        self.disconnect_from_server()
    
    def show_reconnect_options(self):
        """Show options to reconnect or exit after disconnection."""
        # Check if this was an intentional disconnect
        if hasattr(self, '_intentional_disconnect'):
            title = "Left Meeting"
            message = "You have left the meeting.\n\nWhat would you like to do?"
        else:
            title = "Connection Lost"
            message = "Connection to the server was lost.\n\nWhat would you like to do?"
        
        # Create custom message box with better button labels
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Icon.Question)
        
        reconnect_btn = msg_box.addButton("🔄 Connect Again", QMessageBox.ButtonRole.AcceptRole)
        exit_btn = msg_box.addButton("❌ Exit", QMessageBox.ButtonRole.RejectRole)
        msg_box.setDefaultButton(reconnect_btn)
        
        msg_box.exec()
        
        if msg_box.clickedButton() == reconnect_btn:
            # Show connection dialog to reconnect
            self.show_connection_dialog()
        else:
            # Close the application
            self.close()
    
    def on_connection_status_changed(self, connected: bool, message: str):
        """Handle connection status change."""
        was_connected = self.connected
        self.connected = connected
        
        if connected:
            self.connection_status.setText("🟢 Connected")
            self.connection_status.setStyleSheet("color: #28a745; font-weight: bold;")
            self.status_bar.showMessage(f"Connected to {self.host}:{self.port}")
        else:
            self.connection_status.setText("⚫ Disconnected")
            self.connection_status.setStyleSheet("color: #dc3545; font-weight: bold;")
            self.status_bar.showMessage(message)
            
            # If we were connected and now disconnected unexpectedly (not via Leave button)
            if was_connected and not hasattr(self, '_intentional_disconnect'):
                print("[DEBUG] Unexpected disconnection detected")
                # Clean up UI state
                self.participants.clear()
                self.participants_widget.update_participants({})
                self.chat_widget.clear_chat()
                # Show reconnect options after a short delay
                QTimer.singleShot(1000, self.show_reconnect_options)
    
    def handle_message(self, message: dict):
        """Handle incoming message from server."""
        msg_type = message.get('type', '')
        
        if msg_type == MessageTypes.LOGIN_SUCCESS:
            self.uid = message.get('uid')
            username = message.get('username')
            
            # Set UID for media clients and start them
            if self.video_client:
                self.video_client.set_uid(self.uid)
                if not self.video_client.isRunning():
                    self.video_client.start()
                    print(f"[DEBUG] Started video client with UID {self.uid}")
            
            if self.audio_client:
                self.audio_client.set_uid(self.uid)
                if not self.audio_client.isRunning():
                    self.audio_client.start()
                    print(f"[DEBUG] Started audio client with UID {self.uid}")
            
            self.chat_widget.add_message("System", f"Welcome {username}! You are now connected.", is_system=True)
            
            # Update title with username
            self.update_title_with_username()
            
            # Request participant list after login
            if self.network_thread:
                participant_request = {
                    'type': MessageTypes.GET_PARTICIPANTS,
                    'timestamp': datetime.now().isoformat()
                }
                self.network_thread.send_message_sync(participant_request)
            
        elif msg_type == MessageTypes.PARTICIPANT_LIST:
            participants = message.get('participants', [])
            self.participants = {p['uid']: p for p in participants}
            self.participants_widget.update_participants(self.participants)
            
            # Add video frames for participants (exclude self)
            for participant in participants:
                if participant['uid'] != self.uid:
                    self.video_grid.add_participant_frame(participant['uid'], participant['username'])
            
        elif msg_type == MessageTypes.USER_JOINED:
            uid = message.get('uid')
            username = message.get('username')
            
            if uid != self.uid:
                self.participants[uid] = {'uid': uid, 'username': username}
                self.participants_widget.add_participant(uid, username)
                self.video_grid.add_participant_frame(uid, username)
                self.chat_widget.add_message("System", f"{username} joined the session", is_system=True)
            
        elif msg_type == MessageTypes.USER_LEFT:
            uid = message.get('uid')
            username = message.get('username')
            
            if uid in self.participants:
                del self.participants[uid]
                self.participants_widget.remove_participant(uid)
                self.video_grid.remove_participant_frame(uid)
                self.chat_widget.add_message("System", f"{username} left the session", is_system=True)
            
        elif msg_type == MessageTypes.CHAT:
            sender = message.get('username', 'Unknown')
            text = message.get('content', '')
            timestamp = message.get('timestamp', '')
            
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime("%H:%M:%S")
                except:
                    time_str = None
            else:
                time_str = None
            
            self.chat_widget.add_message(sender, text, time_str)
        
        elif msg_type == MessageTypes.UNICAST:
            # Private message received
            sender = message.get('username', 'Unknown')
            text = message.get('content', '')
            timestamp = message.get('timestamp', '')
            
            print(f"[DEBUG] Received private message from {sender}: {text}")
            
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime("%H:%M:%S")
                except:
                    time_str = None
            else:
                time_str = None
            
            # Display private message with special formatting
            self.chat_widget.add_private_message(sender, text, time_str)
            
        elif msg_type == MessageTypes.FILE_UPLOAD_PORT:
            # Server provided upload port
            upload_port = message.get('port')
            if self.pending_upload and upload_port:
                self.start_file_upload(self.pending_upload, upload_port)
                self.pending_upload = None
            
        elif msg_type == MessageTypes.FILE_DOWNLOAD_PORT:
            # Server provided download port and file list
            download_port = message.get('port')
            files = message.get('files', [])
            if files:
                # Update the file transfer tab display
                self.update_file_list_display(files)
                # Also show the traditional dialog for backward compatibility
                self.chat_widget.show_file_download_dialog(files)
            else:
                if hasattr(self, 'file_list_area'):
                    self.file_list_area.setText("No files are currently available for download.")
                QMessageBox.information(self, "No Files", "No files are currently available for download.")
            
        elif msg_type == MessageTypes.FILE_AVAILABLE:
            # New file available notification
            filename = message.get('filename', 'Unknown')
            uploader = message.get('uploader', 'Unknown')
            self.chat_widget.add_message("System", f"📁 New file available: {filename} (uploaded by {uploader})", is_system=True)
            
        elif msg_type == MessageTypes.UNICAST_SENT:
            # Private message sent confirmation
            target_uid = message.get('target_uid')
            timestamp = message.get('timestamp', '')
            # Message already shown in sender's chat, just log success
            print(f"[DEBUG] Private message sent to UID {target_uid}")
        
        elif msg_type == MessageTypes.HEARTBEAT_ACK:
            # Heartbeat acknowledged - connection is alive
            pass
        
        elif msg_type == MessageTypes.SCREEN_SHARE_PORTS:
            # Server provided screen share port for presenter
            port = message.get('port')
            if port:
                print(f"[DEBUG] Received screen share port: {port}")
                self.start_screen_capture(port)
            else:
                print("[ERROR] No screen share port provided by server")
                self.chat_widget.add_message("System", "❌ Server did not provide screen share port", is_system=True)
        
        elif msg_type == MessageTypes.PRESENT_START_BROADCAST:
            # Someone started presenting
            uid = message.get('uid')
            username = message.get('username')
            port = message.get('screen_share_port')
            
            if uid != self.uid:  # Don't show viewer for our own presentation
                self.chat_widget.add_message("System", f"🖥️ {username} started screen sharing", is_system=True)
                self.show_screen_share_viewer(self.host, port, username)
        
        elif msg_type == MessageTypes.PRESENT_STOP_BROADCAST:
            # Someone stopped presenting
            uid = message.get('uid')
            username = message.get('username')
            
            if uid != self.uid:
                self.chat_widget.add_message("System", f"🖥️ {username} stopped screen sharing", is_system=True)
                self.close_screen_share_viewer()
            
        elif msg_type == MessageTypes.ERROR:
            error_msg = message.get('message', 'Unknown error')
            self.chat_widget.add_message("System", f"Error: {error_msg}", is_system=True)
            
            # If it's a screen sharing error, reset the button state
            if "presenting" in error_msg.lower():
                self.media_controls.screen_sharing = False
                self.media_controls.screen_btn.setChecked(False)
                self.media_controls.screen_btn.setText("🖥️ Share")
    
    def send_chat_message(self, text: str):
        """Send chat message."""
        if self.network_thread and self.connected:
            message = create_chat_message(text)
            self.network_thread.send_message_sync(message)
    
    def send_private_message(self, target_uid: int, username: str):
        """Send private message."""
        if not self.network_thread or not self.connected:
            QMessageBox.warning(self, "Not Connected", "Please connect to server first.")
            return
        
        # Get message text from user
        text, ok = QInputDialog.getText(
            self, 
            "Private Message", 
            f"Send private message to {username}:",
            QLineEdit.EchoMode.Normal
        )
        
        if ok and text.strip():
            print(f"[DEBUG] Sending private message to {username} (UID: {target_uid}): {text.strip()}")
            
            message = {
                'type': MessageTypes.UNICAST,
                'target_uid': target_uid,
                'content': text.strip(),
                'timestamp': datetime.now().isoformat()
            }
            self.network_thread.send_message_sync(message)
            
            # Show the sent message in sender's chat
            self.chat_widget.add_private_message(f"You → {username}", text.strip())
    
    def upload_file(self, file_path=None):
        """Upload file to server. If no file_path provided, opens file dialog."""
        if not self.network_thread or not self.connected:
            QMessageBox.warning(self, "Not Connected", "Please connect to server first.")
            return
        
        # Handle boolean parameter from button clicks (PyQt6 passes checked state)
        if isinstance(file_path, bool):
            file_path = None
        
        # If no file path provided or it's empty, open file dialog
        if file_path is None or file_path == "" or (isinstance(file_path, str) and not file_path.strip()):
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select File to Upload",
                "",
                "All Files (*.*)"
            )
            
            if not file_path:  # User cancelled dialog or no file selected
                return
        
        # Ensure file_path is a valid string and not empty
        if not isinstance(file_path, (str, Path)):
            QMessageBox.warning(self, "File Error", f"Invalid file path type received: {type(file_path)}")
            return
        
        # Convert to string and validate
        file_path_str = str(file_path).strip()
        if not file_path_str:
            QMessageBox.warning(self, "File Error", "No valid file selected.")
            return
        
        try:
            # Create Path object and validate existence
            file_info = Path(file_path_str)
            if not file_info.exists():
                QMessageBox.warning(self, "File Error", "Selected file does not exist.")
                return
            
            # Request upload port from server
            message = {
                'type': MessageTypes.FILE_OFFER,
                'filename': file_info.name,
                'size': file_info.stat().st_size,
                'timestamp': datetime.now().isoformat()
            }
            self.network_thread.send_message_sync(message)
            
            # Store file path for when we get the upload port
            self.pending_upload = file_path_str
            
            # Show upload initiated message
            self.chat_widget.add_message("System", f"Uploading file: {file_info.name}", is_system=True)
            
        except Exception as e:
            QMessageBox.critical(self, "Upload Error", f"Failed to initiate upload: {e}")
    
    def request_file_list(self):
        """Request list of available files from server."""
        if not self.network_thread or not self.connected:
            QMessageBox.warning(self, "Not Connected", "Please connect to server first.")
            return
        
        message = {
            'type': MessageTypes.FILE_REQUEST,
            'timestamp': datetime.now().isoformat()
        }
        self.network_thread.send_message_sync(message)
    
    def download_file(self, file_id: str, filename: str):
        """Download file from server."""
        if not self.network_thread or not self.connected:
            QMessageBox.warning(self, "Not Connected", "Please connect to server first.")
            return
        
        # Ask user where to save the file
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save File As",
            filename,
            "All Files (*.*)"
        )
        
        if save_path:
            # Start download in a separate thread
            self.start_file_download(file_id, save_path)
    
    def start_file_download(self, file_id: str, save_path: str):
        """Start file download process."""
        try:
            self.chat_widget.add_message("System", f"Starting download: {Path(save_path).name}", is_system=True)
            
            # Start download in a separate thread
            download_thread = FileDownloadThread(self.host, 14000, file_id, save_path, self)
            download_thread.download_progress.connect(self.on_download_progress)
            download_thread.download_finished.connect(self.on_download_finished)
            download_thread.download_error.connect(self.on_download_error)
            download_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Download Error", f"Failed to download file: {e}")
    
    def on_download_progress(self, filename: str, progress: int):
        """Handle download progress update."""
        self.chat_widget.add_message("System", f"Downloading {filename}: {progress}%", is_system=True)
    
    def on_download_finished(self, filename: str, save_path: str):
        """Handle download completion."""
        self.chat_widget.add_message("System", f"✅ Download completed: {filename}", is_system=True)
        QMessageBox.information(self, "Download Complete", f"File saved to: {save_path}")
    
    def on_download_error(self, filename: str, error: str):
        """Handle download error."""
        self.chat_widget.add_message("System", f"❌ Download failed: {filename} - {error}", is_system=True)
        QMessageBox.critical(self, "Download Error", f"Failed to download {filename}: {error}")
    
    def start_file_upload(self, file_path: str, upload_port: int):
        """Start file upload to server."""
        try:
            # Validate and convert file path
            if not file_path or not isinstance(file_path, (str, Path)):
                raise ValueError("Invalid file path provided")
            
            file_path_str = str(file_path)
            file_info = Path(file_path_str)
            
            if not file_info.exists():
                raise FileNotFoundError(f"File does not exist: {file_path_str}")
            
            self.chat_widget.add_message("System", f"Uploading {file_info.name}...", is_system=True)
            
            # Start upload in a separate thread
            upload_thread = FileUploadThread(self.host, upload_port, file_path_str, self.username, self)
            upload_thread.upload_progress.connect(self.on_upload_progress)
            upload_thread.upload_finished.connect(self.on_upload_finished)
            upload_thread.upload_error.connect(self.on_upload_error)
            upload_thread.start()
            
        except Exception as e:
            error_msg = f"Failed to upload file: {e}"
            QMessageBox.critical(self, "Upload Error", error_msg)
            filename = Path(file_path).name if file_path else "unknown"
            self.chat_widget.add_message("System", f"❌ Upload failed: {filename}", is_system=True)
    
    def on_upload_progress(self, filename: str, progress: int):
        """Handle upload progress update."""
        self.chat_widget.add_message("System", f"Uploading {filename}: {progress}%", is_system=True)
    
    def on_upload_finished(self, filename: str):
        """Handle upload completion."""
        self.chat_widget.add_message("System", f"✅ File uploaded successfully: {filename}", is_system=True)
    
    def on_upload_error(self, filename: str, error: str):
        """Handle upload error."""
        self.chat_widget.add_message("System", f"❌ Upload failed: {filename} - {error}", is_system=True)
        QMessageBox.critical(self, "Upload Error", f"Failed to upload {filename}: {error}")
    
    def toggle_video(self, enabled: bool):
        """Toggle video on/off."""
        if self.video_client:
            self.video_client.set_enabled(enabled)
        
        # Clear local video display when disabled
        if not enabled:
            if self.video_grid.local_frame:
                self.video_grid.local_frame.set_placeholder()
        
        self.media_controls.video_enabled = enabled
        self.media_controls.video_btn.setChecked(enabled)
        self.media_controls.video_btn.setText("📹 Video On" if enabled else "📹 Video Off")
    
    def clear_local_video(self):
        """Clear the local video display."""
        if self.video_grid.local_frame:
            self.video_grid.local_frame.set_placeholder()
    
    def toggle_audio(self, enabled: bool):
        """Toggle audio on/off."""
        if self.audio_client:
            self.audio_client.set_enabled(enabled)
        self.media_controls.audio_enabled = enabled
        self.media_controls.audio_btn.setChecked(enabled)
        self.media_controls.audio_btn.setText("🎤 Audio On" if enabled else "🎤 Audio Off")
    
    def toggle_screen_share(self, enabled: bool):
        """Toggle screen sharing on/off."""
        print(f"[DEBUG] Screen share toggle called: enabled={enabled}")
        if enabled:
            self.start_screen_sharing()
        else:
            self.stop_screen_sharing()
    
    def start_screen_sharing(self):
        """Start screen sharing."""
        if self.network_thread and self.connected:
            print("[DEBUG] Sending PRESENT_START message to server")
            
            # Start preview immediately when user requests screen sharing
            self.start_screen_preview()
            
            # Send present start request to server
            message = {
                'type': MessageTypes.PRESENT_START,
                'timestamp': datetime.now().isoformat()
            }
            self.network_thread.send_message_sync(message)
            self.chat_widget.add_message("System", "🖥️ Requesting to start screen sharing...", is_system=True)
            
            # Update status to show we're requesting
            if hasattr(self, 'screen_share_status'):
                self.screen_share_status.setText("⏳ Requesting screen share permission...")
                self.screen_share_status.setStyleSheet("""
                    QLabel {
                        background-color: #ffc107;
                        color: #000000;
                        border-radius: 6px;
                        padding: 10px;
                        font-size: 14px;
                        font-weight: bold;
                        margin: 10px 0;
                    }
                """)
        else:
            print("[ERROR] Cannot start screen sharing - not connected to server")
            QMessageBox.warning(self, "Not Connected", "Please connect to server first.")
            
            # Update status to show error
            if hasattr(self, 'screen_share_status'):
                self.screen_share_status.setText("❌ Not connected to server")
                self.screen_share_status.setStyleSheet("""
                    QLabel {
                        background-color: #dc3545;
                        color: #ffffff;
                        border-radius: 6px;
                        padding: 10px;
                        font-size: 14px;
                        font-weight: bold;
                        margin: 10px 0;
                    }
                """)
    
    def stop_screen_sharing(self):
        """Stop screen sharing."""
        if self.network_thread and self.connected:
            print("[DEBUG] Sending PRESENT_STOP message to server")
            # Send present stop request to server
            message = {
                'type': MessageTypes.PRESENT_STOP,
                'timestamp': datetime.now().isoformat()
            }
            self.network_thread.send_message_sync(message)
            self.chat_widget.add_message("System", "🖥️ Stopping screen sharing...", is_system=True)
        
        # Stop local screen capture if running
        if hasattr(self, 'screen_capture_client') and self.screen_capture_client:
            self.screen_capture_client.stop()
            self.screen_capture_client = None
        
        # Stop preview capture
        self.stop_screen_preview()
        
        # Reset UI state - both media controls and dedicated tab
        self.media_controls.screen_sharing = False
        self.media_controls.screen_btn.setChecked(False)
        self.media_controls.screen_btn.setText("🖥️ Share")
        
        # Update dedicated screen sharing tab buttons and status
        if hasattr(self, 'start_share_btn') and hasattr(self, 'stop_share_btn'):
            self.start_share_btn.setEnabled(True)
            self.stop_share_btn.setEnabled(False)
        
        if hasattr(self, 'screen_share_status'):
            self.screen_share_status.setText("📱 Ready to share screen")
            self.screen_share_status.setStyleSheet("""
                QLabel {
                    background-color: #333333;
                    color: #ffffff;
                    border-radius: 6px;
                    padding: 10px;
                    font-size: 14px;
                    font-weight: bold;
                    margin: 10px 0;
                }
            """)
    
    def start_screen_capture(self, port: int):
        """Start screen capture for presentation."""
        try:
            print(f"[DEBUG] Starting screen capture client on port {port}")
            
            # Test screen capture capability first
            test_client = ScreenCaptureClient(self.host, port, self)
            test_screenshot = test_client.capture_screen()
            
            if test_screenshot is None:
                raise Exception("Screen capture not available on this platform")
            
            self.screen_capture_client = ScreenCaptureClient(self.host, port, self)
            self.screen_capture_client.start()
            
            self.chat_widget.add_message("System", "🖥️ You are now sharing your screen", is_system=True)
            
            # Update UI - both media controls and dedicated tab
            self.media_controls.screen_sharing = True
            self.media_controls.screen_btn.setChecked(True)
            self.media_controls.screen_btn.setText("🖥️ Sharing")
            
            # Update dedicated screen sharing tab buttons and status
            if hasattr(self, 'start_share_btn') and hasattr(self, 'stop_share_btn'):
                self.start_share_btn.setEnabled(False)
                self.stop_share_btn.setEnabled(True)
            
            if hasattr(self, 'screen_share_status'):
                self.screen_share_status.setText("🖥️ Currently sharing your screen")
                self.screen_share_status.setStyleSheet("""
                    QLabel {
                        background-color: #28a745;
                        color: #ffffff;
                        border-radius: 6px;
                        padding: 10px;
                        font-size: 14px;
                        font-weight: bold;
                        margin: 10px 0;
                    }
                """)
            
        except Exception as e:
            error_msg = str(e)
            if "PIL" in error_msg or "Pillow" in error_msg:
                error_msg = "Screen capture requires Pillow. Install with: pip install Pillow"
            
            QMessageBox.critical(self, "Screen Share Error", f"Failed to start screen sharing: {error_msg}")
            self.chat_widget.add_message("System", "❌ Failed to start screen sharing", is_system=True)
            
            # Reset button states - both media controls and dedicated tab
            self.media_controls.screen_sharing = False
            self.media_controls.screen_btn.setChecked(False)
            self.media_controls.screen_btn.setText("🖥️ Share")
            
            if hasattr(self, 'start_share_btn') and hasattr(self, 'stop_share_btn'):
                self.start_share_btn.setEnabled(True)
                self.stop_share_btn.setEnabled(False)
            
            if hasattr(self, 'screen_share_status'):
                self.screen_share_status.setText("❌ Failed to start screen sharing")
                self.screen_share_status.setStyleSheet("""
                    QLabel {
                        background-color: #dc3545;
                        color: #ffffff;
                        border-radius: 6px;
                        padding: 10px;
                        font-size: 14px;
                        font-weight: bold;
                        margin: 10px 0;
                    }
                """)
    
    def show_screen_share_viewer(self, host: str, port: int, presenter_name: str):
        """Show screen share viewer window."""
        try:
            if hasattr(self, 'screen_viewer') and self.screen_viewer:
                self.screen_viewer.close()
            
            self.screen_viewer = ScreenShareViewer(host, port, presenter_name, self)
            self.screen_viewer.show()
            
        except Exception as e:
            print(f"[ERROR] Failed to open screen share viewer: {e}")
            self.chat_widget.add_message("System", "❌ Failed to open screen share viewer", is_system=True)
    
    def close_screen_share_viewer(self):
        """Close screen share viewer window."""
        if hasattr(self, 'screen_viewer') and self.screen_viewer:
            self.screen_viewer.close()
            self.screen_viewer = None
    
    def start_screen_preview(self):
        """Start screen preview in the Screen Share tab."""
        try:
            if not hasattr(self, 'screen_preview_capture') or self.screen_preview_capture is None:
                print("[DEBUG] Starting screen preview capture")
                self.screen_preview_capture = ScreenPreviewCapture(self)
                self.screen_preview_capture.preview_frame_ready.connect(self.update_screen_preview)
                self.screen_preview_capture.start()
                
                # Update preview label to show it's starting
                if hasattr(self, 'screen_preview_label'):
                    self.screen_preview_label.setText("🔄 Starting preview...")
                    self.screen_preview_label.setStyleSheet("""
                        QLabel {
                            background-color: transparent;
                            color: #ffc107;
                            font-size: 14px;
                            padding: 20px;
                        }
                    """)
        except Exception as e:
            print(f"[ERROR] Failed to start screen preview: {e}")
            if hasattr(self, 'screen_preview_label'):
                self.screen_preview_label.setText("❌ Preview failed to start")
    
    def stop_screen_preview(self):
        """Stop screen preview in the Screen Share tab."""
        try:
            if hasattr(self, 'screen_preview_capture') and self.screen_preview_capture:
                print("[DEBUG] Stopping screen preview capture")
                self.screen_preview_capture.stop()
                self.screen_preview_capture.wait()
                self.screen_preview_capture = None
                
                # Reset preview label
                if hasattr(self, 'screen_preview_label'):
                    self.screen_preview_label.clear()
                    self.screen_preview_label.setText("Screen sharing preview will appear here when you start sharing")
                    self.screen_preview_label.setStyleSheet("""
                        QLabel {
                            background-color: transparent;
                            color: #888888;
                            font-size: 16px;
                            padding: 50px;
                        }
                    """)
        except Exception as e:
            print(f"[ERROR] Failed to stop screen preview: {e}")
    
    def update_screen_preview(self, frame: np.ndarray):
        """Update the screen preview display with captured frame."""
        try:
            if frame is not None and frame.size > 0 and hasattr(self, 'screen_preview_label'):
                # Convert BGR to RGB for Qt
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Create QImage
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                
                # Convert to QPixmap and scale to fit the preview area
                pixmap = QPixmap.fromImage(qt_image)
                
                # Scale to fit the preview label while maintaining aspect ratio
                label_size = self.screen_preview_label.size()
                scaled_pixmap = pixmap.scaled(
                    label_size, 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                )
                
                # Set the pixmap to the label
                self.screen_preview_label.setPixmap(scaled_pixmap)
                
                # Update styling to remove text styling
                self.screen_preview_label.setStyleSheet("""
                    QLabel {
                        background-color: transparent;
                        border: none;
                    }
                """)
                
        except Exception as e:
            print(f"[ERROR] Failed to update screen preview: {e}")
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Stop screen preview if running
        self.stop_screen_preview()
        
        # Disconnect from server
        self.disconnect_from_server()
        event.accept()


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='LAN Collaboration Client - Complete Implementation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Features:
  - Real-time video conferencing with multiple participants
  - High-quality audio communication
  - Screen sharing viewing
  - Text chat with broadcast and private messaging
  - File sharing with progress tracking
  - Modern PyQt6 GUI interface

Examples:
  # Start client (will show connection dialog)
  python main_client.py
  
  # Start with pre-filled server info
  python main_client.py --server 192.168.1.100 --username "John Doe"
        """
    )
    
    parser.add_argument('--server', type=str, default=None,
                       help='Server IP address (default: will be asked in dialog)')
    parser.add_argument('--port', type=int, default=DEFAULT_TCP_PORT,
                       help='Server port (default: 9000)')
    parser.add_argument('--username', type=str, default=None,
                       help='Username (default: will be asked in dialog)')
    
    args = parser.parse_args()
    
    try:
        # Set up application with better compatibility
        app = QApplication(sys.argv)
        app.setApplicationName("LAN Collaboration Client")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("LAN Collab")
        app.setOrganizationDomain("lancollab.local")
        
        # Enable high DPI support (Qt6 handles this automatically)
        try:
            # These attributes were deprecated in Qt6 but may still be available in some versions
            if hasattr(Qt.ApplicationAttribute, 'AA_EnableHighDpiScaling'):
                app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
            if hasattr(Qt.ApplicationAttribute, 'AA_UseHighDpiPixmaps'):
                app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
        except AttributeError:
            # Qt6 handles high DPI automatically, so this is not needed
            print("[INFO] High DPI scaling handled automatically by Qt6")
            pass
        
        # Set consistent style across platforms
        try:
            if sys.platform == "darwin":  # macOS
                app.setStyle("macOS")
            elif sys.platform == "win32":  # Windows
                app.setStyle("windowsvista")
            else:  # Linux and others
                app.setStyle("Fusion")
        except Exception as e:
            print(f"[INFO] Could not set preferred style, using default: {e}")
            app.setStyle("Fusion")  # Fallback to Fusion
        
        # Set application icon if available
        try:
            app.setWindowIcon(QIcon())  # You can add an icon file here later
        except:
            pass
        
        # Print system info for debugging
        print(f"[INFO] Python version: {sys.version}")
        print(f"[INFO] Platform: {sys.platform}")
        print(f"[INFO] Qt style: {app.style().objectName()}")
        
        # Check PyQt6 version
        try:
            from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR
            print(f"[INFO] PyQt6 version: {PYQT_VERSION_STR}")
            print(f"[INFO] Qt version: {QT_VERSION_STR}")
            
            # Version compatibility check
            pyqt_version = tuple(map(int, PYQT_VERSION_STR.split('.')))
            if pyqt_version < (6, 4, 0):
                print("[WARNING] PyQt6 version is older than 6.4.0, some features may not work properly")
                print("[INFO] Consider upgrading: pip install --upgrade PyQt6")
                
        except ImportError:
            print("[WARNING] Could not determine PyQt6 version")
        except Exception as e:
            print(f"[WARNING] Version check failed: {e}")
        
        # Create main window
        main_window = ClientMainWindow()
        
        # Center window on screen
        screen = app.primaryScreen().geometry()
        window_geometry = main_window.geometry()
        x = (screen.width() - window_geometry.width()) // 2
        y = (screen.height() - window_geometry.height()) // 2
        main_window.move(x, y)
        
        main_window.show()
        
        print("[INFO] LAN Collaboration Client started")
        return app.exec()
        
    except KeyboardInterrupt:
        print("\n[INFO] Client terminated by user")
        return 0
    except Exception as e:
        print(f"[ERROR] Client error: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())