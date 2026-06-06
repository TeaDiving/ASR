import sys
import os
import asyncio
import threading
import numpy as np
import time
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, 
                             QMainWindow, QPushButton, QLineEdit, QFormLayout, 
                             QGroupBox, QHBoxLayout, QComboBox, QFrame)
from PySide6.QtCore import Qt, Signal, QObject, QPoint
from PySide6.QtGui import QFont, QColor

# Fix imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from audio.capture import AudioCapturer
from audio.vad import VADHandler
from asr.whisper import WhisperASR
from backend.text_preprocessing import normalize_text
from backend.xfyun_translation import translate_text, XFYUNCredentials, read_xfyun_credentials

class ASRSignals(QObject):
    subtitle_updated = Signal(str, str, bool) 
    status_updated = Signal(str)
    loading_finished = Signal()

class ASRWorker(threading.Thread):
    def __init__(self, signals, model_size="tiny", creds=None):
        super().__init__()
        self.signals = signals
        self.is_running = False
        self.model_size = model_size
        self.creds = creds
        self.audio_buffer = []
        self.is_processing = False

    def stop(self):
        self.is_running = False
        if hasattr(self, 'capturer') and self.capturer:
            self.capturer.stop()

    def run(self):
        self.is_running = True
        
        # Initialize components INSIDE the thread to keep UI responsive
        try:
            self.capturer = AudioCapturer(samplerate=16000, blocksize=512)
            self.vad = VADHandler()
            self.asr = WhisperASR(model_size=self.model_size, device="cpu")
            self.signals.loading_finished.emit() # Notify UI that loading is done
        except Exception as e:
            self.signals.status_updated.emit(f"Init Error: {str(e)}")
            return

        self.capturer.start()
        self.signals.status_updated.emit("System LIVE - High Speed Sync")
        
        in_speech = False
        silence_counter = 0
        
        while self.is_running:
            try:
                if not self.capturer.audio_queue.empty():
                    chunk = self.capturer.audio_queue.get_nowait().flatten()
                    peak = np.max(np.abs(chunk))
                    
                    speech_dict = self.vad.is_speech(chunk)
                    if speech_dict:
                        if 'start' in speech_dict: in_speech = True; silence_counter = 0
                        elif 'end' in speech_dict: in_speech = False

                    if in_speech or peak > 0.05:
                        self.audio_buffer.append(chunk)
                        silence_counter = 0
                    else:
                        if len(self.audio_buffer) > 0:
                            silence_counter += 1
                    
                    if len(self.audio_buffer) > 160:
                        self.audio_buffer = self.audio_buffer[-90:] 
                    
                    if len(self.audio_buffer) > 10:
                        if not in_speech and silence_counter > 12:
                            self.request_transcribe(is_final=True)
                            self.audio_buffer = []
                            silence_counter = 0
                        elif len(self.audio_buffer) % 20 == 0:
                            self.request_transcribe(is_final=False)
                else:
                    time.sleep(0.01)
            except Exception as e:
                print(f"Worker Loop Error: {e}")

    def request_transcribe(self, is_final=False):
        if self.is_processing: return 
        audio_snapshot = np.concatenate(self.audio_buffer)
        self.is_processing = True
        threading.Thread(target=self._do_work, args=(audio_snapshot, is_final), daemon=True).start()

    def _do_work(self, audio, is_final):
        try:
            text, lang, confidence = self.asr.transcribe(audio)
            if text:
                normalized = normalize_text(text)
                if normalized:
                    try:
                        translated = asyncio.run(translate_text(normalized, from_lang=lang, credentials=self.creds))
                        self.signals.subtitle_updated.emit(text, translated, is_final)
                    except Exception: pass
        finally:
            self.is_processing = False

class SubtitleOverlay(QWidget):
    close_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(30, 25, 30, 15)
        
        self.close_btn = QPushButton("×", self)
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setStyleSheet("color: rgba(255, 255, 255, 150); font-size: 20px; font-weight: bold; background: transparent; border: none;")
        self.close_btn.clicked.connect(self.close_requested.emit)
        
        self.label_source = QLabel("")
        self.label_source.setStyleSheet("color: rgba(255, 255, 255, 180); font-size: 16px; background: transparent;")
        self.label_source.setAlignment(Qt.AlignCenter)
        self.label_source.setWordWrap(False)
        
        self.label_trans = QLabel("Wait for audio...")
        self.label_trans.setStyleSheet("color: white; font-size: 26px; font-weight: bold; background: transparent;")
        self.label_trans.setAlignment(Qt.AlignCenter)
        self.label_trans.setWordWrap(False)
        
        self.layout.addWidget(self.label_source)
        self.layout.addWidget(self.label_trans)
        self.setLayout(self.layout)
        
        self.resize(900, 140)
        self._drag_pos = None
        
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2, screen.height() - 180)

    def resizeEvent(self, event):
        self.close_btn.move(self.width() - 35, 10)
        super().resizeEvent(event)

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QBrush
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 170)))
        painter.drawRoundedRect(self.rect(), 12, 12)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._drag_pos:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event): self._drag_pos = None

    def update_text(self, source, translated, is_final):
        if len(translated) > 50: font_size = 18
        elif len(translated) > 35: font_size = 22
        else: font_size = 26
        
        max_trans_len = 55
        if len(translated) > max_trans_len: translated = "..." + translated[-(max_trans_len-3):]
        max_source_len = 80
        if len(source) > max_source_len: source = "..." + source[-(max_source_len-3):]

        self.label_source.setText(source)
        self.label_trans.setText(translated)
        self.label_trans.setStyleSheet(f"color: white; font-size: {font_size}px; font-weight: bold; background: transparent;")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Desktop Interpreter")
        self.setMinimumSize(450, 480)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        api_group = QGroupBox("iFLYTEK API Configuration")
        api_form = QFormLayout(api_group)
        default_creds = None
        try: default_creds = read_xfyun_credentials()
        except: pass
        self.app_id = QLineEdit(default_creds.app_id if default_creds else "")
        self.api_key = QLineEdit(default_creds.api_key if default_creds else "")
        self.api_secret = QLineEdit(default_creds.api_secret if default_creds else "", echoMode=QLineEdit.Password)
        api_form.addRow("AppID:", self.app_id); api_form.addRow("APIKey:", self.api_key); api_form.addRow("APISecret:", self.api_secret)
        layout.addWidget(api_group)
        
        asr_group = QGroupBox("ASR Settings")
        asr_form = QFormLayout(asr_group)
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.model_combo.setCurrentText("tiny")
        asr_form.addRow("Whisper Model:", self.model_combo)
        layout.addWidget(asr_group)
        
        self.start_btn = QPushButton("START Interpretation")
        self.start_btn.setFixedHeight(55)
        self.start_btn.setStyleSheet("background-color: #28a745; color: white; font-size: 16px; font-weight: bold; border-radius: 5px;")
        self.start_btn.clicked.connect(self.toggle_asr)
        layout.addWidget(self.start_btn)
        
        # STATUS BOX (The long box at the bottom)
        self.status_frame = QFrame()
        self.status_frame.setFrameShape(QFrame.StyledPanel)
        self.status_frame.setStyleSheet("background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px;")
        status_layout = QVBoxLayout(self.status_frame)
        self.status_label = QLabel("Status: Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #495057; font-weight: bold;")
        status_layout.addWidget(self.status_label)
        layout.addWidget(self.status_frame)
        
        self.overlay = SubtitleOverlay()
        self.overlay.close_requested.connect(self.toggle_asr)
        self.signals = ASRSignals()
        self.signals.subtitle_updated.connect(self.overlay.update_text)
        self.signals.status_updated.connect(self.update_status_text)
        self.signals.loading_finished.connect(self.on_loading_finished)
        self.worker = None

    def update_status_text(self, text):
        self.status_label.setText(text)

    def on_loading_finished(self):
        self.status_frame.setStyleSheet("background-color: #e9ecef; border: 1px solid #ced4da; border-radius: 5px;")
        self.status_label.setText("Status: Running (Loaded)")

    def toggle_asr(self):
        if self.worker and self.worker.is_running:
            self.worker.stop()
            self.start_btn.setText("START Interpretation")
            self.start_btn.setStyleSheet("background-color: #28a745; color: white;")
            self.status_frame.setStyleSheet("background-color: #f8f9fa; border: 1px solid #dee2e6;")
            self.status_label.setText("Status: Stopped")
            self.overlay.hide()
        else:
            creds = XFYUNCredentials(app_id=self.app_id.text().strip(), api_key=self.api_key.text().strip(), api_secret=self.api_secret.text().strip())
            if not creds.app_id or not creds.api_key:
                self.status_label.setText("Status: Missing API Keys!"); return
            
            # Show loading style in main window
            self.status_frame.setStyleSheet("background-color: #ffffff; border: 2px solid #007bff; border-radius: 5px;")
            self.status_label.setText("Whisper 模型加载中...")
            
            self.overlay.show()
            self.worker = ASRWorker(self.signals, model_size=self.model_combo.currentText(), creds=creds)
            self.worker.start()
            self.start_btn.setText("STOP Interpretation")
            self.start_btn.setStyleSheet("background-color: #dc3545; color: white;")

    def closeEvent(self, event):
        if self.worker: self.worker.stop()
        self.overlay.close(); super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
