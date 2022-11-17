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

function run_test
{
    fn=$1
    echo "Testing" $fn

    if $DIR/../saturn.py run $fn $fn.tmp > $fn.tmp-out; then
        if diff $fn.tmp $fn.expected > /dev/null; then
            echo $Green "   Expected transformation" $Color_Off
            rm $fn.tmp
        else
            echo $Red "   Failed transformation" $Color_Off
            res=1
        fi

        if diff $fn.tmp-out $fn.expected-out > /dev/null; then
            echo $Green "   Expected output" $Color_Off
            rm $fn.tmp-out
        else
            echo $Red "   Failed output" $Color_Off
            res=1
        fi
    else
        echo $IRed "   Failed execution!" $Color_Off
        res=1
    fi
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
        $DIR/../saturn.py run $fn $fn.expected > $fn.expected-out
        res=$?
        ;;
    "") # run all
        for fn in `ls $DIR/*.py`; do
            run_test $fn
        done
        ;;
    *)  # run specific
        run_test $1
        ;;
esac

exit $res
