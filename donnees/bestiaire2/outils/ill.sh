#!/bin/sh
# ill.sh NOM n1 n2 : assemble les 2 moitiés d'une illustration -> illu/NOM.png
D=$(ls -dt /tmp/claude-chrome-screenshots-* | head -1)
python3 - "$1" "$D"/screenshot-*-"$2".png "$D"/screenshot-*-"$3".png <<'PY'
import sys
from PIL import Image
n,a,b=sys.argv[1:4]
a=Image.open(a).convert('RGB'); b=Image.open(b).convert('RGB')
c=Image.new('RGB',(a.width+b.width,a.height)); c.paste(a,(0,0)); c.paste(b,(a.width,0))
bb=c.point(lambda v:255 if v>8 else 0).convert('L').getbbox(); c=c.crop(bb)
c.save(f'/tmp/claude-0/-home-claude/cfd82251-4fa5-55cd-8b51-4f0548d9aa8a/scratchpad/illu/{n}.png'); print(n,c.size)
PY
