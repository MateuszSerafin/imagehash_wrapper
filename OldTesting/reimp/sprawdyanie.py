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
        if(hash_func == imagehash.colorhash):
            hashes.append(hash_func(bounding_box, binbits=8))
        else:
            hashes.append(hash_func(bounding_box, hash_size=8))
    # Show bounding box
    # im_segment = image.copy()
    # for pix in segment:
    #   im_segment.putpixel(pix[::-1], 255)
    # im_segment.show()
    # bounding_box.show()

    return imagehash.ImageMultiHash(hashes)


def load(file, arr, extension):
    file = bz2.BZ2File(file + f""".bz28x300{extension}""", 'rb')
    try:
        while True:
            arr.extend(pickle.load(file))
    except (EOFError):
        pass
    file.close()

lista = []


file = "Rick and Morty S02E02 Mortynight Run.mp4"
load(file, lista, "phash")


def warcrime(file):
    fileint = int(os.path.basename(file).split(".")[0])
    frame = PIL.Image.open("zapis/{}".format(file))

    ahash = crop_resistant_hash(frame, hash_func=imagehash.average_hash)
    p_hash = crop_resistant_hash(frame, hash_func=imagehash.phash)
    p_hash_simple = crop_resistant_hash(frame, hash_func=imagehash.phash_simple)

    d_hash = crop_resistant_hash(frame, hash_func=imagehash.dhash)
    d_hash_vert = crop_resistant_hash(frame, hash_func=imagehash.dhash_vertical)
    w_hash = crop_resistant_hash(frame, hash_func=imagehash.whash)
    colorhash = crop_resistant_hash(frame, hash_func=imagehash.colorhash)

    return (ahash, p_hash, p_hash_simple, d_hash, d_hash_vert, w_hash, colorhash, fileint)




def worker(org, compareto, metadata: dict):

    diff = []
    for hashe in compareto:
        bruhmomentos = hashe[metadata["index"]].best_match(org)
        diff.append((abs(hashe[-1] - org.index(bruhmomentos)), hashe[metadata["index"]].hash_diff(bruhmomentos)))

    return (diff, metadata["enc"])



def workertoredable(worker):
    zus = 0
    for a in worker[0]:
        diff = a[0]
        if(diff < 400):
            zus += 1

    return "Zus: " + str(zus) + " " + worker[1]

zus = 0

letrollmoment = []

for file in os.listdir("zapis"):
    if(".png" not in file): continue

    crime = warcrime(file)
    letrollmoment.append(crime)
    print(len(letrollmoment))

print(workertoredable(worker(lista, letrollmoment, {"index": 1, "enc": "png"})))

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