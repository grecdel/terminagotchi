import animer as A
from PIL import Image, ImageDraw, ImageEnhance, ImageFont
import numpy as np, math, random
from scipy import ndimage
L=A.L; W,H=A.W,A.H; PIV=A.PIV; YEUX=A.YEUX
def hsv(im): return np.asarray(im.convert('RGB').convert('HSV')).astype(int)
def beige(im):
    h=hsv(im); return (h[...,0]<38)&(h[...,1]<150)&(h[...,2]>140)&(np.asarray(im)[...,3]>0)
def boucher(im):
    """referme les petits trous laissés à l'intérieur de la silhouette"""
    a=np.asarray(im).copy(); al=a[...,3]>0
    trous=ndimage.binary_fill_holes(al)&~al
    if trous.any():
        idx=ndimage.distance_transform_edt(~al,return_distances=False,return_indices=True)
        for c in range(3): a[...,c][trous]=a[...,c][idx[0][trous],idx[1][trous]]
        a[...,3][trous]=255
    return Image.fromarray(a,'RGBA')
def sans_pointes(im, ymax):
    a=np.asarray(im).copy(); b=beige(im); yy=np.mgrid[0:H,0:W][0]
    a[...,3][b&(yy<ymax)]=0
    return boucher(Image.fromarray(a,'RGBA'))
CORNES=[(213,5,294,124),(340,5,424,124)]
def cornes_mask(im):
    h=hsv(im); al=np.asarray(im)[...,3]>0
    b=((h[...,1]<175)|(h[...,2]<70))&al     # corne claire, ombrée ou contour (la peau rouge est très saturée)
    m=np.zeros_like(b)
    for x0,y0,x1,y1 in CORNES: m[y0:y1,x0:x1]=b[y0:y1,x0:x1]
    lab,n=ndimage.label(m); 
    if n: sz=ndimage.sum(m,lab,range(1,n+1)); m=np.isin(lab,1+np.where(sz>40)[0])
    return ndimage.binary_dilation(m,iterations=2)&(np.asarray(im)[...,3]>0)
def cornes_echelle(tete,f,nub=False):
    a=np.asarray(tete).copy(); cm=cornes_mask(tete)
    cor=a.copy(); cor[...,3]=np.where(cm,a[...,3],0)
    a[...,3][cm]=0; base=boucher(Image.fromarray(a,'RGBA'))
    if f>0:
        cimg=Image.fromarray(cor,'RGBA')
        for (x0,y0,x1,y1),bx in zip(CORNES,[(262,118),(372,118)]):
            part=cimg.crop((x0,y0,x1,y1)); part=part.resize((max(1,int(part.width*f)),max(1,int(part.height*f))),Image.BICUBIC)
            base.alpha_composite(part,(int(bx[0]-(bx[0]-x0)*f),int(bx[1]-(bx[1]-y0)*f)))
    if nub:
        d=ImageDraw.Draw(base)
        for x,y in [(265,112),(360,112)]:
            d.polygon([(x-9,y+8),(x+9,y+8),(x+2,y-10)],fill=(225,200,160,255),outline=(60,30,25,255))
    return base
def crete(im):
    a=np.asarray(im).copy(); h=hsv(im); z=np.zeros(a.shape[:2],bool); z[60:128,292:336]=True
    a[...,3][z&((h[...,1]<175)|(h[...,2]<70))]=0; return boucher(Image.fromarray(a,'RGBA'))
def bourgeons(im):
    d=ImageDraw.Draw(im)
    for x,y in [(268,116),(357,116)]:
        d.polygon([(x-10,y+8),(x+10,y+8),(x+2,y-12)],fill=(235,215,175,255),outline=(60,30,25,255))
def yeux_mignons(im):
    d=ImageDraw.Draw(im)
    for (x,y) in YEUX:
        d.ellipse([x-14,y-13,x+14,y+13],fill=(20,8,10,255)); d.ellipse([x-11,y-10,x+11,y+10],fill=(255,205,40,255))
        d.ellipse([x-6,y-6,x+6,y+8],fill=(15,5,10,255)); d.ellipse([x-5,y-6,x,y-1],fill=(255,255,255,255))
BOUCHE=(286,176,340,232)
def sans_crocs(im):
    a=np.asarray(im).copy(); b=beige(im); x0,y0,x1,y1=BOUCHE; z=np.zeros_like(b); z[y0:y1,x0:x1]=True
    r=b&z; a[...,0][r]=70; a[...,1][r]=12; a[...,2][r]=18
    return Image.fromarray(a,'RGBA')
def petits_crocs(im):
    d=ImageDraw.Draw(im)
    for dx in (-15,-6,6,15): d.polygon([(312+dx-3,190),(312+dx+3,190),(312+dx,201)],fill=(245,240,225,255),outline=(40,10,10,255))
def bouche_mignonne(im):
    d=ImageDraw.Draw(im); x,y=312,203
    d.ellipse([x-22,y-16,x+22,y+20],fill=(95,20,25,255),outline=(30,8,10,255),width=3)
    d.ellipse([x-14,y-4,x+14,y+14],fill=(170,50,60,255))
    for dx in (-10,10): d.polygon([(x+dx-4,y-14),(x+dx+4,y-14),(x+dx,y-3)],fill=(250,245,230,255))
def teinte(im,rgb,f): return A.teinte(im,rgb,f)
def variante(lum=1,sat=1,rose=0):
    def f(im):
        im=ImageEnhance.Color(im).enhance(sat); im=ImageEnhance.Brightness(im).enhance(lum)
        return teinte(im,(255,150,160),rose) if rose else im
    return f
# ---------------------------------------------------------------- bébé : rond, sans pointes, cornes-bourgeons, grands yeux
B={}
for k in L:
    im=sans_pointes(L[k],H)              # ni pointes ni griffes : tout rond
    if k=='tete': im=sans_pointes(cornes_echelle(sans_crocs(L[k]),0),H); im=crete(im); bourgeons(im); yeux_mignons(im); bouche_mignonne(im)
    B[k]=variante(1.12,0.8,0.12)(im)
# ---------------------------------------------------------------- jeune : petites cornes, pointes aux épaules seulement
J={}
for k in L:
    im=L[k]
    if k.startswith('aile'): im=sans_pointes(im,140)          # pas encore de griffes au bout des ailes
    if k=='tete': im=cornes_echelle(sans_crocs(im),0.55); petits_crocs(im)
    J[k]=variante(1.04,0.92)(im)
# ---------------------------------------------------------------- forme finale enrichie
def veines(im,graine,n=14):
    im=im.copy(); a=np.asarray(im)[...,3]>0; d=ImageDraw.Draw(im); rnd=random.Random(graine)
    ys,xs=np.where(ndimage.binary_erosion(a,iterations=6))
    if not len(ys): return im
    for _ in range(n):
        i=rnd.randrange(len(ys)); x,y=xs[i],ys[i]; ang=rnd.uniform(0,2*math.pi); pts=[(x,y)]
        for _ in range(rnd.randint(4,9)):
            ang+=rnd.uniform(-0.9,0.9); x+=math.cos(ang)*rnd.uniform(5,11); y+=math.sin(ang)*rnd.uniform(5,11)
            if not (0<=int(y)<H and 0<=int(x)<W and a[int(y),int(x)]): break
            pts.append((x,y))
        if len(pts)>2:
            d.line(pts,fill=(255,90,10,255),width=4); d.line(pts,fill=(255,230,120,255),width=2)
    return im
def epaulieres(im,cotes):
    d=ImageDraw.Draw(im)
    for (x,y,sens) in cotes:
        for i,(dx,dy,l) in enumerate([(0,0,34),(16*sens,12,28),(30*sens,26,22)]):
            bx,by=x+dx,y+dy; tip=(bx+sens*l*0.55,by-l)
            d.polygon([(bx-9,by+6),(bx+9,by+6),tip],fill=(230,210,170,255),outline=(40,15,15,255))
    return im
def troisieme_oeil(im):
    d=ImageDraw.Draw(im); x,y=316,126
    d.ellipse([x-9,y-12,x+9,y+12],fill=(15,5,10,255)); d.ellipse([x-6,y-9,x+6,y+9],fill=(120,255,255,255)); d.ellipse([x-2,y-4,x+2,y+4],fill=(255,255,255,255))
E={}
for k in L:
    im=L[k]
    if k.startswith('aile'): im=A.mise_echelle(im,PIV[k],1.3).rotate(-8 if k=='aile_g' else 8,center=PIV[k],resample=Image.BICUBIC)
    if k=='tete':
        im=A.mise_echelle(im,PIV['tete'],1.06)
        sup=Image.new('RGBA',im.size)
        cg=im.crop((205,5,290,110)); cd=im.crop((350,5,435,110))
        cg=cg.resize((int(cg.width*0.85),int(cg.height*0.85)),Image.BICUBIC).rotate(48,expand=True,resample=Image.BICUBIC)
        cd=cd.resize((int(cd.width*0.85),int(cd.height*0.85)),Image.BICUBIC).rotate(-48,expand=True,resample=Image.BICUBIC)
        sup.alpha_composite(cg,(205-cg.width+30,95)); sup.alpha_composite(cd,(435-30,95)); sup.alpha_composite(im); im=sup
    if k=='corps': im=epaulieres(im.copy(),[(168,168,-1)])
    if k=='bras': im=epaulieres(im.copy(),[(452,170,1)])
    im=A.carte_gradient(im)
    if k in ('corps','bras'): im=veines(im,{'corps':1,'bras':2}[k],18 if k=='corps' else 7)
    if k=='tete': A.yeux_ardents(im); troisieme_oeil(im)
    E[k]=im
QUEUE=(452,487)
def flamme_queue(c,t):
    d=ImageDraw.Draw(c); x,y=A.PAD+QUEUE[0],A.PAD+QUEUE[1]
    for i in range(7):
        u=(t*3+i/7)%1; r=(1-u)*13+3; xx=x+math.sin(u*9+i)*6; yy=y-u*45
        d.ellipse([xx-r,yy-r*1.5,xx+r,yy+r],fill=(255,int(90+150*u),20,int(230*(1-u))))
# ---------------------------------------------------------------- composition d'un stade (proportions + calques propres)
PIED=(313,592); COU=PIV['tete']
def ech(im,piv,f):
    big=im.resize((max(1,int(im.width*f)),max(1,int(im.height*f))),Image.BICUBIC)
    return big,(piv[0]-piv[0]*f,piv[1]-piv[1]*f)
def stade(jeu,sb,st,sa,t=0.0,anim=None):
    s=math.sin(2*math.pi*t)
    c=Image.new('RGBA',(W+2*A.PAD,H+2*A.PAD))
    def pos(p): return (PIED[0]+(p[0]-PIED[0])*sb, PIED[1]+(p[1]-PIED[1])*sb)
    for k in ['aile_g','aile_d','corps','bras','tete']:
        im=jeu[k]
        if k=='tete':
            nc=pos(COU); big,(ox,oy)=ech(im,COU,st); ox+=nc[0]-COU[0]; oy+=nc[1]-COU[1]-4*s
        elif k.startswith('aile'):
            piv=PIV[k]; np_=pos(piv); im=im.rotate((-4*s if k=='aile_g' else 4*s),center=piv,resample=Image.BICUBIC)
            big,(ox,oy)=ech(im,piv,sa); ox+=np_[0]-piv[0]; oy+=np_[1]-piv[1]
        else:
            big,(ox,oy)=ech(im,PIED,sb)
        c.alpha_composite(big,(int(A.PAD+ox),int(A.PAD+oy)))
    bg=Image.new('RGBA',c.size,A.FOND); bg.alpha_composite(c); return bg
