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
                frame_id = loaded[2].split(".")[-2]
                name_of = ".".join(loaded[2].split(".")[:-2])
                kontener = container(name_of, frame_id)
                arr.update({loaded[0]: kontener})
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

    Item = collections.namedtuple('Item', 'int list')

    try:
        while True:
            arr = pickle.load(file)
            for hashed in arr:
                for segment_hash in hashed[0].segment_hashes:
                    hexed = int(str(segment_hash),16)
                    myhexedszajs = Item(hexed, [])
                    found = tree.find(myhexedszajs, 0)

                    if(len(found) != 0):
                        for nbr,fnd in found:
                            fnd.list.append(container(".".join(filename.split(".")[:-1]), hashed[2]))
                    else:
                        tree.add(myhexedszajs)

    except (EOFError):
        pass
    file.close()


class container():
    def __init__(self, file:str, index:int):
        self.file = file
        self.index = int(index)


    def __eq__(self, other):
        return

    def __str__(self):
        return self.file + "."+ str(self.index)


def hamming_distance(x, y):


    return bin(x.int ^ y.int).count('1')

if __name__ == "__main__":
    imges = {}
    load("ZDJECIA.BZ28", imges)

    tree = pybktree.BKTree(hamming_distance)

    dir = "8multihash/"

    for file in os.listdir(dir):
        print(file)
        if(not "bz28withresistant" in file): continue
        loadtotree(dir+file, tree)


    """

    files  = os.listdir(dir)


    file = bz2.BZ2File(dir+files[0], 'rb')
    Item = collections.namedtuple('Item', 'int list')

    arr = pickle.load(file)
    sgmnt =  int(str(arr[0][0].segment_hashes[0]),16)
    print(sgmnt)



    avarage = tree.find(Item(sgmnt, []), 0)

    for at,nop in avarage:
        for i in nop.list:
            print(i)


    """


    filematches = 1
    notmatches = 0

    diffaa = 1

    loops = 0

    Item = collections.namedtuple('Item', 'int list')

    for hash,imgkontener in imges.items():
        vidmatches = {}

        for segment_hash in hash.segment_hashes:
            sgmnt = int(str(segment_hash), 16)
            majszajs = Item(sgmnt, [])

            for matchint,matchlist in tree.find(majszajs, 6):
                for kontener in matchlist.list:
                    stringable = kontener.file
                    kontenerindex = kontener.index

                    if(stringable in vidmatches):
                        dictmoj = vidmatches.get(stringable)
                        if(kontenerindex in dictmoj):
                            dictmoj.update({kontenerindex: dictmoj.get(kontenerindex) + 1})
                        else:
                            dictmoj.update({kontenerindex: 1})
                    else:
                        vidmatches.update({stringable: {kontenerindex: 1}})


        potentialframe, currentmax, currentmaxstring = 0, 0,""

        for stringfile, dictofindexes in vidmatches.items():

            for index,matchesamnt in dictofindexes.items():
                if(matchesamnt > currentmax):
                    currentmax = matchesamnt
                    currentmaxstring = stringfile
                    potentialframe = index



        if(imgkontener.file != currentmaxstring.replace("8multihash/", "")):
                notmatches += 1
        else:
            filematches += 1
            diffinindex = abs(int(imgkontener.index) - int(potentialframe))
            diffaa += diffinindex
        loops += 1


        print("File matches: ", filematches, " Mój diff: " ,diffinindex, " Avg diff: ", diffaa/filematches, "NOT MATCHED: ", notmatches, " LOOPS: ", loops)


        """

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
        """