"""
I-Study - 시야 캘리브레이션 창
사용자 시선 범위를 측정하여 임계값을 설정합니다.
"""

import customtkinter as ctk
import cv2
from PIL import Image


class CalibrationWindow(ctk.CTkToplevel):
    """시야 캘리브레이션 창"""

    def __init__(self, parent, gaze_tracker, on_complete):
        super().__init__(parent)
        self.gaze_tracker = gaze_tracker
        self.on_complete = on_complete
        self.sample_count = 0
        self.required_samples = 30

        self.title("시야 설정")
        self.geometry("450x480")
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color="#F2F2F7")

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 450) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 480) // 2
        self.geometry(f"+{x}+{y}")

        self._setup_ui()
        self._start_calibration()

    def _setup_ui(self):
        ctk.CTkLabel(self, text="시야 설정", font=ctk.CTkFont(size=20, weight="bold"), text_color="#000000").pack(pady=(25, 10))
        ctk.CTkLabel(self, text="화면 중앙을 바라보세요", font=ctk.CTkFont(size=15), text_color="#8E8E93").pack(pady=(0, 15))

        self.camera_frame = ctk.CTkFrame(self, fg_color="#000000", corner_radius=12, width=300, height=225)
        self.camera_frame.pack(pady=10)
        self.camera_frame.pack_propagate(False)
        self.camera_label = ctk.CTkLabel(self.camera_frame, text="")
        self.camera_label.pack(expand=True, fill="both")

        self.progress_bar = ctk.CTkProgressBar(self, width=300, height=8, corner_radius=4)
        self.progress_bar.pack(pady=20)
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(self, text="0 / 30", font=ctk.CTkFont(size=14), text_color="#8E8E93")
        self.status_label.pack(pady=5)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="건너뛰기", width=100, height=40, fg_color="#E5E5EA", hover_color="#D1D1D6", text_color="#000000", corner_radius=10, command=self._skip).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="취소", width=100, height=40, fg_color="#FF3B30", hover_color="#CC2F26", corner_radius=10, command=self._cancel).pack(side="left", padx=10)

    def _start_calibration(self):
        self.gaze_tracker.reset_calibration()
        self._update_loop()

    def _update_loop(self):
        if not self.winfo_exists():
            return
        frame = self.gaze_tracker.get_current_frame()
        status = self.gaze_tracker.get_status()
        if frame is not None:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            img = img.resize((300, 225), Image.Resampling.LANCZOS)
            photo = ctk.CTkImage(light_image=img, dark_image=img, size=(300, 225))
            self.camera_label.configure(image=photo)
            self.camera_label.image = photo
        if status['face_detected']:
            if self.gaze_tracker.add_calibration_sample():
                self.sample_count += 1
                self.progress_bar.set(self.sample_count / self.required_samples)
                self.status_label.configure(text=f"{self.sample_count} / {self.required_samples}")
                if self.sample_count >= self.required_samples:
                    self._complete_calibration()
                    return
        self.after(100, self._update_loop)

    def _complete_calibration(self):
        if self.gaze_tracker.complete_calibration(margin=0.12):
            self.on_complete(True)
        else:
            self.on_complete(False)
        self.destroy()

    def _skip(self):
        self.on_complete(True)
        self.destroy()

    def _cancel(self):
        self.on_complete(False)
        self.destroy()
