imagehash_wrapper
========

imagehash_wrapper is a wrapper around imagehash using pybktree and other libraries. What it allows you to hash images, videos and check if they already exist in your database using simple function calls. You don't have to implement anything on your own mess around with settings etc.

Install depedencies 
::

    pip install pybktree imagehash python-opencv psutil

Then you need to copy wrapper_imagehash.py to your project, I might or might not upload it to pip. For now copying is the way.

.. code:: python

    >>> from wrapper_imagehash import Wrapped()
    >>> instance = Wrapped()
    >>> instance.add_video("vid1.mp4")
    >>> instance.add_video("vid2.mp4")
    #match_frame tries to match frame that matches best in this case its vid1 448th frame
    >>> instance.match_frame(PIL.Image.open("screenshotvid1.png"))
    ('vid1.mp4', 448)
    >>> instance.match_video("vid2.mp4")
    'vid2.mp4'
    #Vid3 not added to the tree result unknown, increasing hamming distance might yield not wanted results
    >>> type(instance.match_video("vid3.mp4"))
    <class 'NoneType'>

My lib allows also is not only for videos but supports images too. Please look at class definition
### class Wrapper:
#### .__ init __(savedir: os.path, hashfunc: CustomHashFunc)
###### savedir, if save dir is specified all of added images videos when computed will be added to this directory. When creating instance it will also load this data.

###### hashfunc, I am using currently imagehash.cropresistanthash you can change to phash or type of hash however you need to change it please look at my code how it looks like.

#### .add_image_pil(image: PIL.Image.Image, filename: str) -> bool
This will add image to internal database make sure that filename is unique otherwise it will reject it. It will result false if it encounters issue and true if it sucessfully worked.

#### .add_image(file: os.path) -> bool
Internally calls add_image_pil, please make sure that this file exist currently not a lot of issue handling is implemented. False = failed

#### .add_video(filename: os.path, leavethismuchmemory: int)
###### leavethismuchmemory, i am using multiprocessing for faster computing of hashes, make sure to put a sensible limit on it otherwise while processing big files it might take 95% of your ram

#### .match_video(file: os.path, hamming_distance: int) -> str
###### hamming_distance, put higher value the more your frame is disorted.
It might return None be carefull, it will return None only if it won't find anything in internal database (within hamming_distance), Otherwise it returns a exact filename of video that matches the best

#### .match_frame(image: PIL.Image.Image, hamming_distance:int) -> tuple(str, int)
Bassically the same as above function difference is you call it with a single frame and it results in tuple with filename and framenumber that most fits. 

#### .match_one_video_multiple_frames(self, listImages: list[PIL.Image.Image], hamming_distance=24) -> str
Internally match_video calls this function, if you have multiple screenshots of same video you can call that and it takes account of all frames to match a video.