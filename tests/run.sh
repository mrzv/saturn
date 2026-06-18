#!/bin/sh

DIR="$(dirname $0)"

## Automatic cleanup on exit
#function finish
#{
#    rm -f $DIR/*.tmp
#    rm -f $DIR/*.tmp-out
#}
#trap finish EXIT

res=0

Color_Off='\033[0m'       # Text Reset
Red='\033[0;31m'          # Red
Green='\033[0;32m'        # Green
IRed='\033[0;91m'         # Red

# fix the output width
export COLUMNS=80

run_test() {
    fn=$1
    fixture=$(basename "$fn")
    uv run pytest "$DIR/test_cli_golden.py::test_cli_runs_legacy_golden_fixture[$fixture]" || res=1
}

trap "echo; exit" INT

case $1 in
    clean)
        echo "Cleaning"
        rm -f $DIR/*.tmp
        rm -f $DIR/*.tmp-out
        ;;
    generate)
        fn=$2
        $DIR/../saturn.py run $fn $fn.expected --inline > $fn.expected-out
        res=$?
        ;;
    "") # run all notebook fixtures with golden files
        uv run pytest "$DIR/test_cli_golden.py::test_cli_runs_legacy_golden_fixture"
        res=$?
        ;;
    *)  # run specific
        run_test $1
        ;;
esac

exit $res
