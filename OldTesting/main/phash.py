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
    b20its = []
    for frame in frames:
        frame = PIL.Image.fromarray(frame)
        b20its.append(crop_resistant_hash(frame, hash_func=imagehash.phash))
    print("Done one task of {}".format(len(frames)))
    return b20its

def crop_resistant_hash(
        image,
        hash_func=None,
        limit_segments=None,
        segment_threshold=128,
        min_segment_size=500,
        segmentation_image_size=300
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
        hashes.append(hash_func(bounding_box, hash_size=8))
    # Show bounding box
    # im_segment = image.copy()
    # for pix in segment:
    #   im_segment.putpixel(pix[::-1], 255)
    # im_segment.show()
    # bounding_box.show()

    return imagehash.ImageMultiHash(hashes)


def processfile(pool, file):
    video_capture = cv2.VideoCapture(file)

    frames = []
    tasks = []
    counter = 0
    frame_counter = 0

    while video_capture.isOpened():
        counter += 1
        ret, frame = video_capture.read()

        if not ret:
            break

        while(psutil.virtual_memory().available/1024/1024 < 5000):
            print("sleeping cus of memory ", len(tasks))
            time.sleep(10)

        if(len(frames) > 40):
            tasks.append(pool.apply_async(process, args=[frames.copy(),]))
            print("apeddnign additional tasks to queue current queue size {}", len(tasks))
            frames.clear()
        else:
            frames.append(frame)
        frame_counter += 1


    if(len(frames) != 0): tasks.append(pool.apply_async(process, args=[frames.copy()]))

    frames.clear()

    tojson = []

    taskinfo = 0
    for task in tasks:
        taskinfo += 1
        task.wait()
        print("Processed videos, waiting for {} task out of {} tasks".format(taskinfo, len(tasks)))
        tojson.extend(task.get())

    ofile = bz2.BZ2File(os.path.basename(file)+'.bz2LEPSZY', 'wb')
    pickle.dump(tojson, ofile)
    ofile.close()

    video_capture.release()

if __name__=="__main__":
    multiprocessing.set_start_method('forkserver')
    pool = multiprocessing.Pool(16)
    processfile(pool, "Rick and Morty Season 2 S02 1080p BDRip [HEVC AAC] - SEPH1/Rick and Morty S02E02 Mortynight Run.mp4")
