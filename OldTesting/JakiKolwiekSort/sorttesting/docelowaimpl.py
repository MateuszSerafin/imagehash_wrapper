import bz2
import collections
import os
import pickle
import pprint

import imagehash
import pybktree


def load(file, arr):
    file = bz2.BZ2File(file, 'rb')
    try:
        while True:
            for loaded in pickle.load(file):
                toadd = loaded[0]

                toadd.index = loaded[2].split(".")[-2]
                toadd.file = ".".join(loaded[2].split(".")[:-2])
                arr.append(toadd)
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
    iter = 0
    Item = collections.namedtuple('Item', 'int imagemultihash')

    try:
        while True:
            arr = pickle.load(file)
            for hashed in arr:
                toadd = hashed[0]
                toadd.index = hashed[2]
                toadd.file = ".".join(filename.split(".")[:-1])

                for hash in toadd.segment_hashes:
                    tree.add(Item(int(str(hash), 16), toadd))
                iter += 1
    except (EOFError):
        pass
    file.close()


class container():
    def __init__(self, file: str, index: int):
        self.file = file
        self.index = int(index)

    def __eq__(self, other):
        return

    def __str__(self):
        return self.file + "." + str(self.index)


def checkable(imges, tree):
    above500matches = 0
    howmucprocessed = 1
    misses = 0
    bruh = 0
    maximum = 0
    minimum = 9999;

    differentmatches = 0
    for tobecompared in imges:
        realmatchesasobjects = []

        iterable = []

        boolable = True
        for segment in tobecompared.segment_hashes:
            Item = collections.namedtuple('Item', 'int imagemultihash')

            toaddlater = set()


            findings = tree.find(Item(int(str(segment), 16), tobecompared), 6)
            if(len(findings) != 0): boolable = False
            for nbr, value in findings:
                toaddlater.add(value.imagemultihash)
            realmatchesasobjects.append(toaddlater)


        if(boolable):
            differentmatches += 1
            continue

        size = len(realmatchesasobjects)
        if (size == 0):
            print("WAT 0 matches xdddddddddddd")
            return
        if (size == 1):
            print("Size one")
            for imghash in realmatchesasobjects[0]:
                iterable.append(imghash)
        else:
            print("MULTTIPLE")
            element_counts = {}
            num_sets = size

            for s in realmatchesasobjects:
                for elem in s:
                    if elem in element_counts:
                        element_counts[elem] += 1
                    else:
                        element_counts[elem] = 1

            # Find elements that appear in more than half of the sets
            half_threshold = num_sets / 2

            print("NIBY PRAWIDLOWE: ", len(list(elem for elem, count in element_counts.items())))
            iterable = list(elem for elem, count in element_counts.items())

        print(len(iterable))
        best_match = tobecompared.best_match(iterable)

        if (not (tobecompared.file == best_match.file.replace("8multihash/", ""))):
            misses += 1
        diffinindex = abs(int(tobecompared.index) - int(best_match.index))
        if (diffinindex < minimum):
            minimum = diffinindex
        if (diffinindex > maximum):
            maximum = diffinindex
        if (diffinindex > 500):
            above500matches += 1
        else:
            bruh += diffinindex
            howmucprocessed += 1
        print("Current: ", howmucprocessed + above500matches, " Misses: ", misses, "Avarage: ", bruh / howmucprocessed,
              " Max: ",
              maximum, " Min: ", minimum, " Above 500matches:" + str(above500matches), " Recalculation: ",  str(differentmatches))


def hamming_distance(x, y):
    return bin(x.int ^ y.int).count('1')


def returnable():
    imges = []
    load("ZDJECIA.BZ28", imges)

    tree = pybktree.BKTree(hamming_distance)

    dir = "8multihash/"

    for file in os.listdir(dir):
        print(file)
        if (not "bz28withresistant" in file): continue
        loadtotree(dir + file, tree)

    return tree, imges


if __name__ == "__main__":
    imges = []
    load("ZDJECIA.BZ28", imges)

    tree = pybktree.BKTree(hamming_distance)

    dir = "8multihash/"

    for file in os.listdir(dir):
        print(file)
        if (not "bz28withresistant" in file): continue
        loadtotree(dir + file, tree)

    checkable(imges, tree)
