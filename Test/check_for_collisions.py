import os
import bz2
import pickle
import imagehash
import tqdm as tqdm

def calculate_size(hash: imagehash.ImageMultiHash) -> int:
    amount = len(hash.segment_hashes)
    size_bytes = hash.segment_hashes[0].hash.nbytes
    return amount * size_bytes

def set_check(dict: dict, mutliHash: imagehash.ImageMultiHash):
    for segment in mutliHash.segment_hashes:
        stringed = str(segment)
        if(stringed in dict):
            dict[stringed] += 1
        else:
            dict[stringed] = 0

#we want to remove all unique hashes and keep only duplicates or the ones that were matched more than 10 times
#number 10 is totally random i do not have any reason to take this number you can clone it and test with 5
def sieve(dict: dict):
    above_10 = {k: v for k, v in dict.items() if v > 10}
    return above_10

if __name__=="__main__":
    frame_counter = 0

    #i used different hashes 8,12,16 size
    byte_counter8 = 0
    byte_counter12 = 0
    byte_counter16 = 0

    processed_dir = "processed"

    #you can make it to know which exact frame is causing set to go up but for my use it's unnecessary
    set_8 = dict()
    set_12 = dict()
    set_16 = dict()


    for processed in tqdm.tqdm(os.listdir(processed_dir)):
        file = bz2.BZ2File(os.path.join(processed_dir,processed), "rb")
        depickled = pickle.load(file)

        for tuple_8_12_16 in depickled:
            #made mistake, but already processed data
            #[0] shouldn't be in there. Changes nothing less clear code
            byte_counter8 += calculate_size(tuple_8_12_16[0][0])
            byte_counter12 += calculate_size(tuple_8_12_16[0][1])
            byte_counter16 += calculate_size(tuple_8_12_16[0][2])

            set_check(set_8, tuple_8_12_16[0][0])
            set_check(set_12, tuple_8_12_16[0][1])
            set_check(set_16, tuple_8_12_16[0][2])

    sieved8 = sieve(set_8)
    sieved12 = sieve(set_12)
    sieved16 = sieve(set_16)

    print(len(sieved8))
    print(len(sieved12))
    print(len(sieved16))
