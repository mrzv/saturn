import pathlib


if __name__ == '__main__':
    #m> # Main-Guard Notebook
    #m>
    #m> This file can run directly with Python or as a Saturn notebook.

    value = 40

    #chk>

    print(value + 2)
else:
    pathlib.Path('/tmp/saturn-main-guard-imported').write_text('imported')
