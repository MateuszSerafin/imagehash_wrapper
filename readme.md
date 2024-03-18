imagehash_wrapper
========

imagehash_wrapper is a wrapper around imagehash using pybktree and other libraries. What it allows you to hash images, videos and check if they already exist in your database using simple function calls. You don't have to implement anything on your own mess around with settings etc.

Install depedencies

    pip install pybktree imagehash python-opencv psutil

Then you need to copy wrapper_imagehash.py to your project, I might or might not upload it to pip. For now copying is the way.

## Example usage

    custom = Wrapped(savedir="mydirectory")

    custom.add_video("vid1.mp4")

    #False means not found
    assert custom.match_video("vid2.mp4", hamming_distance=3).get_data() == False

    #Increasing hamming distance makes it match frames that are not necessary from same video.
    #This cannot be changed as matching less similar images literary means that it can match somethning that is different
    #matches vid1 even we put vid2 as a reference
    assert custom.match_video("vid2.mp4", hamming_distance=12).get_data() == "vid1.mp4"

    custom.add_video("vid2.mp4")

    #However after adding vid2 to binary tree it became the best match even with same hamming_distance please be aware of this behaviour
    assert custom.match_video("vid2.mp4", hamming_distance=12).get_data() == "vid2.mp4"

    #screen shot includes part of windows player, it changes hashes therefore it needs increased hamming distance
    #If windows player would be cropped out hamming_distance of 3 would be enough
    #Please take this information to consideration with your project
    #TODO do test to make sure that frames are matched within sensible amount of frames
    assert custom.match_frame("screenshotvid1_54.png", hamming_distance=16).get_data() == ("vid1.mp4", 64)

    #Check to make sure that loading is working properly
    assert list(Wrapped(savedir="mydirectory")._tree) == list(custom._tree)
## Benchmarks
TODO, my implementation is working but not sure where is limit of for example 8 bit hashes, not sure about it's speed on scale, 

## Acknowledgements 
[imagehash](https://github.com/JohannesBuchner/imagehash) - Code for image hashing, base of my wrapper
<br> [pybktree](https://github.com/benhoyt/pybktree) - Code for binary tree, no need to reinvent the wheel working nicely.