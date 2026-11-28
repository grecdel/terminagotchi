#!/bin/sh
# capt.sh NOM n1 n2 : intègre les captures screenshot-*-n1.png et -n2.png
N=$(python3 -c "import sys,unicodedata;print(unicodedata.normalize('NFKD',sys.argv[1]).encode('ascii','ignore').decode().replace(' ','_'))" "$1"); shift; set -- "$N" "$@"
D=$(ls -dt /tmp/claude-chrome-screenshots-* | head -1)
g=$(ls "$D"/screenshot-*-"$2".png) ; d=$(ls "$D"/screenshot-*-"$3".png)
cd /home/claude/depot-android/donnees/bestiaire2 && python3 integrer.py "$g" "$d" "$1" >/dev/null 2>&1 && echo "OK $1 $(ls images/$1_*.png | wc -l)" || echo "ECHEC $1"
