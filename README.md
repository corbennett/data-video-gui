# data-video-gui
Gui for annotating video and comparing it with simultaneous data streams

## Installation
Requires conda. Following instructions for Windows (OS should work with minor modifications),

1) Download repo to some local folder

2) Open cmd window and navigate to folder

3) Make conda environment with environment.yml

    conda env create -f environment.yml
   
4) This creates a python 2.7 environment called 'lickAnnotation'. Activate this environment and run the gui:
    
    activate lickAnnotation
    python lickVideo.py
    
## Use

Use toolbar to open video file and load a corresponding annotation file (if one exists).

### Basic video controls
Once video is loaded, use the buttons to control display:

* Play: toggles video play on and off
* Frame text input: Displays current frame. Enter value to jump to specific frame. Value just after end of box indicates total frames for this video.

Or, use the following shortcuts to control display (focus must be on image window, so click image first if these aren't working):

* Spacebar: Plays video (repeated presses toggle play on and off)
* Left arrow: go back one frame. Hold to rewind.
* Right arrow: advance one frame. Hold to play.

### Set field of view
Click the image and drag to pan. 

Use scroll wheel to zoom. (Focus must be on image window, so click image first if this isn't working).


### Annotate frames
To control annotation, either click the corresponding radio button on the frame you wish to annotate or use the following shortcuts (not case sensitive):

* 'L': annotate lick for current frame
* 'N': annotate no lick for current frame (default)
* 'C': annotate 'other contact' for current frame

Remember to save annotations when finished (toolbar, "Save Annotation Data"). The next time you load this annotation data with the corresponding video, the video will automatically advance to the last annotated frame.
