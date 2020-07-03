from joblib import Parallel, parallel_backend, delayed

#---#

def f(i):
    return i * 10

#---#

trials = 100

#---#

print(trials)

with parallel_backend('loky', n_jobs = 2):
    lst = Parallel()(delayed(f)(i) for i in range(trials))

#chk>

print(lst)

#---#

lst2 = [2*i for i in range(trials)]

#---#

print(lst2)
