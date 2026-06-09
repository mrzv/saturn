from pathlib import Path

if __name__ == '__main__':
    #m> Main-guard notebook body
    marker = Path('main-guard-compat.marker')
    marker.write_text('ran')
    value = 40
    #---#
    print(value + 2)
else:
    print('imported')
