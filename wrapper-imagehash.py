import bz2
import collections
import os
import pickle
import PIL.Image
import imagehash
import pybktree
import tqdm
import concurrent.futures
import cv2
import psutil
import time

def hamming_distance_func(x, y):
    return x.ImageHash - y.ImageHash

# Long story short, when testing i used imageMultihash from imagehash lib
# I found out it's better to store each hash and then compare how many matches from what vid
# Please make sure that your call function returns [hashes, ...] must be a iterable
# check my function to find images in tree this will make much more sense why
class CustomHashFunc:
    def __call__(self, image: PIL.Image.Image, *args, **kwargs) -> list[imagehash.ImageHash]:
        hashed = imagehash.crop_resistant_hash(image, *args, **kwargs)
        return [segmented for segmented in hashed.segment_hashes]


class Wrapped:
    # This implementation of binary tree is really clean, that's why i use it
    _tree: pybktree.BKTree = pybktree.BKTree(hamming_distance_func)

    #files should be uniquely named
    _duplicateCheck: set[str] = set()
    #Filenames stored, they are not persistent each time it loads it can change do not rely on just numbers, filenames should be the way to go
    _lookUp: list[str] = []

    # hash func should return a list[str] see class to see why
    _hashFunc: CustomHashFunc = None

    # if save dir is not none
    # when initializing make sure to load all processed files
    # and when processing file make sure to save it
    # if it's none skip it
    _saveDir: os.path = None

    # When you look at pybktree docs it says to do that, all it is just container, i can get data when it matches something
    # when doing lookup to the tree element such as fileID can be empty, but when this is actually in tree all of them
    # should be populated, when processing a single Image assume a frameNumber of 0
    _treeData = collections.namedtuple('treeData', 'ImageHash frameNumber fileID')

    def __init__(self, savedir: os.path = None, hashfunc: CustomHashFunc = CustomHashFunc()):
        self._tree = pybktree.BKTree(hamming_distance_func)
        self._duplicateCheck = set()
        self._lookUp = []
        self._hashFunc = hashfunc
        self._saveDir = savedir
        self._treeData = collections.namedtuple('treeData', 'ImageHash frameNumber fileID')

        if (savedir != None):
            for processed_file in os.listdir(self._saveDir):
                to_load = os.path.join(self._saveDir, processed_file)
                self._load_to_tree(to_load)
        self._saveDir = savedir

    def _load_to_tree(self, file: os.path):
        if(self._saveDir == None):
            raise Exception("Saving/Loading files is not supported without telling the directory")

        splited = os.path.basename(file).split(".")
        basename = '.'.join(splited[0:-1])
        fileId = self._duplicate_and_fileid(basename)
        if(fileId == None):
            raise Exception("Should not happen")

        with bz2.BZ2File(file, "rb") as f:
            try:
                while True:
                    #Should be list[tuple[list[imageHash], framenumber]]
                    toload = pickle.load(f)
                    for oneFrameHashes, oneFrameNumber in toload:
                        self._add_to_tree(oneFrameHashes, fileId, oneFrameNumber)

            except (EOFError, pickle.UnpicklingError):
                pass

    #@Nullable
    def _duplicate_and_fileid(self, filename: str) -> int:
        if (filename in self._duplicateCheck):
            #I return none because 0 == False
            #TODO this should return like response wrapper with true false and then integer
            return None
        self._duplicateCheck.add(filename)
        fileID = len(self._lookUp)
        self._lookUp.append(filename)
        return fileID

    #one image can contain multiple hashes therefore list[str]
    #TODO i swear i need to wrap everything over classes because it starts to not make sense
    def _add_to_tree(self, oneframe: list[imagehash], fileid: int, framenumber: int):
        for potentialsubhashes in oneframe:
            assembled = self._treeData(potentialsubhashes, framenumber, fileid)
            self._tree.add(assembled)

    #False = fail
    #True it worked
    def add_image_pil(self, image: PIL.Image.Image, filename: str) -> bool:
        fileID = self._duplicate_and_fileid(filename)
        if(fileID == None):
            return False
        #One image = 0 frame number
        hashes = self._hashFunc(image)
        self._add_to_tree(hashes, fileID, 0)
        if(self._saveDir != None):
            file = bz2.BZ2File(os.path.join(self._saveDir, filename + ".bz2"), "wb")
            pickle.dump([(hashes, 0)], file)
            file.flush()
            file.close()
        return True

    def add_image(self, file: os.path) -> bool:
        basename = os.path.basename(file)
        image = PIL.Image.open(file)
        copy = image.copy()
        image.close()
        return self.add_image_pil(copy, basename)


    def _processed_to_tree(self, processedframes:  list[tuple[list[str], int]], fileid: int):
        for listhashes, framenumber in processedframes:
            self._add_to_tree(listhashes, fileid, framenumber)


    def look_up(self, image: PIL.Image.Image, hamming_distance: int = 6):
        counter = {}

        for nbr, hash in enumerate(self._hashFunc(image)):
            assembled = self._treeData(hash, None, None)

            for distance, treeData in self._tree.find(assembled, hamming_distance):
                if(nbr not in counter):
                    counter[nbr] = {}

                print(distance)
                print(treeData)
        #return accumulator



    #False = fail
    #True it worked
    #I woudln't run it with less than 4gb
    def add_video(self, filename: os.path, threads: int=os.cpu_count(), leavethismuchmemory: int=4096) -> bool:
        pool = concurrent.futures.ProcessPoolExecutor(threads)

        #TODO this requires more checks
        if(not os.path.exists(filename)):
            return False

        #I assume that the file is correct by that it can definitely error
        video_capture = cv2.VideoCapture(filename)

        #TODO Past this point it shouldn't be error make check to above video
        fileID = self.duplicate_and_fileid(filename)
        if(fileID == None):
            return False

        frames = []
        tasks = []
        fps = 0
        #skip amount of frames
        counter = 8
        #save_as = os.path.join(save_dir, os.path.basename(file) + "." + str(len(tasks)) + ".part")

        while video_capture.isOpened():
            ret, frame = video_capture.read()
            if not ret:
                break
            if (counter > 7):
                while (psutil.virtual_memory().available / 1024 / 1024 < leavethismuchmemory):
                    #TODO there should be adding to tree
                    time.sleep(15)

                if (len(frames) > 50):
                    tasks.append(pool.submit(_process_frames_to_hashes, self._hashFunc, frames.copy()))
                    frames.clear()
                else:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame_pil = PIL.Image.fromarray(frame_rgb)
                    frames.append((frame_pil, fps))

                counter = 0
            fps += 1
            counter += 1

        if (len(frames) != 0): tasks.append(pool.submit(_process_frames_to_hashes, self._hashFunc, frames.copy()))
        frames.clear()
        video_capture.release()
        pool.shutdown(wait=True)
        #TODO make it so when it iterates it removes element from memory so not copied twice
        for task in tasks:
            result = task.result()
            self._processed_to_tree(result, fileID)

if __name__ == "__main__":
    custom = Wrapped(savedir="save")
    #video = "C:/Users/MSI/Videos/2023-04-17 20-02-39.mp4"
    #custom.add_video(video)
    print(len(custom.look_up(PIL.Image.open("samples/Rick and Morty S06E06.mp4.5551.png"))))
    #print(len(list(custom._tree)))
    #print(list(custom._tree))