import cv2
import os

# --- Step 1: Initialize webcam and face detector ---
face_detector = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
cam = cv2.VideoCapture(0)
cam.set(3, 640)  # width
cam.set(4, 480)  # height

# --- Step 2: Get user input and create dataset folder ---
face_id = input('\nEnter employee ID and press <enter>: ')
dataset_folder = 'dataset'
if not os.path.exists(dataset_folder):
    os.makedirs(dataset_folder)

print("\n[INFO] Initializing face capture. Look at the camera and wait...")

# --- Step 3: Capture and save images ---
count = 0
frame_skip = 5  # save one face every 5 frames
frame_counter = 0
max_images = 200  # number of images to capture per user

while True:
    ret, img = cam.read()
    if not ret:
        continue

    img = cv2.flip(img, 1)  # mirror image
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Detect faces
    faces = face_detector.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

    if len(faces) > 0:
        # Select the largest face
        largest_face = max(faces, key=lambda rect: rect[2]*rect[3])
        x, y, w, h = largest_face

        # Draw rectangle around the face
        cv2.rectangle(img, (x, y), (x+w, y+h), (255, 0, 0), 2)

        # Save image every `frame_skip` frames
        if frame_counter % frame_skip == 0:
            count += 1
            face_img = gray[y:y+h, x:x+w]
            face_img = cv2.resize(face_img, (200, 200))  # standard size
            file_path = os.path.join(dataset_folder, f"User.{face_id}.{count}.jpg")
            cv2.imwrite(file_path, face_img)
            print(f"[INFO] Captured image {count}/{max_images}")

        frame_counter += 1

    # Show live video
    cv2.imshow('Face Capture', img)

    # Stop on ESC key or when max_images reached
    k = cv2.waitKey(10) & 0xff
    if k == 27 or count >= max_images:
        break

# --- Step 4: Cleanup ---
print("\n[INFO] Finished capturing. Cleaning up...")
cam.release()
cv2.destroyAllWindows()
