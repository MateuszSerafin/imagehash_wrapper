import multiprocessing
import os
import pickle
import PIL
import imagehash
import bz2

def load(file, arr,):
    file = bz2.BZ2File(file,'rb')
    try:
        while True:
            arr.extend(pickle.load(file))
    except (EOFError):
        pass
    file.close()

class custom_hash_func:
    # play around with bits but 8 is enough
    # it's only there because i want to adjust size without changing the actual function behind it.
    def __init__(self, hashfunc, bits=8):
        self.hash_func = hashfunc
        self.bits = bits

    def __call__(self, *args, **kwargs):
        return self.hash_func(*args, hash_size=self.bits)

def worker(tasks, mainarr):
    howmucprocessed = 0
    misses = 0
    avarage = 0
    maximum = 0
    minimum = 9999

    for task in tasks:
        frame = PIL.Image.open(task)
        best_match = imagehash.crop_resistant_hash(frame, hash_func=custom_hash_func(imagehash.phash)).best_match(mainarr)

        after = ".".join(best_match.file.split(".")[:-1])
        afterfile = ".".join(task.split(".")[:-2])
        if (not (after == afterfile)):
            misses += 1
        diffinindex = abs(int(best_match.index) - int(task.split(".")[-2]))

        avarage += diffinindex

        if (diffinindex < minimum):
            minimum = diffinindex
        if (diffinindex > maximum):
            maximum = diffinindex

    return (howmucprocessed, misses, avarage, maximum, minimum)


if __name__=="__main__":
    mainarr = []
    multiprocessing.set_start_method('forkserver')
    pool = multiprocessing.Pool(1)

    processed_path = "processed"
    sample_path = "samples"

    for toload in os.listdir(processed_path):
        print(toload)
        load(os.path.join(processed_path, toload), mainarr)

    #cnt is for allowing multiprocessing to copy it.
    #it didnt like straight variables so it works works.
    cnt = []
    tasks = []

    for file in os.listdir(sample_path):
        cnt.append(os.path.join(sample_path,file))
        if(len(cnt) == 1):
            tasks.append(pool.apply_async(worker, args=[cnt, mainarr]))
            cnt.clear()
    tasks.append(pool.apply_async(worker, args=[cnt, mainarr]))
    cnt.clear()

    howmucprocessed = 0

    misses = 0
    avarage = 0
    maximum = 0
    minimum = 9999

    for task in tasks:
        h, m, b, ax, mx = task.get()
        howmucprocessed += h
        misses += m
        avarage += b

        if (mx < minimum):
            minimum = mx
        if (ax > maximum):
            maximum = ax
        if(not howmucprocessed == 0 and not avarage == 0):
            print("Current: ", howmucprocessed, " Misses: ", misses, "Avarage: ", avarage / howmucprocessed, " Max: ",
                  maximum, " Min: ", minimum)


