# vim: ft=python foldmethod=marker foldlevel=0

import numpy as np
import matplotlib.pyplot as plt

#---#

np.random.seed(42)

#---#

for i in range(3):
    a = np.random.random((30,30))
    print(i, a.shape)
    plt.matshow(a)
    plt.show()
