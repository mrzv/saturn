#m> # Sample Saturn Notebook
#m>
#m> Some **test** *markup*:
#m>
#m>  - item 1
#m>  - item 2
#m>
#m> First, we import some necessary boilerplate.

import sys, os
import numpy as np

#m> Set up the matrix `a` on which we operate.

a = np.random.random((10,20))

#m> We can examine `a`'s shape:

print(a.shape)

#o> (10, 20)

a.shape

#o> (10, 20)

#chk>

## Is this the best demarkation of the evaluated expression?

b = 5

#---#

print(b)

#o> 5

import matplotlib.pyplot as plt
plt.matshow(a)
plt.show()

#o> <matplotlib.image.AxesImage object at 0x113a35590>

# vim: ft=python foldmethod=marker foldlevel=0
