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
import time

def load(file, arr):
    file = bz2.BZ2File(file + f""".bz232x300""", 'rb')
    try:
        while True:
            arr.extend(pickle.load(file))
    except (EOFError):
        pass
    file.close()
if __name__ == "__main__":
    kurwa = []
    load("Rick and Morty S01E04 - M. Night Shaym-Aliens!.mp4", kurwa)
    print(len(kurwa))
    print(len(kurwa[0].segment_hashes[0].hash))
