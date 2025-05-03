import cv2
import tkinter as tk
from tkinter import ttk
from threading import Thread
from PIL import Image, ImageTk
import numpy as np

class CameraApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Camera Recorder with Settings")

        self.cap = None
        self.recording = False
        self.zoom = 1.0
        self.brightness = 0
        self.out = None

        # Layout: Horizontal
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(fill="both", expand=True)

        # Left side: fixed-size canvas for video
        self.video_frame = tk.Frame(self.main_frame, width=640, height=480)
        self.video_frame.pack(side="left", padx=10, pady=10)
        self.video_frame.pack_propagate(False)  # Prevent resizing

        self.video_label = tk.Label(self.video_frame)
        self.video_label.pack()

        # Right side: controls
        self.controls_frame = tk.Frame(self.main_frame)
        self.controls_frame.pack(side="right", fill="y", padx=10, pady=10)

        # Zoom control
        tk.Label(self.controls_frame, text="Zoom").pack()
        self.zoom_slider = ttk.Scale(self.controls_frame, from_=1.0, to=2.0, value=1.0, orient='horizontal', command=self.set_zoom)
        self.zoom_slider.pack(fill="x", pady=5)

        # Brightness control
        tk.Label(self.controls_frame, text="Brightness").pack()
        self.brightness_slider = ttk.Scale(self.controls_frame, from_=-100, to=100, value=0, orient='horizontal', command=self.set_brightness)
        self.brightness_slider.pack(fill="x", pady=5)

        # Buttons
        self.start_btn = ttk.Button(self.controls_frame, text="Start Camera", command=self.start_camera)
        self.start_btn.pack(fill="x", pady=(20, 5))

        self.record_btn = ttk.Button(self.controls_frame, text="Start Recording", command=self.start_recording, state='disabled')
        self.record_btn.pack(fill="x", pady=5)

        self.stop_btn = ttk.Button(self.controls_frame, text="Stop Recording", command=self.stop_recording, state='disabled')
        self.stop_btn.pack(fill="x", pady=5)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def set_zoom(self, val):
        self.zoom = float(val)

    def set_brightness(self, val):
        self.brightness = int(float(val))

    def start_camera(self):
        if self.cap is None:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                print("No camera found")
                return
            self.record_btn.config(state='normal')
            Thread(target=self.show_frames, daemon=True).start()

    def show_frames(self):
        while self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break

            # Apply zoom
            frame = self.apply_zoom(frame, self.zoom)

            # Apply brightness
            frame = cv2.convertScaleAbs(frame, alpha=1, beta=self.brightness)

            # Write frame if recording
            if self.recording and self.out:
                self.out.write(frame)

            # Convert to display in Tkinter
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.config(image=imgtk)

    def apply_zoom(self, frame, zoom_factor):
        if zoom_factor == 1.0:
            return frame
        h, w = frame.shape[:2]
        new_h, new_w = int(h / zoom_factor), int(w / zoom_factor)
        y1 = (h - new_h) // 2
        x1 = (w - new_w) // 2
        cropped = frame[y1:y1+new_h, x1:x1+new_w]
        return cv2.resize(cropped, (w, h))

    def start_recording(self):
        if self.cap is None or not self.cap.isOpened():
            return
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.out = cv2.VideoWriter('recording.avi', fourcc, 20.0, (width, height))
        self.recording = True
        self.stop_btn.config(state='normal')
        self.record_btn.config(state='disabled')

    def stop_recording(self):
        self.recording = False
        if self.out:
            self.out.release()
            self.out = None
        self.stop_btn.config(state='disabled')
        self.record_btn.config(state='normal')

    def on_close(self):
        self.stop_recording()
        if self.cap:
            self.cap.release()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = CameraApp(root)
    root.mainloop()
