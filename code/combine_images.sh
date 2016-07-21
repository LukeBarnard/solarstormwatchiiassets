#!/bin/bash
cd $1
convert -delay 0 -loop 0 -resize 50% *norm.png norm.gif
convert -delay 0 -loop 0 -resize 50% *diff.png diff.gif
for f in *norm.png; do
convert $f ${f/"norm"/"diff"}+append ${f/"keep"/"both"}
done
convert -loop 0 -delay 0 *both.png both.gif
rm *both.png