import cv2
import os
import numpy as np
from datetime import datetime

class AttendanceSystem:
    def __init__(self, trainer_file, cascade_file, id_to_name_map, log_file="attendance_log.csv"):
        """Initializes the face recognition system with all necessary components."""
        
        # Load the trained model and face cascade classifier
        try:
            self.recognizer = cv2.face.LBPHFaceRecognizer_create()
            self.recognizer.read(trainer_file)
        except cv2.error as e:
            print(f"Error loading trainer file '{trainer_file}': {e}")
            exit()
            
        try:
            self.face_cascade = cv2.CascadeClassifier(cascade_file)
            if self.face_cascade.empty():
                raise IOError("Could not load face cascade file.")
        except IOError as e:
            print(f"Error loading cascade file '{cascade_file}': {e}")
            exit()

        self.id_to_name = id_to_name_map
        self.log_file = log_file
        self.cam = None
        self.is_present = {}  # Tracks people currently in the frame to avoid redundant logging
        
        # Create the attendance log file if it doesn't exist
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w") as f:
                f.write("ID,Name,Timestamp,Status\n")

    def log_attendance(self, user_id, name, status):
        """Appends a new entry to the attendance log file."""
        with open(self.log_file, "a") as f:
            f.write(f"{user_id},{name},{datetime.now().strftime('%Y-%m-%d %H:%M:%S')},{status}\n")

    def run(self):
        """Starts the real-time face recognition loop."""
        self.cam = cv2.VideoCapture(0)
        if not self.cam.isOpened():
            print("Error: Could not open webcam.")
            return

        self.cam.set(3, 640)  # Set video width
        self.cam.set(4, 480)  # Set video height
        
        confidence_threshold = 70  # Lower is a better match

        print("Press 'q' to exit the system.")
        
        while True:
            ret, img = self.cam.read()
            if not ret:
                print("Failed to grab frame.")
                break
                
            img = cv2.flip(img, 1)  # Flip video frame for a natural view
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(100, 100))

            current_frame_ids = []

            for (x, y, w, h) in faces:
                # Predict the ID and confidence of the detected face
                id, confidence = self.recognizer.predict(gray[y:y+h, x:x+w])
                
                # Draw a rectangle around the face
                cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
                
                # Check if the confidence is good AND the ID exists in our map
                if confidence < confidence_threshold and id in self.id_to_name:
                    name = self.id_to_name[id]
                    box_color = (0, 255, 0)  # Green for authorized
                    
                    # Track recognized IDs in the current frame
                    current_frame_ids.append(id)
                    
                    # Log attendance only if the person just appeared
                    if not self.is_present.get(id, False):
                        print(f"Access Granted: {name}")
                        self.log_attendance(id, name, "Authorized")
                        self.is_present[id] = True
                else:
                    # This block handles both high confidence scores AND unknown IDs
                    name = "Unknown"
                    box_color = (0, 0, 255)  # Red for unauthorized
                
                    self.log_attendance("N/A", "Unknown", "Unauthorized")

                # Display name and confidence
                cv2.putText(img, f"Name: {name}", (x + 5, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, box_color, 2)
                cv2.putText(img, f"Conf: {round(100 - confidence, 2)}%", (x + 5, y + h + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, box_color, 2)
            
            # Update presence status for people who have left the frame
            for person_id in list(self.is_present.keys()):
                if person_id not in current_frame_ids and self.is_present[person_id]:
                    self.is_present[person_id] = False

            # Display the resulting frame
            cv2.imshow('Attendance System', img)
            
            # Exit loop on 'q' key press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    def cleanup(self):
        """Releases webcam and closes all windows."""
        if self.cam:
            self.cam.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    # --- Configuration ---
    # In a real application, this would come from a database.
    id_to_name_map = {
        101: "Arijeet Banerjee",
        102: "sangeet",
        103: "abhishek",
        104: "indrajit",
        105: "Security Team"
    }

    # Instantiate the system and run it
    system = AttendanceSystem(
        trainer_file='trainer.yml', 
        cascade_file='haarcascade_frontalface_default.xml', 
        id_to_name_map=id_to_name_map
    )
    
    try:
        system.run()
    finally:
        system.cleanup()