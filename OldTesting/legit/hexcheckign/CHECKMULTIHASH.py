import bz2
import collections
import os
import pickle

import imagehash
import pybktree


def load(file, arr):
    file = bz2.BZ2File(file, 'rb')
    try:
        while True:
            for loaded in pickle.load(file):
                frame_id = loaded[2].split(".")[-2]
                name_of = ".".join(loaded[2].split(".")[:-2])
                kontener = container(loaded[0], name_of, frame_id)
                arr.append(kontener)
    except (EOFError):
        pass
    file.close()



def twos_complement(hexstr, bits):
    value = int(hexstr, 16)  # convert hexadecimal to integer

    # convert from unsigned number to signed number with "bits" bits
    if value & (1 << (bits - 1)):
        value -= 1 << bits
    return value

def loadtotree(filename, tree):
    file = bz2.BZ2File(filename, 'rb')

    Item = collections.namedtuple('Item', 'int container')

    try:
        while True:
            arr = pickle.load(file)

            for hashed in arr:
                ints = []

                for segment_hash in hashed[0].segment_hashes:
                    ints.append(twos_complement(str(segment_hash),64))
                kontener = container(hashed[0], ".".join(filename.split(".")[:-1]), hashed[2])
                tree.add(Item(ints, kontener))
    except (EOFError):
        pass
    file.close()


class container():
    def __init__(self, imagehash:imagehash.ImageMultiHash, file:str, index:int):
        self.imagehash = imagehash
        self.file = file
        self.index = int(index)
    def __str__(self):
        return self.file + "."+ str(self.index)

    def lowest_match(self, other_MATCHES:list):
        try:
            match = min(other_MATCHES, key=lambda other_hash: self.imagehash.__sub__(other_hash[1].container.imagehash))[1].container
            return (self.file == match.file, abs(self.index - match.index))
        except Exception as e:
            return None


def hamming_distanec(x,y):
    distances = []
    hamming_cutoff = len(x.int) * 8
    for segment_hash in x.int:
        lowest_distance = min(bin(segment_hash ^ other_segment_hash).count('1') for other_segment_hash in y.int)
        if lowest_distance > hamming_cutoff:
            continue
        distances.append(lowest_distance)

    return sum(distances)


if __name__ == "__main__":
    imges = []
    load("ZDJECIA.BZ28", imges)

    tree = pybktree.BKTree(hamming_distanec)

    dir = "8multihash/"

    for file in os.listdir(dir):
        print(file)
        if(not "bz28withresistant" in file): continue
        loadtotree(dir+file, tree)



    filematches = 1
    notmatches = 0

    diffaa = 1

    loops = 0


    for img in imges:

        Item = collections.namedtuple('Item', 'int container')
        ints = []

        for segment_hash in img.imagehash.segment_hashes:
            ints.append(twos_complement(str(segment_hash), 64))

        letrollmomentosiksde123XXDXDXD = Item(ints, img)
        a = tree.find(letrollmomentosiksde123XXDXDXD, 256)

        matched = img.lowest_match(a)
        if(matched == None):
            notmatches += 1
            loops += 1
            continue

        file, diff = matched
        if(file):
            filematches += 1
            diffaa += diff

        else:
            notmatches += 1
        loops += 1
        print("File matches: ", filematches, " Avg diff: ", diffaa/filematches, "NOT MATCHED: ", notmatches, " LOOPS: ", loops)