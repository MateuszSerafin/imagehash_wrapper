import bz2
import concurrent.futures
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

def process(frames, save_as):
    processed = []
    #frame (image) and also what frame number it is.
    for framerog in frames:
        cropp_resistant8 = imagehash.crop_resistant_hash(framerog[0], hash_func=custom_hash_func(imagehash.phash, 8))
        #cropp_resistant12 = imagehash.crop_resistant_hash(frame, hash_func=custom_hash_func(imagehash.phash, 12))
        #cropp_resistant16 = imagehash.crop_resistant_hash(frame, hash_func=custom_hash_func(imagehash.phash, 16))
        processed.append((cropp_resistant8, framerog[1]))
    save(processed, save_as)
    return

def save(what, save_as):
    file = bz2.BZ2File(save_as, 'wb')
    pickle.dump(what, file)
    file.flush()
    os.fsync(file)
    file.close()

def create_process(frames, save_as):
    p = multiprocessing.Process(target=process, args=(frames, save_as))
    p.start()
    return p

def processfile(file, save_dir):
    #multiprocessing pool has issues with leaking memory i seriously tried a lot of stuff
    #this is stupid but it's going to work

    video_capture = cv2.VideoCapture(file)

    frames = []
    tasks = []
    fps = 0

    while video_capture.isOpened():
        ret, frame = video_capture.read()
        if not ret:
            break

        while (psutil.virtual_memory().available / 1024 / 1024 < 20000):
            print("sleeping cus of memory ", len(tasks))
            time.sleep(15)

        if (len(frames) > 100):
            save_as = os.path.join(save_dir, os.path.basename(file) + "." + str(len(tasks)) + ".part")
            tasks.append(create_process(frames.copy(), save_as))
            print("apeddnign additional tasks to queue current queue size {}", len(tasks))
            frames.clear()
        else:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_pil = PIL.Image.fromarray(frame_rgb)
            frames.append((frame_pil, fps))

        fps += 1

    save_as = os.path.join(save_dir, os.path.basename(file) + "." + str(len(tasks)) + ".part")
    if (len(frames) != 0): tasks.append(create_process(frames.copy(), save_as))

    frames.clear()
    video_capture.release()

    for task in tasks:
        while(task.is_alive()):
            time.sleep(5)
        print("Processed videos, waiting for {} task out of {} tasks")

if __name__ == "__main__":
    # I had it set to 4 however it resutled in broken pipe errors I don't understand why but having it as 1 fixes it.
    videos_dir = "videos"
    process_save_dir = "processed"

    if (not os.path.exists(videos_dir)):
        os.mkdir(videos_dir)
    if (not os.path.exists(process_save_dir)):
        os.mkdir(process_save_dir)

    for dir in os.listdir(videos_dir):
        joined = os.path.join(videos_dir, dir)
        if (not os.path.isdir(joined)): continue
        for file in os.listdir(joined):
            movie = os.path.join(joined, file)
            processfile(movie, process_save_dir)