import bz2
import collections
import os
import pickle
import PIL.Image
import imagehash
import pybktree
import tqdm

def twos_complement(hexstr, bits):
    value = int(hexstr, 16)
    if value & (1 << (bits - 1)):
        value -= 1 << bits
    return value

class custom_hash_func:
    # play around with bits but 8 is enough
    # it's only there because i want to adjust size without changing the actual function behind it.
    def __init__(self, hashfunc, bits=8):
        self.hash_func = hashfunc
        self.bits = bits

    def __call__(self, *args, **kwargs):
        return self.hash_func(*args, hash_size=self.bits)

def loadtotree(filename, tree):
    file = bz2.BZ2File(filename, 'rb')
    iter = 0
    # TODO realistically i think it copies each time imagemultihash object. There should be another array that stores it and it just points into it.
    # Simirarly with .file it copies lots of characters where it could just point to array or something
    Item = collections.namedtuple('Item', 'int imagemultihash')

    try:
        while True:
            arr = pickle.load(file)
            for hashed in arr:
                toadd = hashed[0]
                toadd.index = hashed[1]
                # dirname/filenanem.mkv.bz2
                toadd.file = ".".join(filename.split("/")[-1].split(".")[:-1])

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
    avarage = 0
    maximum = 0
    minimum = 9999
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

        # if it doesnt match it means that tree search was too low 6 for me was good.
        # adding more means more to compare so its a speed tradeoff.
        # test what you need
        if(boolable):
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
            #print("NIBY PRAWIDLOWE: ", len(list(elem for elem, count in element_counts.items())))
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
        print("Current: ", howmucprocessed + above500matches, " Misses: ", misses, "Avarage: ", avarage / howmucprocessed,
              " Max: ",
              maximum, " Min: ", minimum, " Above 500matches:" + str(above500matches), " Recalculation: ",  str(differentmatches))

        # Current - currently processed frames (amount)
        # misses - how many frames did not match samples
        # avarage - avarage difference between frames numbers
        # maximum - maximum difference between frames
        # minimum - similar to maximum
        # above 500 matches - how many frames were above 500 frames difference (if you need to match exact frames of video this seems usefull stat)
        # recalculation - when tree won't find anything to search realistially a next search should occur then with hamming distance of 8 perhaps 10. (Comment somewhere above)

def hamming_distance(x, y):
    return bin(x.int ^ y.int).count('1')

if __name__ == "__main__":
    samples = []
    sample_dir = "samples"
    processed_dir = "processed"

    print("Preprocessing samples")
    for sample in tqdm.tqdm(os.listdir(sample_dir)):
        to_load = os.path.join(sample_dir, sample)
        hash = imagehash.crop_resistant_hash(PIL.Image.open(to_load), hash_func=custom_hash_func(imagehash.phash))
        hash.index = sample.split(".")[-2]
        hash.file = ".".join(sample.split(".")[:-2])
        samples.append(hash)

    tree = pybktree.BKTree(hamming_distance)

    for file in os.listdir(processed_dir):
        print(file)
        loadtotree(os.path.join(processed_dir, file), tree)

    checkable(samples, tree)
