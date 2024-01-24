import os
import random
import PIL
import cv2
from PIL import Image

#This one is slow, but worked other one is fast but i had sometimes issues with it.
def findlengthofvid(fileloc):
    video_capture = cv2.VideoCapture(fileloc)
    counter = 0
    while video_capture.isOpened():
        ret, frame = video_capture.read()
        if not ret:
            break
        counter += 1
    return counter

def fastfindlengthofvid(fileloc):
    video_capture = cv2.VideoCapture(fileloc)
    return int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))

def processfile(fileloc, saveloc):
    print("Processing: ", fileloc)
    length = fastfindlengthofvid(fileloc)
    print("Found length: ", length)
    video_capture = cv2.VideoCapture(fileloc)
    lista = random.sample(range(1,length),10)
    counter = 0;
    #I know you can set cap into specific frame or at least second but i had some issues with some formats.
    #also its for testing so i didnt really care
    while video_capture.isOpened():
        ret, frame = video_capture.read()
        if not ret:
            break
        if(counter in lista):
            # yea exactly what you think happened
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            PIL.Image.fromarray(frame_rgb).save(os.path.join(saveloc, os.path.basename(fileloc) + "." +str(counter)+".png"),"PNG")
            print(counter)
        counter += 1
    video_capture.release()

if __name__=="__main__":
    videos_dir = "videos"
    sample_dir = "samples"

    if(not os.path.exists(sample_dir)):
        os.mkdir("samples")
    for dir in os.listdir(videos_dir):
        joined = os.path.join(videos_dir, dir)
        if(not os.path.isdir(joined)): continue
        for file in os.listdir(joined):
            movie = os.path.join(joined, file)
            processfile(movie, sample_dir)
