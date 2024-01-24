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


def process(frames):
    try:
        a_hash = []
        p_hash = []
        p_hash_simple = []
        d_hash = []
        d_hash_vert = []
        w_hash = []
        colorhash = []
        for frame in frames:
            frame = PIL.Image.fromarray(frame)

            a_hash.append(crop_resistant_hash(frame, hash_func=imagehash.average_hash))
            p_hash.append(crop_resistant_hash(frame, hash_func=imagehash.phash))
            p_hash_simple.append(crop_resistant_hash(frame, hash_func=imagehash.phash_simple))

            d_hash.append(crop_resistant_hash(frame, hash_func=imagehash.dhash))
            d_hash_vert.append(crop_resistant_hash(frame, hash_func=imagehash.dhash_vertical))
            w_hash.append(crop_resistant_hash(frame, hash_func=imagehash.whash))
            colorhash.append(crop_resistant_hash(frame, hash_func=imagehash.colorhash))

        print("Done one task of {}".format(len(frames)))

        done = [a_hash, p_hash, p_hash_simple, d_hash, d_hash_vert, w_hash, colorhash]

        for hashtype in done:
            for multi in hashtype:
                for segment in multi.segment_hashes:
                    segment.hash = segment.hash.astype('bool')

        return done
    except Exception as e:
        print(e)

def crop_resistant_hash(
        image,
        hash_func=None,
        limit_segments=None,
        segment_threshold=128,
        min_segment_size=500,
        segmentation_image_size=900
):
    if hash_func is None:
        hash_func = imagehash.phash

    orig_image = image.copy()
    # Convert to gray scale and resize
    image = image.convert("L").resize((segmentation_image_size, segmentation_image_size), PIL.Image.ANTIALIAS)
    # Add filters
    image = image.filter(ImageFilter.GaussianBlur()).filter(ImageFilter.MedianFilter())
    pixels = numpy.array(image).astype(numpy.float32)

    segments = imagehash._find_all_segments(pixels, segment_threshold, min_segment_size)

    # If there are no segments, have 1 segment including the whole image
    if not segments:
        full_image_segment = {(0, 0), (segmentation_image_size-1, segmentation_image_size-1)}
        segments.append(full_image_segment)

    # If segment limit is set, discard the smaller segments
    if limit_segments:
        segments = sorted(segments, key=lambda s: len(s), reverse=True)[:limit_segments]

    # Create bounding box for each segment
    hashes = []
    for segment in segments:
        orig_w, orig_h = orig_image.size
        scale_w = float(orig_w) / segmentation_image_size
        scale_h = float(orig_h) / segmentation_image_size
        min_y = min(coord[0] for coord in segment) * scale_h
        min_x = min(coord[1] for coord in segment) * scale_w
        max_y = (max(coord[0] for coord in segment)+1) * scale_h
        max_x = (max(coord[1] for coord in segment)+1) * scale_w
        # Compute robust hash for each bounding box
        bounding_box = orig_image.crop((min_x, min_y, max_x, max_y))
        if(hash_func == imagehash.colorhash):
            hashes.append(hash_func(bounding_box, binbits=128))
        else:
            hashes.append(hash_func(bounding_box, hash_size=128))
    # Show bounding box
    # im_segment = image.copy()
    # for pix in segment:
    #   im_segment.putpixel(pix[::-1], 255)
    # im_segment.show()
    # bounding_box.show()

    return imagehash.ImageMultiHash(hashes)

def save(fileorg, what, name):
    file = None
    if(not os.path.exists(os.path.basename(fileorg) + f""".bz2128x900{name}""")):
        file = bz2.BZ2File(os.path.basename(fileorg) + f""".bz2128x900{name}""", 'wb')
    else:
        file = bz2.BZ2File(os.path.basename(fileorg) + f""".bz2128x900{name}""", 'ab')
    pickle.dump(what, file)
    file.close()

def savebuttask(file, task):
    a, p, p_sim, d, d_v, w, c = task.get()
    save(file, a, "ahash")
    save(file, p, "phash")
    save(file, p_sim, "psimple")
    save(file, d, "dhash")
    save(file, d_v, "dhashvert")
    save(file, w, "whash")
    save(file, c, "chash")


def processfile(pool, file):
    video_capture = cv2.VideoCapture(file)

    frames = []
    tasks = []
    counter = 0
    frame_counter = 0
    deleted = 0

    while video_capture.isOpened():
        counter += 1
        ret, frame = video_capture.read()

        if not ret:
            break

        while(psutil.virtual_memory().available/1024/1024 < 10000):
            for task in tasks[:]:
                if(task.ready()):
                    savebuttask(file, task)
                    tasks.remove(task)
                    deleted += 1

            print("sleeping cus of memory ", len(tasks) + deleted)
            time.sleep(10)

        if(len(frames) > 40):
            tasks.append(pool.apply_async(process, args=[frames.copy(),]))
            print("apeddnign additional tasks to queue current queue size {}", len(tasks) + deleted)
            frames.clear()
        else:
            frames.append(frame)
        frame_counter += 1


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
    multiprocessing.set_start_method('forkserver')
    pool = multiprocessing.Pool(32, maxtasksperchild=1)
    processfile(pool, "Rick and Morty S02E02 Mortynight Run.mp4")
