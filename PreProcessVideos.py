import bz2
import multiprocessing
import pickle
import PIL
import imagehash
import cv2
import os
import psutil
import time

class custom_hash_func:
    #play around with bits but 8 is enough
    #it's only there because i want to adjust size without changing the actual function behind it.
    def __init__(self, hashfunc, bits=8):
        self.hash_func = hashfunc
        self.bits = bits

    def __call__(self, *args, **kwargs):
        return self.hash_func(*args, hash_size=self.bits)

def process(frames):
    b20its = []
    #frame (image) and also what frame number it is.
    for framerog in frames:
        frame = PIL.Image.fromarray(framerog[0])
        cropp_resistant = imagehash.crop_resistant_hash(frame, hash_func=custom_hash_func(imagehash.phash))
        b20its.append((cropp_resistant, framerog[1]))
    print("Done one task of {}".format(len(frames)))
    return b20its


def save(fileorg, what, save_dir):
    file = None
    if(not os.path.exists(os.path.join(save_dir, os.path.basename(fileorg) + f""".bz2"""))):
        file = bz2.BZ2File(os.path.join(save_dir, os.path.basename(fileorg) + f""".bz2"""), 'wb')
    else:
        file = bz2.BZ2File(os.path.join(save_dir, os.path.basename(fileorg) + f""".bz2"""), 'ab')
    pickle.dump(what, file)
    file.close()

def savebuttask(file, task, save_dir):
    save(file,task.get(), save_dir)


def processfile(pool, file, save_dir):
    video_capture = cv2.VideoCapture(file)

    frames = []
    tasks = []

    fps = 0

    counter = 8
    deleted = 0

    while video_capture.isOpened():
        ret, frame = video_capture.read()
        if not ret:
            break
        #amount of frames to skip
        if(counter > 7):
            while (psutil.virtual_memory().available / 1024 / 1024 < 7000):
                for task in tasks[:]:
                    if (task.ready()):
                        savebuttask(file, task, save_dir)
                        tasks.remove(task)
                        deleted += 1

                print("sleeping cus of memory ", len(tasks) + deleted)
                time.sleep(10)

            if (len(frames) > 40):
                tasks.append(pool.apply_async(process, args=[frames.copy(), ]))
                print("apeddnign additional tasks to queue current queue size {}", len(tasks) + deleted)
                frames.clear()
            else:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append((frame_rgb, fps))

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
        savebuttask(file, task, save_dir)
        tasks.remove(task)

if __name__=="__main__":
    multiprocessing.set_start_method('forkserver')
    pool = multiprocessing.Pool(16, maxtasksperchild=4)

    videos_dir = "videos"
    process_save_dir = "processed"

    if(not os.path.exists(videos_dir)):
        os.mkdir(videos_dir)
    if(not os.path.exists(process_save_dir)):
        os.mkdir(process_save_dir)


    for dir in os.listdir(videos_dir):
        joined = os.path.join(videos_dir, dir)
        if(not os.path.isdir(joined)): continue
        for file in os.listdir(joined):
            movie = os.path.join(joined, file)
            processfile(pool, movie, process_save_dir)
