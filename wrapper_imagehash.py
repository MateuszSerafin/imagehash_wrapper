import bz2
import collections
import multiprocessing
import os
import pickle
import random
import PIL.Image
import imagehash
import pybktree
import cv2
import psutil
import time
from collections import Counter


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


def async_worker(frames: list[tuple[PIL.Image.Image, int]], hashfunc: callable, return_pipe: multiprocessing.Queue):
    processed = []
    # frame (image) and also what frame number it is.
    for framerog in frames:
        done = hashfunc(framerog[0])
        processed.append((done, framerog[1]))
    return_pipe.put(processed)
    return


class Wrapped:
    # This implementation of binary tree is really clean, that's why i use it
    _tree: pybktree.BKTree = pybktree.BKTree(hamming_distance_func)

    # files should be uniquely named
    _duplicateCheck: set[str] = set()
    # Filenames stored, they are not persistent each time it loads it can change do not rely on just numbers, filenames should be the way to go
    _lookUp: list[str] = []

    # hash func should return a list[str] see class to see why
    _hashFunc: CustomHashFunc = None

    # if mydirectory dir is not none
    # when initializing make sure to load all processed files
    # and when processing file make sure to mydirectory it
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
        if (self._saveDir == None):
            raise Exception("Saving/Loading files is not supported without telling the directory")

        splited = os.path.basename(file).split(".")
        basename = '.'.join(splited[0:-1])
        fileId = self._duplicate_and_fileid(basename)
        if (fileId == None):
            raise Exception("Should not happen")

        with bz2.BZ2File(file, "rb") as f:
            try:
                while True:
                    # Should be list[tuple[list[imageHash], framenumber]]
                    toload = pickle.load(f)
                    for oneFrameHashes, oneFrameNumber in toload:
                        self._add_to_tree(oneFrameHashes, fileId, oneFrameNumber)

            except (EOFError, pickle.UnpicklingError):
                pass

    # @Nullable
    def _duplicate_and_fileid(self, filename: str) -> int:
        if (filename in self._duplicateCheck):
            # I return none because 0 == False
            # TODO this should return like response wrapper with true false and then integer
            return None
        self._duplicateCheck.add(filename)
        fileID = len(self._lookUp)
        self._lookUp.append(filename)
        return fileID

    # one image can contain multiple hashes therefore list[imageHash]
    # TODO i swear i need to wrap everything over classes because it starts to not make sense
    def _add_to_tree(self, oneframe: list[imagehash], fileid: int, framenumber: int):
        for potentialsubhashes in oneframe:
            assembled = self._treeData(potentialsubhashes, framenumber, fileid)
            self._tree.add(assembled)

    # False = fail
    # True it worked
    def add_image_pil(self, image: PIL.Image.Image, filename: str) -> bool:
        fileID = self._duplicate_and_fileid(filename)
        if (fileID == None):
            return False
        # One image = 0 frame number
        hashes = self._hashFunc(image)
        self._add_to_tree(hashes, fileID, 0)
        if (self._saveDir != None):
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

    def _processed_to_tree(self, processedframes: list[list[imagehash.ImageHash], int], fileid: int):
        for listhashes, framenumber in processedframes:
            self._add_to_tree(listhashes, fileid, framenumber)


    def _create_process(self, frames: list[tuple[PIL.Image.Image, int]], hash_func: callable) -> multiprocessing.Queue:
        return_pipe = multiprocessing.Queue()
        p = multiprocessing.Process(target=async_worker, args=(frames, hash_func, return_pipe))
        p.start()
        return return_pipe

    # False = fail
    # True it worked
    # I know it spawns too much processes but it time it was being processed
    # Also multiprocessing pool has memory leak and it breaks pipe on my machine
    # I spend lot of time debugging it but it looks like internal problem
    def add_video(self, filename: os.path, leavethismuchmemory: int = 4096) -> bool:
        # TODO this requires more checks
        if (not os.path.exists(filename)):
            return False

        # I assume that the file is correct by that it can definitely error
        video_capture = cv2.VideoCapture(filename)

        # TODO Past this point it shouldn't be error make check to above video
        fileID = self._duplicate_and_fileid(filename)
        if (fileID == None):
            return False

        frames = []
        tasks = []
        fps = 0
        # skip amount of frames
        counter = 8

        while video_capture.isOpened():
            ret, frame = video_capture.read()
            if not ret:
                break
            if (counter > 7):
                while (psutil.virtual_memory().available / 1024 / 1024 < leavethismuchmemory):
                    # TODO there should be adding to tree
                    time.sleep(15)

                if (len(frames) > 50):
                    # TODO i think there is an issue calling self._hashffunc. I think multiprocessing will break it and better would be to call CustomHashFunc() as a new object
                    # But then what is the point of self._hashfunc
                    tasks.append(self._create_process(frames.copy(), self._hashFunc))
                    frames.clear()
                else:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame_pil = PIL.Image.fromarray(frame_rgb)
                    frames.append((frame_pil, fps))

                counter = 0
            fps += 1
            counter += 1

        if (len(frames) != 0): tasks.append(self._create_process(frames.copy(), self._hashFunc))
        frames.clear()
        video_capture.release()

        if (self._saveDir != None):
            file = bz2.BZ2File(os.path.join(self._saveDir, os.path.basename(filename) + ".bz2"), "wb")
        else:
            file = None

        for task in tasks:
            return_from_task = task.get()
            self._processed_to_tree(return_from_task, fileID)
            if (file != None):
                pickle.dump(return_from_task, file)

    # @Nullable
    def _match_video(self, hashesList: list[list[imagehash.ImageHash]], hamming_distance: int = 24) -> str:
        mostCommon = []
        for frame in hashesList:
            mostCommon.extend(
                self._internal_matcher(frame, hamming_distance=hamming_distance, skipFrameInformation=True))
        if (len(mostCommon) == 0):
            return None
        # TODO this should return multiple matches if they have the same weight
        fileID = Counter(mostCommon).most_common(1)[0][0]
        return self._lookUp[fileID]

    # @Nullable
    def _match_exact_frame(self, hashes: list[imagehash.ImageHash], hamming_distance: int = 24) -> tuple[str, int]:
        internalResult = self._internal_matcher(hashes, hamming_distance=hamming_distance)
        # TODO this should return multiple matches if they have the same weight
        if (len(internalResult) == 0):
            return None
        fileID, frameNumber = Counter(internalResult).most_common(1)[0][0]
        return self._lookUp[fileID], frameNumber * 8

    # this was wrriten heavy in mind of ImageMultiHash class not sure if it works with regular phash,dhash etc
    # all it does it collects most common fileids on each frame and then again collects it and this is the result
    # more or less exactly what ImageMultiHash.best_match() look like
    def _internal_matcher(self, hashes: list[imagehash.ImageHash], hamming_distance: int = 24,
                          skipFrameInformation=False):
        most_frequent = []
        for hash in hashes:
            assembled = self._treeData(hash, None, None)
            result = self._tree.find(assembled, hamming_distance)

            sorter = {}
            for distance, treeData in result:
                # This changes datatype and result
                if (skipFrameInformation):
                    extracted = treeData.fileID
                else:
                    extracted = (treeData.fileID, treeData.frameNumber)
                if (distance in sorter):
                    sorter[distance].append(extracted)
                else:
                    sorter[distance] = [extracted]
            if (len(sorter) == 0):
                return []
            min_value = min(sorter)
            most_frequent.extend(list(sorter[min_value]))
        return most_frequent

    # TODO this should return response object failed or not and result
    # Also it can return multiple matches as matching is not perfect end user
    # @Nullable
    def match_video(self, file: os.path, hamming_distance: int = 24) -> str:
        if (not os.path.exists(file)):
            raise Exception("File does not exist")

        cap = cv2.VideoCapture(file)

        frameCount = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        randomIndices = random.sample(range(frameCount), 10)

        pil_images = []

        for frame_index in randomIndices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ret, frame = cap.read()
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = PIL.Image.fromarray(frame_rgb)
            pil_images.append(self._hashFunc(pil_image))

        cap.release()
        return self._match_video(pil_images, hamming_distance=hamming_distance)

    # @Nullable
    def match_frame(self, image: PIL.Image.Image, hamming_distance=24):
        hashed = self._hashFunc(image)
        return self._match_exact_frame(hashed, hamming_distance=hamming_distance)

    # @Nullable
    def match_one_video_multiple_frames(self, listImages: list[PIL.Image.Image], hamming_distance=24):
        hashes = []
        for image in listImages:
            hashes.append(self._hashFunc(image))
        return self._match_video(hashes, hamming_distance=hamming_distance)


#if __name__ == "__main__":
    #custom = Wrapped(savedir="mydirectory")
    # for img in tqdm.tqdm(os.listdir("samples")):
    #   custom.add_image(os.path.join("samples", img))

    #print(custom.match_frame(PIL.Image.open("Untitled.png")))
    #video = "C:/Users/MSI/Videos/2023-04-17 20-02-39.mp4"
    # custom.add_video(video)
    #print(custom.match_video(video))
    # print(list(custom._tree))
    # among = [custom._hashFunc(PIL.Image.open("samples/Rick and Morty S06E06.mp4.5551.png"))]
    # print(custom._match_video(among))
    # print(len(list(custom._tree)))
    # print(list(custom._tree))
