import bz2
import collections
import os
import pickle
import sys

import imagehash
import pybktree
from tqdm import tqdm

Item = collections.namedtuple('Item', 'int container')
sys.setrecursionlimit(999999999)

def twos_complement(hexstr, bits):
    value = int(hexstr, 16)  # convert hexadecimal to integer

    # convert from unsigned number to signed number with "bits" bits
    if value & (1 << (bits - 1)):
        value -= 1 << bits
    return value

def loadtotree(filename, tree):
    file = bz2.BZ2File(filename, 'rb')

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
    hamming_cutoff = len(x.int) * 64
    for segment_hash in x.int:
        lowest_distance = min(bin(segment_hash ^ other_segment_hash).count('1') for other_segment_hash in y.int)
        if lowest_distance > hamming_cutoff:
            continue
        distances.append(lowest_distance)

    return sum(distances)


if __name__ == "__main__":
    tree = pybktree.BKTree(hamming_distanec)


    dir = "8multihash/"

    cnt = 0
    for file in tqdm(os.listdir(dir)):
        if(cnt > 50):
            print("breaking")
            break
        cnt += 1
        if(not "bz28withresistant" in file): continue
        loadtotree(os.path.join(dir, file), tree)

    todump = bz2.BZ2File("zrzutka32.tree.bz2", 'wb')
    pickle.dump(tree, todump)
    todump.close()

