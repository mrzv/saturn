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

#chk>{{{
#chk>gASVJAAAAAAAAABDIJZCQePiVH9SX7wVtBfgrDpcgWu5HUFFiFEeyNF9sVjFlC6ABJVuBwAAAAAAAH2U
#chk>KIwIX19uYW1lX1+UjAhfX21haW5fX5SMDF9fYnVpbHRpbnNfX5RjYnVpbHRpbnMKX19kaWN0X18KjANz
#chk>eXOUjApkaWxsLl9kaWxslIwOX2ltcG9ydF9tb2R1bGWUk5SMA3N5c5SFlFKUjAJvc5RoB2gLhZRSlIwC
#chk>bnCUaAeMBW51bXB5lIWUUpSMAWGUaAWMDV9jcmVhdGVfYXJyYXmUk5QojBVudW1weS5jb3JlLm11bHRp
#chk>YXJyYXmUjAxfcmVjb25zdHJ1Y3SUk5RoD4wHbmRhcnJheZSTlEsAhZRDAWKUh5QoSwFLCksUhpRoD4wF
#chk>ZHR5cGWUk5SMAmY4lImIh5RSlChLA4wBPJROTk5K/////0r/////SwB0lGKJQkAGAABAjHR84sfWP5jr
#chk>cYEl4r8/jCCA9Wwizj8cZEVTR+3HP5Hp3bN0Leo/EHBrJcY+xD85P3ELq9TkPyKb3kqRg+s/h+r/MI+z
#chk>6z+IWOQh1JDYP1zBP2/gJuE/bDo0XS+FwT8xQ9Lg6N3pPx69g6Hrwu4/B8QhD2Yn4T9wWyLvoMrCP0Bh
#chk>ZyNRQMQ/aqoXZx2U0j8o4ZjYpwXoP6DRtzVasLI/FfazVjl+4z+AFFmuYT+NPwX/E+l8tes/Y4yVFE4I
#chk>7z82Ty8Jl5TcP+7eH81/3tI/U43qw1BZ5D+IwuVcwXfLP6GTTJnLa+0/TEoyzqUU6z9gTTBWhYmpP+Ae
#chk>ObvdXJY/kzvXDcT+6D94wOs99xvAP5ghuk+bcOc/80hcqziA6z8OlwCWB8LoPy+EJlaFmeE/NIn46oMw
#chk>4D8qFBcgtzrYP7a1iPAZfeA/A+PUCN7w4D9MGbAZlr7dP0/lWU5eoeo/cMSUITRO4D+wyzavKFu4P/Rr
#chk>J5Dm09I/GTr9acWL6z9bXvOZzy3kP+dG+PYWdOQ/fDf5M78c2z81H7RGSCLtPzX02dwwWuQ/IOCBomK2
#chk>mD/8IW7qzG3fPwD7+P9ka9s/3J7rCNofzz9bTabsgEDrPyyxGPINf9w/jqs41sN34z/2eSOfWovoP0x9
#chk>//bryeA/YO48CWsA4z9ACtz9d7WmPyJ4fnevWtc/WkGQV66y0z+Sre2i4cfXP3RQ2ECiAs0/J8fC4cvp
#chk>5j8u0+JGBXbWP+sM7BnFAe4/ihPE8z5w7z+9d2vQxr3oP/I5hG6Axts/Tqiea9CX2D/J2lG4K+3lP3vE
#chk>HNRxv+M/WEhmPtH1xT8KdRjAQ5DTP3i0s6o2bOo/7oQjLAqr5T/6UUf0K0LZP1ELUP8GDuk/uu6oYBt/
#chk>1z/d5gN+rxPrPx8uxh2+6ew/3naBtWSk2j+sjHpSsizbP6AFcOKN8Zs/FIUGPmgKxz9Ga6MoDaPiP9xj
#chk>WIM7a+M/JlNJAG4W0j8wsc2HuPDpP85340krReM/iNvWzMfqwj9acPIi2STsP3sWnFpiGuI/tD9EZHrv
#chk>4z8vBTSbVAjtP3SqkGq0QME/ZRpDSshD5D88BUQ4S9XRP0jiRwKpjNY/BBIHHDWZzT9oHnttoSy0P1B2
#chk>fMEWhMo/p04ZOqoo5T9OutSXH77qP+i5XQbdaNU/eMG65gXQuz9zffGF/RbhPwjr3+LhwcI/h8z5tPzn
#chk>7D8SXG2KflXUP1j57b1Jh+s/LRMBRbnA7j9OQlRZJBrWP2g3jiGQXe0/zMoAyrslwj/cm0iIwhbrP12F
#chk>pigvtus/KJsVouql4T8U8Y49KBrLP5A9StbZcas/jnKwRRhi2z8I/Nnmw27IP1JxuUBU+ds/sUvyQiix
#chk>7T8v4pS2bSbtP8IdHEiWaN4/zFQmbkTE6j8CR2h6qqDjPwoSXQCJQO4/G8n7w2kv4T88howqDT7rP7qd
#chk>Hrc9zto/cZ8HMNhP7D+gzFHBZoTUP3T6jmRmleE/DmZcO4tZ3j8EjLJfnlrrP+j3cdAFr9o/U1XPHkUo
#chk>6j9IhoL3QQLVP3xou9hfouc/oNwOqM1PoD/AI9yGWrKJP/5s+Ul5fts/GDs/leqc2j+XFEkzTknoP2ac
#chk>3K3eANA/UppmzAwK6D/iwp0CVLXUP6+6HoLGo+4/IIv/2sq7vz80vjMNjjfFP+43G1YwaO0/HYg41qQK
#chk>6z8zwRgZ3KXvPyGK3vJVHeI/8mSPNSy26T9j7FIPps/qP+5v/8x6nOQ/BMzg87jKyz8qX+LDnzffP5CC
#chk>2wploO0/xkcIfkGF6D8ME6IyYmnuP4J11i6on+s/0JjGZX7O1j/R7hGiEPrqPyFUY9xd5OM/un3cv05n
#chk>3D+QcKoSWFjTP9I4c0yDW+4/SgrmDDyN1T/8+QVbUObjP7DQrPmaPME/RfRAYjl56D/uaHNQBNnUP11y
#chk>Hy+e7+w/ICB8/h8iqD9gKg6pMJCUPw6GC7YTWd0/AZyE7XN15T/YD1r6pBjiP2yFqLK1yuI/TILsDtVG
#chk>0T8X53wYkEjoPxoaoQe3B+k/MnhjgCGZ6j8ljGlJnYXsPwDNs6owN7I/k5j5EukR4z9L16RDId/rP9yC
#chk>xniks9U/XHKqTEe2zT8AXBUzwI/kP4R1HZVtGtw/lHSUTnSUUpR1Lg==
#chk>}}}

## Is this the best demarkation of the evaluated expression?

b = 5

#---#

print(b)

#o> 5

import matplotlib.pyplot as plt
plt.matshow(a)
plt.show()

#o> png hash=d925a746463c085a.png

# vim: ft=python foldmethod=marker foldlevel=0
