import cv2
import os
import sqlite3
import numpy as np
from PIL import Image

detector = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
recognizer = cv2.face.LBPHFaceRecognizer_create()


# Create a connection witn databse
conn = sqlite3.connect('facedb')
if conn != 0:
    print("Connection Successful")
else:
    print('Connection Failed')
    exit()

# Creating table if it doesn't already exists
conn.execute('''create table if not exists facedata ( id int primary key, name char(20) not null)''')

class FaceRecognition:    

    def faceDetect(Entry1, Entry2):
        face_id = Entry1
        face_name = Entry2
        try:
            conn.execute('''insert into facedata values ( ?, ?)''', (face_id, face_name))
            conn.commit()
        except sqlite3.IntegrityError:
            print("\n ERROR! This id alreeady exists in database!")
            print("\n Try agian with new id\n")
            exit()
        cam = cv2.VideoCapture(0)
        

        count = 0

        while(True):

            ret, img = cam.read()
            # img = cv2.flip(img, -1) # flip video image vertically
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = detector.detectMultiScale(gray, 1.3, 5)

            for (x,y,w,h) in faces:

                cv2.rectangle(img, (x,y), (x+w,y+h), (255,0,0), 2)
                count += 1

                # Save the captured image into the datasets folder
                cv2.imwrite("dataset/User." + str(face_id) + '.' + str(count) + ".jpg", gray[y:y+h,x:x+w])

                cv2.imshow('image', img)

            k = cv2.waitKey(100) & 0xff # Press 'ESC' for exiting video
            if k == 27:
                break
            elif count >= 30: # Take 30 face sample and stop video
                break
    
    
        cam.release()
        cv2.destroyAllWindows()

    
    def trainFace(self):
        # Path for face image database
        path = 'dataset'

        # function to get the images and label data
        def getImagesAndLabels(path):

            imagePaths = [os.path.join(path,f) for f in os.listdir(path)]     
            faceSamples=[]
            ids = []

            for imagePath in imagePaths:

                PIL_img = Image.open(imagePath).convert('L') # convert it to grayscale
                img_numpy = np.array(PIL_img,'uint8')

                id = int(os.path.split(imagePath)[-1].split(".")[1])
                faces = detector.detectMultiScale(img_numpy)

                for (x,y,w,h) in faces:
                    faceSamples.append(img_numpy[y:y+h,x:x+w])
                    ids.append(id)

            return faceSamples,ids

        print ("\n Training faces. It will take a few seconds. Wait ...")
        faces,ids = getImagesAndLabels(path)
        recognizer.train(faces, np.array(ids))

        # Save the model into trainer/trainer.yml
        recognizer.save('trainer/trainer.yml') # recognizer.save() worked on Mac, but not on Pi

        # Print the numer of faces trained and end program
        print("\n {0} faces trained. Exiting Program".format(len(np.unique(ids))))


    def recognizeFace(self):
        recognizer.read('trainer/trainer.yml')
        cascadePath = "haarcascade_frontalface_default.xml"
        faceCascade = cv2.CascadeClassifier(cascadePath)

        font = cv2.FONT_HERSHEY_SIMPLEX

        #iniciate id counter
        id = 0

        names = ['None']

        # Retriving names from database
        data = conn.execute('''select * from facedata''')
        for x in data:
            names.append(x[1]) 

        # Initialize and start realtime video capture
        cam = cv2.VideoCapture(0)

        # Define min window size to be recognized as a face
        minW = 0.1*cam.get(3)
        minH = 0.1*cam.get(4)

        while True:

            ret, img =cam.read()

            gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

            faces = faceCascade.detectMultiScale( 
                gray,
                scaleFactor = 1.2,
                minNeighbors = 5,
                minSize = (int(minW), int(minH)),
            )

            for(x,y,w,h) in faces:

                cv2.rectangle(img, (x,y), (x+w,y+h), (0,255,0), 2)

                id, confidence = recognizer.predict(gray[y:y+h,x:x+w])

                # Check if confidence is less then 100 ==> "0" is perfect match 
                if (confidence < 100):
                    id = names[id]
                    confi = "  {0}%".format(round(100 - confidence))
                else:
                    id = "unknown"
                    confi = "  {0}%".format(round(100 - confidence))
                
                cv2.putText(img, str(id), (x+5,y-5), font, 1, (255,255,255), 2)
                cv2.putText(img, str(confi), (x+5,y+h-5), font, 1, (255,255,0), 1)  
            
            cv2.imshow('camera',img) 

            k = cv2.waitKey(10) & 0xff # Press 'ESC' for exiting video
            if k == 27:
                break
            if confidence > 50:
                break

        print("\n Exiting Program")
        cam.release()
        cv2.destroyAllWindows()

        return str(id)