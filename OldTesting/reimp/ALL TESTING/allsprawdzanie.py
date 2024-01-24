import bz2
import multiprocessing
import os
import pickle

import PIL
import imagehash
import numpy
from PIL import ImageFilter



def loadBETTER(file, arr, extension):
    file = bz2.BZ2File(file + f""".bz2128x900{extension}""", 'rb')
    try:
        while True:
            loaded = pickle.load(file)

            for multi in loaded:
                for segment in multi.segment_hashes:
                    segment.hash = segment.hash.astype('bool')

            arr.extend(loaded)
    except (EOFError):
        pass
    file.close()


def load(file, arr, extension):
    file = bz2.BZ2File(file + f""".bz2128x900{extension}""", 'rb')
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




def tasktoreadable(task):
    zus = 0
    get = task.get()
    for a in get[0]:
        diff = a[0]
        if(diff < 200):
            zus += 1

    return "Zus: " + str(zus) + " " + get[1]

def workertoredable(worker):
    zus = 0
    for a in worker[0]:
        diff = a[0]
        if(diff < 200):
            zus += 1

    return "Zus: " + str(zus) + " " + worker[1]

if __name__=="__main__":
    file = "Rick and Morty S02E02 Mortynight Run.mp4"
    a_hash = []
    p_hash = []
    p_hash_simple = []
    d_hash = []
    d_hash_vert = []
    w_hash = []
    colorhash = []

    #load(file, a_hash, "ahash")
    load(file, p_hash, "phash")
    #load(file, p_hash_simple, "psimple")
    #load(file, d_hash, "dhash")
    #load(file, d_hash_vert, "dhashvert")
    #load(file, w_hash, "whash")
    #load(file, colorhash, "chash")


    #print("A hash: ",len(a_hash))
    print("p hash: ",len(p_hash))
    #print("p simple hash: ",len(p_hash_simple))
    #print("d hash: ",len(d_hash))
    #print("d vert hash: ",len(d_hash_vert))
    #print("w hash: ",len(w_hash))
    #print("color hash: ",len(colorhash))



    png_hash = []
    jpeg_hash = []
    webp_hash = []

    for file in os.listdir("zapis"):
        print(file)
        if(".png" in file):
            crime = warcrime(file)
            png_hash.append(crime)
            continue
        if(".jpeg" in file):
            continue
            crime = warcrime(file)
            jpeg_hash[crime[-1]] = crime
            continue
        if(".webp" in file):
            continue
            crime = warcrime(file)
            webp_hash[crime[-1]] = crime
            continue

    multiprocessing.set_start_method('forkserver')
    pool = multiprocessing.Pool(16)

    print("going")


    #a_task = pool.apply_async(worker, args=[a_hash, png_hash, {"index": 0, "enc":"png"}])
    p_task = pool.apply_async(worker, args=[p_hash, png_hash, {"index": 1, "enc": "png"}])
    #p_sim_task = pool.apply_async(worker, args=[p_hash_simple, png_hash, {"index": 2, "enc": "png"}])
    #d_hash_task = pool.apply_async(worker, args=[d_hash,png_hash, {"index": 3, "enc": "png"}])
    #d_hash_vert_task = pool.apply_async(worker, args=[d_hash_vert, png_hash, {"index": 4, "enc": "png"}])
    #w_hash_task = pool.apply_async(worker, args=[w_hash, png_hash, {"index": 5, "enc": "png"}])
    #colorhash_task = pool.apply_async(worker, args=[colorhash, png_hash, {"index": 6, "enc": "png"}])


    #print(tasktoreadable(a_task))
    print(tasktoreadable(p_task))
    #print(tasktoreadable(p_sim_task))
    #print(tasktoreadable(d_hash_task))
    #print(tasktoreadable(d_hash_vert_task))
    #print(tasktoreadable(w_hash_task))
    #print(tasktoreadable(colorhash_task))