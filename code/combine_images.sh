#!/bin/bash
# Convert the normal files in $1 to animation in $3
IMG_ARR=($1/*$2*.jpg)
FILENAME=$(basename "$IMG_ARR")
FILENAME=${FILENAME:0:25}
convert -delay 0 -loop 0 -resize 50% $1/*$2*.jpg $4/"$FILENAME".gif

# Convert the diff files in $2 to animation in $3
IMG_ARR=($1/*$3*.jpg)
FILENAME=$(basename "$IMG_ARR")
FILENAME=${FILENAME:0:25}
convert -delay 0 -loop 0 -resize 50% $1/*$3*.jpg $4/"$FILENAME".gif

# Make join animation from normal and diff files in $1 and $2. Copy all over, append, make gif, clean up.
cp $1/*.jpg $4

for f in $4/*$2*.jpg; do
convert $f ${f/"$2"/"$3"} +append ${f/"$2"/"both"}
done

rm $4/*$2*.jpg
rm $4/*$3*.jpg

IMG_ARR=($4/*.jpg)
FILENAME=$(basename "$IMG_ARR")
FILENAME=${FILENAME:0:25}
convert -delay 0 -loop 0 -resize 50% $4/*.jpg $4/"$FILENAME".gif
rm $4/*.jpg
