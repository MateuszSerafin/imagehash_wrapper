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
    return bin(x.hash ^ y.hash).count('1')


# Long story short, when testing i used imageMultihash from imagehash lib
# I found out it's better to store each hash and then compare how many matches from what vid
# Please make sure that your call function returns [hashes, ...] must be a iterable
# check my function to find images in tree this will make much more sense why
class CustomHashFunc:
    def __call__(self, image: PIL.Image.Image, *args, **kwargs) -> list[str]:
        hashed = imagehash.crop_resistant_hash(image, *args, **kwargs)

        return [str(segmented) for segmented in hashed.segment_hashes]



class RequiredComparasion:
    def str_to_hash(self, hex_hash: str):
        pass

#Binary tree on it's own is not enough to match exactly, I am using imagehash by default
#Their hex values represent slightly more than binary tree can match therefore edit this class
#if you have custom implementation or leave it to
class OrginalHashComparer:


#If you just want to use BinaryTree less accuracy but it's much faster use this


#multiprocessing doesn't like this being inside of class
def _process_frames_to_hashes(hashfunc, frames: list[tuple[PIL.Image.Image, int]]) -> list[tuple[list[str], int]]:
    #PIL, framenumber from vid
    processed = []
    for frame in frames:
        processed.append((hashfunc(frame[0]), frame[1]))
    return processed


class Wrapped:
    # This implementation of binary tree is really clean, that's why i use it
    _tree: pybktree.BKTree = pybktree.BKTree(hamming_distance_func)

    #files should be uniquely named
    _duplicateCheck: set[str] = set()
    #Filenames stored
    _lookUp: list[str] = []

    # hash func should return a list[str] see class to see why
    _hashFunc: CustomHashFunc = None

    # TODO this requires a good default, tldr bigger value searches through more images resulting in better accuracy
    #  but it's slower
    _hammingDistance: int = 6

    # if save dir is not none
    # when initializing make sure to load all processed files
    # and when processing file make sure to save it
    # if it's none skip it
    _saveDir: os.path = None

    # When you look at pybktree docs it says to do that, all it is just container, i can get data when it matches something
    # when doing lookup to the tree element such as fileID can be empty, but when this is actually in tree all of them
    # should be populated, when processing a single Image assume a frameNumber of 0
    _treeData = collections.namedtuple('treeData', 'hash frameNumber fileID')

    def __init__(self, save_dir: os.path = None, hashfunc: CustomHashFunc = CustomHashFunc(),
                 hamming_distance: int = 6):
        self._tree = pybktree.BKTree(hamming_distance_func)
        self._duplicateCheck = set()
        self._lookUp = []
        self._hashFunc = hashfunc
        self._hamming_distance = hamming_distance
        self._treeData = collections.namedtuple('treeData', 'hash frameNumber fileID')

        if (save_dir != None):
            pass
        else:
            self._saveDir = save_dir


    #@Nullable
    def duplicate_and_fileid(self, filename: str) -> int:
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
    def _add_to_tree(self, oneframe: list[str], fileid: int, framenumber: int):
        for potentialsubhashes in oneframe:
            assembled = self._treeData(int(potentialsubhashes, 16), framenumber, fileid)
            self._tree.add(assembled)

    #False = fail
    #True it worked
    #TODO this should return fileID
    def add_image(self, image: PIL.Image.Image, filename: str) -> bool:
        fileID = self.duplicate_and_fileid(filename)
        if(fileID == None):
            return False
        #One image = 0 frame number
        self._add_to_tree(self._hashFunc(image), fileID, 0)
        return True

    def _processed_to_tree(self, processedframes:  list[tuple[list[str], int]], fileid: int):
        for listhashes, framenumber in processedframes:
            self._add_to_tree(listhashes, fileid, framenumber)

    #False = fail
    #True it worked
    #TODO this should return fileID
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



    def find_match(self, image: PIL.Image.Image, distance = 6):
        unknownImage = self._hashFunc(image)

        accumulator = []
        for unknownImageHashes in unknownImage:
            self._treeData(unknownImageHashes, None, None)
            accumulator.extend(self._tree.find(int(unknownImageHashes, 16), distance))



    def find_multiple_matches(self, lsi):

def checkable(imges, tree):
        realmatchesasobjects = []

        iterable = []

        boolable = True
        for segment in tobecompared.segment_hashes:
            Item = collections.namedtuple('Item', 'int imagemultihash')

            toaddlater = set()

            findings = tree.find(Item(int(str(segment), 16), tobecompared), 6)
            if (len(findings) != 0): boolable = False
            for nbr, value in findings:
                toaddlater.add(value.imagemultihash)
            realmatchesasobjects.append(toaddlater)

        # if it doesnt match it means that tree search was too low 6 for me was good.
        # adding more means more to compare so its a speed tradeoff.
        # test what you need
        if (boolable):
            differentmatches += 1
            continue

        size = len(realmatchesasobjects)
        if (size == 0):
            return

        if (size == 1):
            # exactly one match
            for imghash in realmatchesasobjects[0]:
                iterable.append(imghash)
        else:
            # multiple matches
            element_counts = {}
            for s in realmatchesasobjects:
                for elem in s:
                    if elem in element_counts:
                        element_counts[elem] += 1
                    else:
                        element_counts[elem] = 1

            # the first idea was to make set and count which video has the most hits and which frame but
            # the current implementation works too.
            # print("NIBY PRAWIDLOWE: ", len(list(elem for elem, count in element_counts.items())))
            iterable = list(elem for elem, count in element_counts.items())

        best_match = tobecompared.best_match(iterable)
        if (not (tobecompared.file == best_match.file)):
            misses += 1
        diffinindex = abs(int(tobecompared.index) - int(best_match.index))
        if (diffinindex < minimum):
            minimum = diffinindex
        if (diffinindex > maximum):
            maximum = diffinindex
        if (diffinindex > 500):
            above500matches += 1
        else:
            avarage += diffinindex
            howmucprocessed += 1
        print("Current: ", howmucprocessed + above500matches, " Misses: ", misses, "Avarage: ",
              avarage / howmucprocessed,
              " Max: ",
              maximum, " Min: ", minimum, " Above 500matches:" + str(above500matches), " Recalculation: ",
              str(differentmatches))

        # Current - currently processed frames (amount)
        # misses - how many frames did not match samples
        # avarage - avarage difference between frames numbers
        # maximum - maximum difference between frames
        # minimum - similar to maximum
        # above 500 matches - how many frames were above 500 frames difference (if you need to match exact frames of video this seems usefull stat)
        # recalculation - when tree won't find anything to search realistially a next search should occur then with hamming distance of 8 perhaps 10. (Comment somewhere above)


if __name__ == "__main__":
    custom = Wrapped()
    video = "C:/Users/MSI/Videos/2023-04-17 20-02-39.mp4"
    custom.add_video(video)

