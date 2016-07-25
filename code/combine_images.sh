#!/bin/bash
# Convert the normal files in $1 to animation in $3
IMG_ARR=($1/*.jpg)
FILENAME=$(basename "$IMG_ARR")
FILENAME=${FILENAME:0:25}
convert -delay 0 -loop 0 -resize 50% $1/*.jpg $3/"$FILENAME".gif

# Convert the diff files in $2 to animation in $3
IMG_ARR=($2/*.jpg)
FILENAME=$(basename "$IMG_ARR")
FILENAME=${FILENAME:0:25}
convert -delay 0 -loop 0 -resize 50% $2/*.jpg $3/"$FILENAME".gif

# Make join animation from normal and diff files in $1 and $2. Copy all over, append, make gif, clean up.
cp $1/*.jpg $3
cp $2/*.jpg $3

for f in $3/*norm*.jpg; do
convert $f ${f/"norm"/"diff"} +append ${f/"norm"/"both"}
done

rm $3/*norm*.jpg
rm $3/*diff*.jpg

IMG_ARR=($3/*.jpg)
FILENAME=$(basename "$IMG_ARR")
FILENAME=${FILENAME:0:22}
convert -delay 0 -loop 0 -resize 50% $3/*.jpg $3/"$FILENAME"_both.gif
rm $3/*.jpg
