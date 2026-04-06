import cv2
import os
import numpy as np
from PIL import Image

# Path for the dataset images
path = 'dataset'

# Initialize the LBPH face recognizer
recognizer = cv2.face.LBPHFaceRecognizer_create()
# Initialize the face detector for cropping faces from images
detector = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")

def getImagesAndLabels(path):
    """
    Reads image paths from the dataset directory, extracts face samples,
    and returns a list of faces and their corresponding user IDs.
    """
    imagePaths = [os.path.join(path, f) for f in os.listdir(path)]
    faceSamples = []
    ids = []

    for imagePath in imagePaths:
        # Open image and convert to grayscale
        PIL_img = Image.open(imagePath).convert('L')
        # Convert PIL image to a NumPy array
        img_numpy = np.array(PIL_img, 'uint8')

        # Get the ID from the filename (e.g., "User.101.1.jpg" -> 101)
        id = int(os.path.split(imagePath)[-1].split(".")[1])

        # Detect faces in the grayscale image
        faces = detector.detectMultiScale(img_numpy)

        # Loop through detected faces and add them to the lists
        for (x, y, w, h) in faces:
            faceSamples.append(img_numpy[y:y + h, x:x + w])
            ids.append(id)

    return faceSamples, ids

print("\n [INFO] Training faces. It will take a few seconds ...")
# Get the training data
faces, ids = getImagesAndLabels(path)

# Train the recognizer with the data
recognizer.train(faces, np.array(ids))

# Save the trained model to a file
recognizer.write('trainer.yml')

# Print completion message
print("\n [INFO] {0} faces trained. Exiting Program".format(len(np.unique(ids))))