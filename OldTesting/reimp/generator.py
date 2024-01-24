import bz2
import collections
import json
import multiprocessing
import pickle
import random
import sys

import PIL
import imagehash
import cv2
import numpy
import os
import psutil
from PIL import ImageFilter
from PIL import Image
import time



if __name__=="__main__":
    video_capture = cv2.VideoCapture("/mnt/4tb/FILM/Rick and Morty Season 2 S02/Rick and Morty S02E02 Mortynight Run.mp4")
    lista = random.sample(range(1,30000),100)
    counter = 0
    while video_capture.isOpened():
        ret, frame = video_capture.read()
        if not ret:
            break
        if(counter in lista):
            PIL.Image.fromarray(frame).save("zapis/"+ str(counter)+".png","PNG")
        counter += 1
    video_capture.release()
