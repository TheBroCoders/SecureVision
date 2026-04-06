import os
import cv2
import time
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import numpy as np
import psutil
import json
import winsound  # WAV sound alert

from backend import AttendanceSystem   # face recognition backend

# ---------------------------
# Config / Paths
# ---------------------------
SNAPSHOT_DIR = "snapshots"
SCREENSHOT_DIR = "screenshots"
ALERT_DIR = "restricted_snapshots"
for d in [SNAPSHOT_DIR, SCREENSHOT_DIR, ALERT_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

CAM_NAMES = {
    "CAM 1": "Office",
    "CAM 2": "Parking",
    "CAM 3": "Server Room",
    "CAM 4": "Cafe"
}

ALARM_FILE = "alarm.wav"   # your custom WAV file

# ---------------------------
# Main app
# ---------------------------
class FaceGuardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SecureVision-Control Room")
        self.root.geometry("1500x880")
        self.root.configure(bg="#0a0a0a")

        # Camera source
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        # Face recognition backend
        id_to_name_map = {
            101: "Arijeet Banerjee",
            102: "Sangeet",
            103: "Abhishek",
            104: "Indrajit",
            105: "Security Team"
        }
        self.attendance_system = AttendanceSystem(
            trainer_file="trainer.yml",
            cascade_file="haarcascade_frontalface_default.xml",
            id_to_name_map=id_to_name_map
        )

        # UI state
        self.mode = "quad"
        self.zoom_mode = False
        self.last_frame = None

        # Alarm flag
        self.alarm_playing = False

        # Configurable restricted zone
        self.config_file = "config.json"
        self.restricted_zone = self.load_config()

        # ---------------- UI Layout ----------------
        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # start loops
        self._running = True
        self.update_loop()
        self.update_system_status()

    # ---------------- Config helpers ----------------
    def load_config(self):
        default_zone = (200, 100, 500, 400)
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                    return tuple(data.get("restricted_zone", default_zone))
            except:
                return default_zone
        return default_zone

    def save_config(self):
        data = {"restricted_zone": self.restricted_zone}
        with open(self.config_file, "w") as f:
            json.dump(data, f)

    # ---------------- UI Layout ----------------
    def setup_ui(self):
        # Top bar
        top = tk.Frame(self.root, bg="#111111", height=60)
        top.pack(side="top", fill="x")

        tk.Label(top, text="🛡️ SecureVision",
                 font=("Helvetica", 20, "bold"),
                 fg="#00ffd7", bg="#111111").pack(side="left", padx=20)

        self.status_label = tk.Label(top, text="🟢 LIVE MODE",
                                     font=("Helvetica", 14, "bold"),
                                     fg="#00ff88", bg="#111111")
        self.status_label.pack(side="right", padx=18)

        # Sidebar
        sidebar = tk.Frame(self.root, bg="#121212", width=260)
        sidebar.pack(side="left", fill="y")

        tk.Label(sidebar, text="📡 VIEW MODE",
                 font=("Helvetica", 16, "bold"), fg="#00ffd7", bg="#121212").pack(pady=(12,6))

        ttk.Button(sidebar, text="Quad View", command=lambda: self.set_mode("quad")).pack(fill="x", padx=12, pady=6)
        for cam in CAM_NAMES.keys():
            ttk.Button(sidebar, text=f"{cam} ({CAM_NAMES[cam]})", command=lambda c=cam: self.set_mode(c)).pack(fill="x", padx=12, pady=6)

        ttk.Separator(sidebar).pack(fill="x", padx=10, pady=(10,8))
        tk.Label(sidebar, text="📸 SNAPSHOT",
                 font=("Helvetica", 14, "bold"), fg="#00ffd7", bg="#121212").pack(pady=(6,6))

        ttk.Button(sidebar, text="Save Screen Capture", command=self.save_screenshot).pack(fill="x", padx=12, pady=6)

        ttk.Separator(sidebar).pack(fill="x", padx=10, pady=(10,8))
        tk.Label(sidebar, text="🔍 ZOOM & EFFECT",
                 font=("Helvetica", 14, "bold"), fg="#00ffd7", bg="#121212").pack(pady=(6,6))

        ttk.Button(sidebar, text="Toggle Zoom", command=self.toggle_zoom).pack(fill="x", padx=12, pady=6)

        ttk.Separator(sidebar).pack(fill="x", padx=10, pady=(10,8))
        tk.Label(sidebar, text="⚙️ SETTINGS",
                 font=("Helvetica", 14, "bold"), fg="#00ffd7", bg="#121212").pack(pady=(6,6))

        ttk.Button(sidebar, text="Open Settings", command=self.show_settings).pack(fill="x", padx=12, pady=6)

        # NEW: Stop Alarm button
        ttk.Separator(sidebar).pack(fill="x", padx=10, pady=(10,8))
        ttk.Button(sidebar, text="🛑 Stop Alarm", command=self.stop_alarm).pack(fill="x", padx=12, pady=6)

        # Center feed
        self.center_frame = tk.Frame(self.root, bg="black", width=1000, height=700)
        self.center_frame.pack(side="left", padx=14, pady=12)

        self.canvas_label = tk.Label(self.center_frame, bg="black")
        self.canvas_label.pack()

        # Right panel
        right = tk.Frame(self.root, bg="#111111", width=300)
        right.pack(side="right", fill="y")

        tk.Label(right, text="📊 System Status",
                 font=("Helvetica", 14, "bold"), fg="#00ffd7", bg="#111111").pack(pady=(12,8))

        self.cpu_label = tk.Label(right, text="CPU: 0%", font=("Consolas", 12),
                                  fg="#00ff88", bg="#111111")
        self.cpu_label.pack(pady=4)

        self.mem_label = tk.Label(right, text="Memory: 0%", font=("Consolas", 12),
                                  fg="#ffcc00", bg="#111111")
        self.mem_label.pack(pady=4)

        ttk.Separator(right).pack(fill="x", padx=10, pady=(10,8))

        tk.Label(right, text="📝 System Logs",
                 font=("Helvetica", 14, "bold"), fg="#00ffd7", bg="#111111").pack(pady=(8,6))

        self.log_console = tk.Text(right, bg="#0b0b0b", fg="#00ff88",
                                   font=("Consolas", 10), width=40, height=25)
        self.log_console.pack(padx=8, pady=6)
        self.log_console.config(state="disabled")

    # ---------------- UI helpers ----------------
    def set_mode(self, mode):
        self.mode = mode

    def save_screenshot(self):
        ts = int(time.time())
        filename = os.path.join(SCREENSHOT_DIR, f"screenshot_{ts}.png")
        if self.last_frame is not None:
            self.last_frame.save(filename)
            messagebox.showinfo("Screenshot", f"Saved screen to {filename}")
        else:
            messagebox.showwarning("Screenshot", "No image to save.")

    def toggle_zoom(self):
        self.zoom_mode = not self.zoom_mode

    def show_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.geometry("300x250")
        win.configure(bg="#111111")

        tk.Label(win, text="Restricted Zone (x1,y1,x2,y2)",
                 font=("Helvetica", 12, "bold"), fg="#00ffd7", bg="#111111").pack(pady=10)

        entries = []
        labels = ["X1", "Y1", "X2", "Y2"]
        for i, val in enumerate(self.restricted_zone):
            frame = tk.Frame(win, bg="#111111")
            frame.pack(pady=4)
            tk.Label(frame, text=labels[i], fg="white", bg="#111111").pack(side="left", padx=5)
            e = tk.Entry(frame)
            e.insert(0, str(val))
            e.pack(side="left")
            entries.append(e)

        def save_and_close():
            try:
                vals = tuple(int(e.get()) for e in entries)
                self.restricted_zone = vals
                self.save_config()
                self.add_log(f"⚙️ Restricted zone updated: {vals}")
                win.destroy()
            except:
                messagebox.showerror("Error", "Invalid values! Must be integers.")

        ttk.Button(win, text="Save", command=save_and_close).pack(pady=15)

    def update_system_status(self):
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        self.cpu_label.config(text=f"CPU: {cpu}%")
        self.mem_label.config(text=f"Memory: {mem}%")
        self.root.after(1000, self.update_system_status)

    def add_log(self, message):
        ts = time.strftime("%H:%M:%S")
        self.log_console.config(state="normal")
        self.log_console.insert("end", f"[{ts}] {message}\n")
        self.log_console.see("end")
        self.log_console.config(state="disabled")

    def box_overlap(self, boxA, boxB):
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])
        return (xA < xB and yA < yB)

    # ---------------- Alarm helpers ----------------
    def stop_alarm(self):
        winsound.PlaySound(None, winsound.SND_PURGE)
        self.alarm_playing = False
        self.add_log("🛑 Alarm stopped manually (button pressed)")

    # ---------------- Frame analysis ----------------
    def analyze_frame(self, frame, cam_name):
        if cam_name == "CAM 3":
            if self.zoom_mode:
                h, w = frame.shape[:2]
                crop = frame[h//4:3*h//4, w//4:3*w//4]
                try:
                    frame = cv2.resize(crop, (w, h))
                except:
                    pass
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                frame = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

            zone = self.restricted_zone
            cv2.rectangle(frame, (zone[0], zone[1]), (zone[2], zone[3]), (0, 0, 255), 2)

            # Run recognition
            frame, results = self.attendance_system.process_frame(frame)
            if results:
                for _, name in results:
                    self.add_log(f"CAM 3: Face detected → {name}")

                    # check restricted zone
                    for (x, y, w, h) in self.attendance_system.last_faces:
                        face_box = (x, y, x+w, y+h)
                        if self.box_overlap(face_box, zone):
                            # 🔊 Play alarm only if face is in restricted zone
                            if os.path.exists(ALARM_FILE) and not self.alarm_playing:
                                self.alarm_playing = True
                                winsound.PlaySound(ALARM_FILE, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)

                            ts = int(time.time())
                            snap_file = os.path.join(ALERT_DIR, f"alert_{ts}.png")
                            Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).save(snap_file)
                            self.add_log(f"⚠️ ALERT: {name} entered restricted zone (snapshot saved)")

            label = f"{cam_name} - {CAM_NAMES.get(cam_name,'')}"
            cv2.putText(frame, label, (20, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 255, 0), 2)
            return frame
        else:
            f = np.zeros_like(frame) + 40
            label = f"{cam_name} - {CAM_NAMES.get(cam_name,'')}"
            cv2.putText(f, label, (20, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 165, 255), 2)
            cv2.putText(f, "(NO SIGNAL)", (50, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
            return f

    # ---------------- Main loop ----------------
    def update_loop(self):
        if not self._running:
            return
        ret, frame = self.cap.read()
        if not ret:
            blank = np.zeros((540,960,3), dtype=np.uint8) + 30
            final = blank
        else:
            cam_frame = cv2.resize(frame, (640, 480))

            if self.mode == "quad":
                cams = []
                for cam_name in ["CAM 1", "CAM 2", "CAM 3", "CAM 4"]:
                    f = self.analyze_frame(cam_frame.copy(), cam_name)
                    f = cv2.resize(f, (480, 360))
                    cams.append(f)

                top_row = np.hstack((cams[0], cams[1]))
                bottom_row = np.hstack((cams[2], cams[3]))
                final = np.vstack((top_row, bottom_row))

            elif self.mode in CAM_NAMES:
                f = self.analyze_frame(cv2.resize(cam_frame, (960,720)), self.mode)
                final = f
            else:
                blank = np.zeros((720,960,3), dtype=np.uint8) + 40
                cv2.putText(blank, f"{self.mode} - NO SIGNAL", (200,360),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0,0,255), 3)
                final = blank

        rgb = cv2.cvtColor(final, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        self.last_frame = img
        imgtk = ImageTk.PhotoImage(image=img)
        self.canvas_label.imgtk = imgtk
        self.canvas_label.configure(image=imgtk)

        self.root.after(30, self.update_loop)

    def on_close(self):
        self._running = False
        try:
            self.cap.release()
        except:
            pass
        winsound.PlaySound(None, winsound.SND_PURGE)
        self.root.destroy()

# ---------------------------
# Run app
# ---------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = FaceGuardApp(root)
    root.mainloop()
