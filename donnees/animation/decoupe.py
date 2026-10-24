"""Découpe d'Abyssor en calques animables (ailes, tête, bras, corps), avec chevauchements aux jointures."""
from PIL import Image, ImageDraw
import numpy as np
from pathlib import Path
ICI=Path(__file__).resolve().parent/'abyssor'
_s=Image.open(ICI/'source.png').convert('RGBA'); src=_s.convert('RGB')
a=np.asarray(src).astype(int)
m=np.asarray(_s.getchannel('A'))>0
m&=~((a[...,2]>a[...,0]+25)&(a[...,2]>70))   # restes bleus vifs du décor
def poly(pts):
    im=Image.new('L',src.size,0); ImageDraw.Draw(im).polygon(pts,fill=255); return np.asarray(im)>0
P={
 'bras':  [(845,430),(985,395),(1190,640),(1190,910),(930,910),(870,700),(820,520)],
 'aile_g':[(0,0),(405,0),(405,270),(330,395),(105,615),(0,615)],
 'aile_d':[(865,0),(1254,0),(1254,640),(1150,640),(985,430),(890,330),(865,260)],
 'tete':  [(415,0),(845,0),(855,270),(770,420),(690,525),(570,525),(490,420),(405,270)],
}
from scipy import ndimage
hsv=np.asarray(src.convert('HSV')).astype(int)
clair=(hsv[...,0]<38)&(hsv[...,1]<150)&(hsv[...,2]>120)
# pointes d'épaule : restent sur le corps / le bras (pas sur l'aile)
epaules=np.zeros_like(m); epaules[255:430,240:400]=True; epaules[255:430,855:1015]=True
pointes=ndimage.binary_dilation(clair&epaules,iterations=3)&m
zones={}
pris=np.zeros_like(m)
for k in ['bras','aile_g','aile_d','tete']:
    z=m&poly(P[k])&~pris
    if k.startswith('aile'): z&=~pointes
    zones[k]=z; pris|=z
zones['corps']=m&~pris
# chevauchements : le corps passe un peu sous chaque morceau, et chaque morceau mord un peu sur le corps
base=zones['corps'].copy()
ailes=zones['aile_g']|zones['aile_d']
zones['corps']=base|(m&ndimage.binary_dilation(base,iterations=16)&~ailes)|(m&ndimage.binary_dilation(base,iterations=3)&ailes)
for k in ['bras','aile_g','aile_d','tete']:
    zones[k]=zones[k]|(m&ndimage.binary_dilation(zones[k],iterations=8 if k.startswith('aile') else 5)&base)
rgba=np.dstack([np.asarray(src),np.zeros(m.shape,np.uint8)])
for k,z in zones.items():
    t=rgba.copy(); t[...,3]=z*255; Image.fromarray(t).save(ICI/'calques'/f'{k}.png')
col={'bras':(255,200,0),'aile_g':(0,160,255),'aile_d':(0,255,200),'tete':(255,0,255),'corps':(255,60,60)}
dbg=np.zeros((*m.shape,3),np.uint8)
for k,z in zones.items(): dbg[z]=col[k]
Image.fromarray(dbg).resize((500,500)).save(ICI/'zones.png')
