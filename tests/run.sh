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

function run_test
{
    fn=$1
    echo "Testing" $fn

    if $DIR/../saturn.py run $fn $fn.tmp > $fn.tmp-out; then
        if diff $fn.tmp $fn.expected > /dev/null; then
            echo "   Expected transformation"
            rm $fn.tmp
        else
            echo "   Failed transformation"
            res=1
        fi

        if diff $fn.tmp-out $fn.expected-out > /dev/null; then
            echo "   Expected output"
            rm $fn.tmp-out
        else
            echo "   Failed output"
            res=1
        fi
    else
        echo "   Failed execution!"
        res=1
    fi
}

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
