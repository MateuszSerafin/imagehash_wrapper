import bz2
import multiprocessing
import os
import pickle
from functools import reduce

import PIL
import imagehash
import numpy
from PIL import ImageFilter


def load(file, arr, ):
    file = open(file, 'rb')
    try:
        while True:
            arr.extend(pickle.load(file))
    except (EOFError):
        pass
    file.close()


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
        full_image_segment = {(0, 0), (segmentation_image_size - 1, segmentation_image_size - 1)}
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
        max_y = (max(coord[0] for coord in segment) + 1) * scale_h
        max_x = (max(coord[1] for coord in segment) + 1) * scale_w
        # Compute robust hash for each bounding box
        bounding_box = orig_image.crop((min_x, min_y, max_x, max_y))
        hashes.append(hash_func(bounding_box, hash_size=32))
    # Show bounding box
    # im_segment = image.copy()
    # for pix in segment:
    #   im_segment.putpixel(pix[::-1], 255)
    # im_segment.show()
    # bounding_box.show()

    return imagehash.ImageMultiHash(hashes)


def worker(tocompare, mainarr):
    howmucprocessed = 0

    misses = 0

    bruh = 0

    above500matches = 0

    maximum = 0

    minimum = 9999



    for tobecompared in tocompare:
        best_match = tobecompared[0].best_match(mainarr)

        after = ".".join(best_match.file.split(".")[:-1])
        afterfile = ".".join(tobecompared[2].split(".")[:-2])

        if (not (after == afterfile)):
            misses += 1

        diffinindex = abs(int(best_match.internal) - int(tobecompared[2].split(".")[-2]))

        if (diffinindex < minimum):
            minimum = diffinindex
        if (diffinindex > maximum):
            maximum = diffinindex


        if(diffinindex > 500):
            above500matches += 1

        else:
            bruh += diffinindex
            howmucprocessed += 1

    return (howmucprocessed, misses, bruh, maximum, minimum, above500matches)


if __name__ == "__main__":
    multiprocessing.set_start_method('forkserver')
    pool = multiprocessing.Pool(8)

    tocompare = pickle.load(bz2.BZ2File("ZDJECIA.BZ28", 'rb'))

    mainarr = []


    print("Readed zdjecia bz2")

    for file in os.listdir("8multihash"):
        print("Reading {}".format(file))

        internal = 0;
        filebz2 = bz2.BZ2File("8multihash/{}".format(file))

        try:
            while True:
                for encoding in pickle.load(filebz2):
                    enc = encoding[0]
                    enc.internal = internal
                    enc.file = file
                    mainarr.append(enc)
                    internal += 4
        except Exception as e:
            print(e)

    print("Size of main arr: " + str(len(mainarr)))
    print("Finished reading processing...")


    howmucprocessed = 0

    misses = 0

    bruh = 0

    maximum = 0

    minimum = 9999;


    taskable = []

    tasks = []

    for i in tocompare:
        taskable.append(i)
        if(len(taskable) > 10):
            tasks.append(pool.apply_async(worker, args=[taskable.copy(), mainarr.copy()]))
            taskable.clear()
    if(len(taskable) != 0):
        tasks.append(pool.apply_async(worker, args=[taskable.copy(), mainarr.copy()]))


    howmucprocessed = 0

    misses = 0

    bruh = 0

    maximum = 0

    minimum = 9999;

    above5000matches = 0

    for task in tasks:
        h, m, b, ax, mx, abv500 = task.get()
        howmucprocessed += h
        misses += m
        bruh += b
        above5000matches += abv500

        if (mx < minimum):
            minimum = mx
        if (ax > maximum):
            maximum = ax
        if(not howmucprocessed == 0 and not bruh == 0 and not above5000matches == 0):
            print("Current: ", howmucprocessed + above5000matches, " Misses: ", misses, "Avarage: ", bruh / howmucprocessed, " Max: ",
                  maximum, " Min: ", minimum, " Above 500matches:" + str(above5000matches))

"""
    for tobecompared in tocompare:
        best_match = tobecompared[0].best_match(mainarr)

        after = ".".join(best_match.file.split(".")[:-1])
        afterfile = ".".join(tobecompared[2].split(".")[:-2])

        if (not (after == afterfile)):
            misses += 1

        diffinindex = abs(int(best_match.internal) - int(tobecompared[2].split(".")[-2]))

        avarage += diffinindex

        if (diffinindex < minimum):
            minimum = diffinindex
        if (diffinindex > maximum):
            maximum = diffinindex

        howmucprocessed += 1
        print("Current: ", howmucprocessed, " Misses: ", misses, "Avarage: ", avarage / howmucprocessed, " Max: ",
              maximum, " Min: ", minimum)
"""