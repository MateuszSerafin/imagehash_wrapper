import bz2
import datetime
import os
import pickle

import PIL.Image
import imagehash
import bz2
import collections
import json
import multiprocessing
import pickle
import random
import sys
import cv2
import PIL
import imagehash
import numpy
import os
import psutil
from PIL import ImageFilter
import time

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
        hashes.append(hash_func(bounding_box, hash_size=40))
    # Show bounding box
    # im_segment = image.copy()
    # for pix in segment:
    #   im_segment.putpixel(pix[::-1], 255)
    # im_segment.show()
    # bounding_box.show()

    return imagehash.ImageMultiHash(hashes)

names = []
lista = []

for file in os.listdir():
    if(not file.endswith(".bz2LEPSZY")): continue
    lista.extend(pickle.load(bz2.BZ2File(file, 'rb')))
    names.append(file)


zus = 0
for rand in random.sample(range(0,30000),100):
    other_hash = lista[rand]
    bruhmomentos = other_hash.best_match(lista)
    if abs(rand - lista.index(bruhmomentos)) < 200:
        print(other_hash.hash_diff(bruhmomentos))
        zus += 1
print("ZUS : ", zus)

'''
    if lista.index(other_hash.best_match(lista)) >= fileint + 50 or lista.index(other_hash.best_match(lista)) >= fileint - 50:
        print("git")
        continue
    print("nie git")

for vid in list:
    for imghash in vid:
        if(other_hash.matches(imghash, bit_error_rate=0.50)):
            baaasdasdas = datetime.timedelta(seconds=(vid.index(imghash)*3)/30)

            print("VID {} : INDEX: {}".format(names[list.index(vid)], baaasdasdas))
'''