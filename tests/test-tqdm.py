from tqdm import tqdm
import time

for i in tqdm(range(20), bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}'):
    time.sleep(.1)