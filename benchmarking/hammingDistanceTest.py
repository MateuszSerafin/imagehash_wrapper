import imagehash
import numpy
import pybktree
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

#Stolen from
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
    #Filenames stored
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
        self._treeData = collections.namedtuple('treeData', 'ImageHash frameNumber fileID')

        if (savedir != None):
            pass
        self._saveDir = savedir

    #Basename without parts video.mp4 not video.mp4.part
    def _load_to_tree(self, filename: str):
        if(self._saveDir == None):
            raise Exception("Saving/Loading files is not supported without telling the directory")

        fileid = self._duplicate_and_fileid(filename)
        if(fileid == None):
            raise Exception("Should not happen")

        for file in os.listdir(self._saveDir):
            splited = file.split(".")
            basename = ''.join(splited[0].split(".")[0:-1])

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
    #TODO this should return fileID
    def add_image(self, image: PIL.Image.Image, filename: str) -> bool:
        fileID = self._duplicate_and_fileid(filename)
        if(fileID == None):
            return False
        #One image = 0 frame number
        self._add_to_tree(self._hashFunc(image), fileID, 0)
        return True


    def look_up(self, image: PIL.Image.Image, hamming_distance: int = 6):
        accumulator = []

        for hash in self._hashFunc(image):
            assembled = self._treeData(hash, None, None)
            accumulator.append(self._tree.find(assembled, hamming_distance))
        return accumulator



if __name__=="__main__":
    wrapped = Wrapped()

    amogus = []
    for image in tqdm.tqdm(os.listdir("../samples")):
        img = PIL.Image.open(os.path.join("../samples", image))
        wrapped.add_image(img, image)
        amogus.append(img.copy())
        img.close()

    print(wrapped.look_up(amogus[0]))

