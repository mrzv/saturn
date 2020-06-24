import sys, io, contextlib

# From: https://stackoverflow.com/a/18854817/44738
def chunkstring(string, length):
    return (string[0+i:length+i] for i in range(0, len(string), length))
