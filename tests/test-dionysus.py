# vim: ft=python foldmethod=marker foldlevel=0

import dionysus as d

#---#

simplices = [([2], 4), ([1,2], 5), ([0,2], 6),
             ([0], 1),   ([1], 2), ([0,1], 3)]
f = d.Filtration()
for vertices, time in simplices:
    f.append(d.Simplex(vertices, time))
f.sort()
for s in f:
   print(s)
#var> f

#---#

#var> f

m = d.homology_persistence(f)

#chk>

#---#

dgms = d.init_diagrams(m,f)
print(dgms)
#var> dgms
