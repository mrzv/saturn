#m# # Sample Saturn Notebook
#m#
#m# Some **test** *markup*:
#m#  - item 1
#m#  - item 2
#m#
#m# First, we import some necessary boilerplate.

import sys, os
import numpy as np

#m# Set up the matrix `a` on which we operate.

a = np.random.random((10,20))

#m# We can examine `a`'s shape:

print(a.shape)

#o# (10, 20)

a.shape

#o# (10, 20)

## Is this the best demarkation of the evaluated expression?

b = 5

#-#

print(b)

#o# 5
