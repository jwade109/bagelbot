FILE=$1
EXPR=$2

grep -nir "$EXPR" $FILE --binary-files=text --color -C 5
