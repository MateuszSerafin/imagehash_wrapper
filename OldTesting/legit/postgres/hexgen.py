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
import psycopg2 as psycopg2
from PIL import ImageFilter
import time


def process(frames):
    b20its = []
    for framerog in frames:
        frame = PIL.Image.fromarray(framerog[0])
        b20its.append((imagehash.phash(frame, hash_size=8), framerog[1]))
    print("Done one task of {}".format(len(frames)))
    return b20its


def save(fileorg, what):
    for imghashed in what:
        imgHash = str(imghashed[0])
        hashInt = twos_complement(imgHash, 64)  # convert from hexadecimal to 64 bit signed integer
        cursor.execute("INSERT INTO hashes(hash, frame, file) VALUES (%s, %s, %s)", (hashInt, imghashed[1],fileorg))
        conn.commit()
        print(f"added image with hash to database")

def savebuttask(file, task):
    save(file,task.get())

def twos_complement(hexstr, bits):
    value = int(hexstr, 16)  # convert hexadecimal to integer

    # convert from unsigned number to signed number with "bits" bits
    if value & (1 << (bits - 1)):
        value -= 1 << bits
    return value

conn = None
cursor = None

def processfile(pool, file):
    video_capture = cv2.VideoCapture(file)

    frames = []
    tasks = []

    fps = 0

    counter = 4
    deleted = 0

    while video_capture.isOpened():
        ret, frame = video_capture.read()
        if not ret:
            break
        if(counter > 3):
            while (psutil.virtual_memory().available / 1024 / 1024 < 10000):
                for task in tasks[:]:
                    if (task.ready()):
                        savebuttask(file, task)
                        tasks.remove(task)
                        deleted += 1

                print("sleeping cus of memory ", len(tasks) + deleted)
                time.sleep(10)

            if (len(frames) > 40):
                tasks.append(pool.apply_async(process, args=[frames.copy(), ]))
                print("apeddnign additional tasks to queue current queue size {}", len(tasks) + deleted)
                frames.clear()
            else:
                frames.append((frame, fps))

            counter = 0
        fps += 1
        counter += 1


    if(len(frames) != 0): tasks.append(pool.apply_async(process, args=[frames.copy()]))

    frames.clear()
    video_capture.release()

    taskinfo = 0
    for task in tasks[:]:
        taskinfo += 1
        task.wait()
        print("Processed videos, waiting for {} task out of {} tasks".format(taskinfo, len(tasks)))
        savebuttask(file, task)
        tasks.remove(task)

if __name__=="__main__":

    conn = psycopg2.connect(database="postgres", user="postgres", password="Iksde2137!", host="172.17.0.2")
    cursor = conn.cursor()

    multiprocessing.set_start_method('forkserver')
    pool = multiprocessing.Pool(16, maxtasksperchild=4)
    for dir in os.listdir():
        if(not os.path.isdir(dir)): continue
        print(dir)
        for file in os.listdir(dir):
            if(os.path.exists(file + ".bz2")):
                print(file, "exists")
                continue
            processfile(pool, os.path.join(dir, file))
