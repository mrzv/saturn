from tqdm import tqdm
import time

fmt = '{l_bar}{bar}| {n_fmt}/{total_fmt}'       # to avoid diff errors

#---#

for i in tqdm(range(20), bar_format=fmt):
    time.sleep(.1)

#---#


for i in tqdm(range(10), bar_format=fmt):
    for j in tqdm(range(30), bar_format=fmt, leave = False):
        time.sleep(.05)
