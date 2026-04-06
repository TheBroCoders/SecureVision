import cv2

class AttendanceSystem:
    def __init__(self, trainer_file, cascade_file, id_to_name_map):
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.recognizer.read(trainer_file)
        self.face_cascade = cv2.CascadeClassifier(cascade_file)
        self.id_to_name = id_to_name_map
        self.last_faces = []  # will hold bounding boxes for last frame

    def process_frame(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)

        results = []
        self.last_faces = []   # reset list for this frame

        for (x, y, w, h) in faces:
            self.last_faces.append((x, y, w, h))   # store face box

            id_, conf = self.recognizer.predict(gray[y:y+h, x:x+w])
            if conf < 70:  # recognized
                name = self.id_to_name.get(id_, "Unknown")
                results.append(("Authorized", name))
                color = (0, 255, 0)
            else:  # not recognized
                name = "Unknown"
                results.append(("Unauthorized", name))
                color = (0, 0, 255)

            # Draw rectangle + label
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            cv2.putText(frame, name, (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        return frame, results
