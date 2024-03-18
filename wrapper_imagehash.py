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
from typing import TypeVar, Generic
T = TypeVar('T')


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


def create_process(frames: list[tuple[PIL.Image.Image, int]], hash_func: callable) -> multiprocessing.Queue:
    return_pipe = multiprocessing.Queue()
    p = multiprocessing.Process(target=async_worker, args=(frames, hash_func, return_pipe))
    p.start()
    return return_pipe


#good to check for errors
class Response(Generic[T]):
    _failed: bool = False
    _data: Generic[T]
    _reason: str

    def __init__(self, failed: bool, data: Generic[T] = None, reason="Unknown"):
        self._failed = failed
        self._data = data
        self._reason = reason

    def did_fail(self) -> bool:
        return self._failed

    def fail_reason(self) -> str:
        return self._reason

    def get_data(self) -> Generic[T]:
        return self._data

    def __str__(self):
        return f"""Failed: {self._failed}"""


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
        if (fileId.did_fail()):
            raise Exception(fileId.fail_reason())

        with bz2.BZ2File(file, "rb") as f:
            try:
                while True:
                    # Should be list[tuple[list[imageHash], framenumber]]
                    toload = pickle.load(f)
                    for oneFrameHashes, oneFrameNumber in toload:
                        self._add_to_tree(oneFrameHashes, fileId.get_data(), oneFrameNumber)

            except (EOFError, pickle.UnpicklingError) as e:
                if(type(e) == EOFError):
                    pass
                else:
                    raise Exception("File {} is most likely corrupted please regenerate this video".format(os.path.basename(file)))

    def _duplicate_and_fileid(self, filename: str) -> Response[int]:
        if (filename in self._duplicateCheck):
            return Response(True, reason="File already exist in internal database please change name no duplicates are allowed")
        self._duplicateCheck.add(filename)
        fileID = len(self._lookUp)
        self._lookUp.append(filename)
        return Response(False, data=fileID)

    # one image can contain multiple hashes therefore list[imageHash]
    def _add_to_tree(self, oneframe: list[imagehash], fileid: int, framenumber: int):
        for potentialsubhashes in oneframe:
            assembled = self._treeData(potentialsubhashes, framenumber, fileid)
            self._tree.add(assembled)

    def add_image(self, image: PIL.Image.Image | os.PathLike, filename: str) -> Response:
        hashes = None
        if(isinstance(image, PIL.Image.Image)):
            hashes = self._hashFunc(image)
        else:
            if (not os.path.exists(image)):
                return Response(True, reason="File does not exist")
            try:
                img = PIL.Image.open(image)
                hashes = self._hashFunc(img)
                img.close()
            except Exception as e:
                return Response(True, reason=str(e))

        if(hashes == None):
            return Response(True, reason="Wrong object provided to add_image function")

        fileID = self._duplicate_and_fileid(filename)
        if(fileID.did_fail()):
            return fileID

        self._add_to_tree(hashes, fileID.get_data(), 0)
        if (self._saveDir != None):
            #Lazy
            try:
                file = bz2.BZ2File(os.path.join(self._saveDir, filename + ".bz2"), "wb")
                pickle.dump([(hashes, 0)], file)
                file.flush()
                file.close()
            except Exception as e:
                return Response(True, reason=str(e))
        return Response(False)

    def _processed_to_tree(self, processedframes: list[list[imagehash.ImageHash], int], fileid: int):
        for listhashes, framenumber in processedframes:
            self._add_to_tree(listhashes, fileid, framenumber)

    # I know it spawns too much processes but it time it was being processed
    # Also multiprocessing pool has memory leak and it breaks pipe on my machine
    # I spend lot of time debugging it but it looks like internal problem
    def add_video(self, filename: os.PathLike | str, leavethismuchmemory: int = 4096, computeeveryNframe: int = 8) -> Response:
        cap = None


        if (not os.path.exists(filename)):
            return Response(True, reason="File doesn't exist")
        #No overload for differnt types just string
        cap = cv2.VideoCapture(str(filename))

        if(cap == None):
            return Response(True, reason="Unsupported argument type")

        fileID = self._duplicate_and_fileid(filename)
        if (fileID.did_fail()):
            return fileID

        frames = []
        tasks = []
        fps = 0

        counter = computeeveryNframe

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if (counter > computeeveryNframe):
                while (psutil.virtual_memory().available / 1024 / 1024 < leavethismuchmemory):
                    # TODO there should be adding to tree
                    time.sleep(15)

                if (len(frames) > 50):
                    # TODO i think there is an issue calling self._hashffunc. I think multiprocessing will break it and better would be to call CustomHashFunc() as a new object
                    # But then what is the point of self._hashfunc
                    tasks.append(create_process(frames.copy(), self._hashFunc))
                    frames.clear()
                else:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame_pil = PIL.Image.fromarray(frame_rgb)
                    frames.append((frame_pil, fps))

                counter = 0
            fps += 1
            counter += 1

        if (len(frames) != 0): tasks.append(create_process(frames.copy(), self._hashFunc))
        frames.clear()
        cap.release()

        if (self._saveDir != None):
            file = bz2.BZ2File(os.path.join(self._saveDir, os.path.basename(filename) + ".bz2"), "wb")
        else:
            file = None

        for task in tasks:
            return_from_task = task.get()
            self._processed_to_tree(return_from_task, fileID.get_data())
            if (file != None):
                pickle.dump(return_from_task, file)

    def _match_video(self, hashesList: list[list[imagehash.ImageHash]], hamming_distance: int = 24) -> str | bool:
        mostCommon = []
        for frame in hashesList:
            mostCommon.extend(
                self._internal_matcher(frame, hamming_distance=hamming_distance, skipFrameInformation=True))
        if (len(mostCommon) == 0):
            return False
        # TODO this should return multiple matches if they have the same weight
        fileID = Counter(mostCommon).most_common(1)[0][0]
        return self._lookUp[fileID]


    def _match_exact_frame(self, hashes: list[imagehash.ImageHash], hamming_distance: int = 24) -> tuple[str, int] | bool:
        internalResult = self._internal_matcher(hashes, hamming_distance=hamming_distance)
        # TODO this should return multiple matches if they have the same weight
        if (len(internalResult) == 0):
            return False
        fileID, frameNumber = Counter(internalResult).most_common(1)[0][0]
        return self._lookUp[fileID], frameNumber

    # this was wrriten heavy in mind of ImageMultiHash class not sure if it works with regular phash,dhash etc
    # all it does it collects most common fileids on each frame and then again collects it and this is the result
    # more or less exactly what ImageMultiHash.best_match() look like
    def _internal_matcher(self, hashes: list[imagehash.ImageHash], hamming_distance: int = 24,
                          skipFrameInformation=False):
        most_frequent = []
        for hashFromTree in hashes:
            assembled = self._treeData(hashFromTree, None, None)
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

    def match_video(self, file: os.path, hamming_distance: int = 3) -> Response[str] | Response[bool]:
        if (not os.path.exists(file)):
            return Response(True, reason="File doesn't exist")
        cap = cv2.VideoCapture(file)

        if(cap == None):
            return Response(True, reason="Unsupported argument type")


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
        return Response(failed=False, data=self._match_video(pil_images, hamming_distance=hamming_distance))

    def match_frame(self, image: PIL.Image.Image, hamming_distance=3) -> Response[tuple[str, int]] | Response[bool]:
        hashes = None
        if(isinstance(image, PIL.Image.Image)):
            hashes = self._hashFunc(image)
        else:
            if(not os.path.exists(image)):
                return Response(True, reason="File does not exist")
            img = PIL.Image.open(image)
            hashes = self._hashFunc(img)
            img.close()

        if(hashes == None):
            return Response(True, reason="Wrong object provided to add_image function")

        return Response(failed=False, data=self._match_exact_frame(hashes, hamming_distance=hamming_distance))

    def match_one_video_multiple_frames(self, listImages: list[PIL.Image.Image], hamming_distance=24) -> str | bool:
        hashes = []
        for image in listImages:
            hashes.append(self._hashFunc(image))
        return self._match_video(hashes, hamming_distance=hamming_distance)


if __name__ == "__main__":
    custom = Wrapped(savedir="mydirectory")

    custom.add_video("vid1.mp4")

    #False means not found
    assert custom.match_video("vid2.mp4", hamming_distance=3).get_data() == False

    #Increasing hamming distance makes it match frames that are not necessary from same video.
    #This cannot be changed as matching less similar images literary means that it can match somethning that is different
    #matches vid1 even we put vid2 as a reference
    assert custom.match_video("vid2.mp4", hamming_distance=12).get_data() == "vid1.mp4"

    custom.add_video("vid2.mp4")

    #However after adding vid2 to binary tree it became the best match even with same hamming_distance please be aware of this behaviour
    assert custom.match_video("vid2.mp4", hamming_distance=12).get_data() == "vid2.mp4"

    #screen shot includes part of windows player, it changes hashes therefore it needs increased hamming distance
    #If windows player would be cropped out hamming_distance of 3 would be enough
    #Please take this information to consideration with your project
    #TODO do test to make sure that frames are matched within sensible amount of frames
    assert custom.match_frame("screenshotvid1_54.png", hamming_distance=16).get_data() == ("vid1.mp4", 64)

    #Check to make sure that loading is working properly
    assert list(Wrapped(savedir="mydirectory")._tree) == list(custom._tree)

    #Doesn't scream when __main__ is empty
    pass