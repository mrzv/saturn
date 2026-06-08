#m> # Checkpoint Cache Example
#m>
#m> The first Saturn run saves a checkpoint after the expensive setup. The next
#m> run can skip directly to the checkpoint if the preceding code has not changed.

import time

time.sleep(1)
value = 42

#chk>

print(value)
