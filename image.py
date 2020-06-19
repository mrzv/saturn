import pixcat
import PIL
import numpy
import matplotlib
import matplotlib.pyplot as plt
import io
import os

def enabled():
    return os.environ['TERM'] == 'xterm-kitty'      # TODO: find a better way

def display(result):        # determine if we can display this type
    return type(result) is matplotlib.image.AxesImage

def show():
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    im = PIL.Image.open(buf)
    pixcat.Image(im).show()
