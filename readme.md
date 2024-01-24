# video-hash

## What is it?
My test implementation using imagehash (https://github.com/JohannesBuchner/imagehash) to detect what video is playing. And match it to nearest frame.

## Usage
1. Put your videos in videos folder. Assume structure of videos/SHOWS1/ep1.mp4/webm anything cv2 supports
2. Preprocess videos using PreProcessVideos.py
3. Run GenerateRandomSamples.py to generate random frames from video
4. Use BinaryTreeImplementation.py to match sample frames to videos (more for testing and how i implemented it)
4. Have realization that there is other repo doing it better, although if you wan't it just in plain python this might not be that bad


## Additional Info
If you look into implementation by default it uses 8 bits to store information. I checked and it was alright for like 10 series each 10 seasons around 10 episodes 30 minutes. 
Also it stores just every 4th frame probably every 10th frame is close enough. So you can change it. OldTesting folder contains lot's of previous tests i did, this was really never meant to see github so all of it is mess. Only main source code is clean up.
<br />
Long story short with samples you can see in this repo and default settings it has like 95% match rate.
Sample output from BinaryTreeImplementation
<br />
Current:  828  Misses:  25 Avarage:  13.52774352651048  Max:  33616  Min:  0  Above 500matches:17  Recalculation:  28
<br /> 
Using default comparasions in lists it's really slow (more than 20 minutes per frame). It took 10 minutes on my PC to iterate through all samples.


## Warning
Currently i store information about each frame in each frame. Which results in higher memory usage. You can probably half or even more memory usage by chaning so each frame just stores like an index of which show is it. Rather than whole name of movie.
Because it's dead project i won't fix it. Also because of it i didn't implement check when adding frames to see if anything is close. E.G each show has some dark frames or whole black ones. It will probably spit random show when feed frames that could be in different show. If it's unique it works. (Dead project why bother implementing it)
## About it
This was a side project, idea was to create a website that would match screen shot to video currently playing.
There is something like that (https://github.com/soruly/trace.moe). But i looked at it too late and this project was almost instantly dead. 