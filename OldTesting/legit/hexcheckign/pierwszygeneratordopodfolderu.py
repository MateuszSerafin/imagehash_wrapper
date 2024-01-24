import bz2
import multiprocessing
import pickle

import PIL
import imagehash
import cv2
import os

import numpy
import psutil
import time

from PIL import ImageFilter
#TO JEST PEIRWSZY GENERATOR ON GENERUJE DO VIDEOS/.MP4 czyli sie robi bulder prawidlowy to jest wyzej generation.py z os.walkiem

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
    image = image.convert("L").resize((segmentation_image_size, segmentation_image_size), imagehash.ANTIALIAS)
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

def process(frames):
    b20its = []
    for framerog in frames:
        frame = PIL.Image.fromarray(framerog[0])

        cropp_resistant = crop_resistant_hash(frame)
        only_phash = imagehash.phash(frame, hash_size=8)

        b20its.append((cropp_resistant, only_phash, framerog[1]))
    print("Done one task of {}".format(len(frames)))
    return b20its


def save(fileorg, what):
    file = None
    if(not os.path.exists(os.path.basename(fileorg) + f""".bz28withresistant""")):
        file = bz2.BZ2File(os.path.basename(fileorg) + f""".bz28withresistant""", 'wb')
    else:
        file = bz2.BZ2File(os.path.basename(fileorg) + f""".bz28withresistant""", 'ab')
    pickle.dump(what, file)
    file.close()
def savebuttask(file, task):
    save(file,task.get())

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
            while (psutil.virtual_memory().available / 1024 / 1024 < 7000):
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
    multiprocessing.set_start_method('forkserver')
    pool = multiprocessing.Pool(16, maxtasksperchild=4)
    for dir in os.listdir():
        if(not os.path.isdir(dir)): continue
        print(dir)
        for file in os.listdir(dir):
            if("png" in file): continue
            if(os.path.exists(file + ".bz28withresistant")):
                print(file, "exists")
                continue
            processfile(pool, os.path.join(dir, file))
