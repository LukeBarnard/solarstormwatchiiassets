#!/bin/bash
cd $1
convert -delay 0 -loop 0 -resize 50% *stars_remove.png stars_remove.gif
convert -delay 0 -loop 0 -resize 50% *stars_keep.png stars_keep.gif
convert stars_keep.gif -coalesce k-%04d.gif
convert stars_remove.gif -coalesce r-%04d.gif
for f in k-*; do convert $f ${f/k/r} +append $f; done
convert -loop 0 -delay 0 k-*.gif stars_both.gif
rm k-*.gif
rm r-*.gif
