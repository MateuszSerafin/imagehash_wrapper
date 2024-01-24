import multiprocessing
import os
import random

import PIL
import cv2
from PIL import Image


def findlengthofvid(fileloc):
    video_capture = cv2.VideoCapture(fileloc)
    counter = 0
    while video_capture.isOpened():
        ret, frame = video_capture.read()
        if not ret:
            break
        counter += 1
    return counter


def processfile(fileloc):
    print("Processing: ", fileloc)

    length = 30000 #too slow findlengthofvid(fileloc)
    print("Found length: ", length)


    video_capture = cv2.VideoCapture(fileloc)

    lista = random.sample(range(1,length),100)

    counter = 0;
    while video_capture.isOpened():
        ret, frame = video_capture.read()
        if not ret:
            break
        if(counter in lista):
            PIL.Image.fromarray(frame).save("zapis/"+ os.path.basename(fileloc) + "." +str(counter)+".png","PNG")
            #PIL.Image.fromarray(frame).save("zapis/"+ str(counter)+".jpeg","JPEG")
            #PIL.Image.fromarray(frame).save("zapis/"+ str(counter)+".webp","WebP")
            print(counter)
        counter += 1
    video_capture.release()

if __name__=="__main__":

    pool = multiprocessing.Pool(16)

    for dir in os.listdir():
        if(not os.path.isdir(dir)): continue
        print(dir)
        for file in os.listdir(dir):
            pool.apply_async(processfile, args=[os.path.join(dir, file)])
    pool.close()
    pool.join()
