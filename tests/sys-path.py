import sys
sys.path.append('abcd')
#no-skip#

#---#

sys.path.append('def')

#---#

a = 5

#chk>{{{
#chk>gANDIO8jEwzEZHsNB3RGqYYvaJIDM+zoWTutyR4BC2OD+ErDcQAugAN9cQAoWAwAAABfX2J1aWx0aW5z
#chk>X19xAWNidWlsdGlucwpfX2RpY3RfXwpYAwAAAHN5c3ECY2RpbGwuX2RpbGwKX2ltcG9ydF9tb2R1bGUK
#chk>cQNYAwAAAHN5c3EEhXEFUnEGWAEAAABhcQdLBXUu
#chk>}}}

print(a)
#o> 5

print('abcd' in sys.path)
print('def' in sys.path)
#o> True
#o> True
