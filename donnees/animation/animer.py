"""Animateur « marionnette » : chaque calque tourne ou plie autour de son articulation, plus des effets dessinés."""
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import math, random
from pathlib import Path
D=str(Path(__file__).resolve().parent/'abyssor'/'calques')+'/'
S=0.5   # on travaille à mi-résolution
L={k:Image.open(D+k+'.png') for k in ['corps','aile_g','aile_d','tete','bras']}
L={k:v.resize((int(v.width*S),int(v.height*S)),Image.NEAREST) for k,v in L.items()}
W,H=L['corps'].size; PAD=90
PIV={'aile_g':(380,330),'aile_d':(880,330),'tete':(630,500),'bras':(895,455)}
PIV={k:(x*S,y*S) for k,(x,y) in PIV.items()}
FOND=(20,20,30,255)
def calque(k,ang=0,dx=0,dy=0,sy=1.0):
    im=L[k]
    if sy!=1.0:
        im=im.resize((W,max(1,int(H*sy))),Image.NEAREST); c=Image.new('RGBA',(W,H)); c.paste(im,(0,H-im.height)); im=c
    if ang: im=im.rotate(ang,center=PIV.get(k,(W/2,H)),resample=Image.BICUBIC)
    return im,(int(dx),int(dy))
def compo(p, effets=None, fond=FOND, assombrir=1.0):
    c=Image.new('RGBA',(W+2*PAD,H+2*PAD),(0,0,0,0))
    sy=p.get('souffle',1.0); dyc=H*(1-sy)
    ordre=['aile_g','aile_d','corps','bras','tete']
    for k in ordre:
        q=p.get(k,{})
        im,(dx,dy)=calque(k,q.get('a',0),q.get('x',0),q.get('y',0), sy if k=='corps' else 1.0)
        if k!='corps': dy+=dyc*0.9
        c.alpha_composite(im,(int(PAD+dx),int(PAD+dy)))
    g=p.get('echelle',1.0)
    if g!=1.0:
        nw,nh=int(c.width*g),int(c.height*g); big=c.resize((nw,nh),Image.BICUBIC)
        c=Image.new('RGBA',c.size); c.alpha_composite(big,((c.width-nw)//2,c.height-nh)) if g<1 else c.alpha_composite(big.crop(((nw-c.width)//2,nh-c.height,(nw-c.width)//2+c.width,nh)),(0,0))  # ancré au sol
    if effets: effets(c)
    if p.get('post'): c=p['post'](c)
    bg=Image.new('RGBA',c.size,fond)
    if p.get('derriere'): p['derriere'](bg)
    ox,oy=p.get('secousse',(0,0)); oy+=p.get('saut',0); bg.alpha_composite(c,(int(ox),int(oy)))
    if assombrir!=1.0: bg=ImageEnhance.Brightness(bg).enhance(assombrir)
    return bg
N=24
def ease(x): return 0.5-0.5*math.cos(math.pi*max(0,min(1,x)))
def statique(t):
    s=math.sin(2*math.pi*t)
    return compo({'souffle':1+0.012*s,'tete':{'y':-5*s,'a':1.2*s},'aile_g':{'a':-3*s},'aile_d':{'a':3*s},'bras':{'a':2*s}})
MOUCHE=(312,200)  # bouche (mi-résolution, avant PAD)
def mange(t):
    croc=abs(math.sin(3*math.pi*max(0,t-0.35)/0.65)) if t>0.35 else 0
    baisse=ease(t/0.35)*18 if t<0.85 else ease((1-t)/0.15)*18
    def eff(c):
        d=ImageDraw.Draw(c)
        mx,my=PAD+MOUCHE[0],PAD+MOUCHE[1]+baisse
        if t<0.4:  # un octet lumineux vole vers la bouche
            u=ease(t/0.4); x=mx+260*(1-u); y=my-140*(1-u)+math.sin(u*math.pi)*-60
            for i,(cx,cy) in enumerate([(0,0),(14,0),(0,14),(14,14)]):
                d.rectangle([x+cx-7,y+cy-7,x+cx+7,y+cy+7],fill=[(120,255,160),(80,220,255),(80,220,255),(120,255,160)][i])
            d.rectangle([x-10,y-10,x+24,y+24],outline=(255,255,255),width=2)
        elif t<0.8:
            rnd=random.Random(int(t*N))
            for _ in range(10):
                a=rnd.uniform(0,2*math.pi); r=rnd.uniform(15,60)*(t-0.35)*3
                x,y=mx+math.cos(a)*r,my+math.sin(a)*r*0.6+20
                d.rectangle([x,y,x+5,y+5],fill=rnd.choice([(120,255,160),(80,220,255),(255,255,255)]))
    return compo({'tete':{'y':baisse+croc*6,'a':-4*ease(t/0.35)},'souffle':1-0.01*croc,
                  'aile_g':{'a':-2*croc},'aile_d':{'a':2*croc},'bras':{'a':6*ease(t/0.35)*(t<0.85)}},eff)
def attaque(t):
    if t<0.3:
        u=ease(t/0.3); p={'echelle':1-0.05*u,'aile_g':{'a':-16*u},'aile_d':{'a':16*u},'tete':{'y':8*u},'bras':{'a':35*u}}
    elif t<0.45:
        u=ease((t-0.3)/0.15); p={'echelle':0.95+0.17*u,'aile_g':{'a':-16+22*u},'aile_d':{'a':16-22*u},'tete':{'y':8-20*u},'bras':{'a':35-80*u}}
    else:
        u=ease((t-0.45)/0.55); k=1-u
        p={'echelle':1+0.12*k,'aile_g':{'a':6*k},'aile_d':{'a':-6*k},'tete':{'y':-12*k},'bras':{'a':-45*k},
           'secousse':(math.sin(t*90)*14*k,math.cos(t*70)*8*k)}
    def eff(c):
        if 0.38<t<0.65:
            d=ImageDraw.Draw(c); k=(t-0.38)/0.27
            for i in range(3):
                off=i*38-38; w=int(14*(1-k))+2
                d.arc([c.width*0.15+off,c.height*0.15+off,c.width*0.95+off,c.height*0.95+off],200+k*30,290+k*40,fill=(255,240,200,int(255*(1-k))),width=w)
    return compo(p,eff)
def salut(t):
    lev=ease(t/0.25) if t<0.8 else ease((1-t)/0.2)
    vague=math.sin((t-0.25)*4*math.pi*2)*14*(0.25<t<0.8)
    hop=abs(math.sin(t*2*math.pi))*6
    return compo({'bras':{'a':(105+vague)*lev},'tete':{'a':-7*lev,'y':-hop},'aile_g':{'a':-5*lev},'aile_d':{'a':3*lev},
                  'souffle':1+0.01*math.sin(t*4*math.pi)})
def dort(t):
    s=math.sin(2*math.pi*t)
    def eff(c):
        d=ImageDraw.Draw(c)
        try: f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',46)
        except: f=None
        for i in range(3):
            u=(t+i/3)%1; x=PAD+440+u*90; y=PAD+110-u*110
            d.text((x,y),'z' if i%2 else 'Z',fill=(200,210,255,int(255*(1-u))),font=f)
    return compo({'souffle':1+0.02*s,'tete':{'y':22+4*s,'a':-6},'aile_g':{'a':12},'aile_d':{'a':-12},'bras':{'a':8}},eff,assombrir=0.75)
ANIMS=[('statique',statique),('mange',mange),('attaque',attaque),('salut',salut),('dort',dort)]

def salut(t):
    # salue d'une aile (trois battements) + hochement de tête poli + petit sursaut de joie
    lev=ease(t/0.15) if t<0.85 else ease((1-t)/0.15)
    bat=math.sin((t-0.15)/0.7*3*2*math.pi)*(0.15<t<0.85)
    hoche=max(0,math.sin(t*2*math.pi*2))*10
    return compo({'aile_d':{'a':(20+16*bat)*lev},'aile_g':{'a':3*lev},
                  'tete':{'y':hoche,'a':-5*lev},'bras':{'a':4*lev},
                  'souffle':1+0.012*math.sin(t*4*math.pi)})
def bulle(c,texte,u):
    d=ImageDraw.Draw(c); f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf',34)
    x0,y0=PAD+400,PAD-60; w,h=270,70
    d.rounded_rectangle([x0,y0,x0+w,y0+h],18,fill=(245,240,225,255),outline=(40,30,30,255),width=4)
    d.polygon([(x0+40,y0+h-2),(x0+75,y0+h-2),(x0+20,y0+h+40)],fill=(245,240,225,255))
    d.line([(x0+40,y0+h),(x0+20,y0+h+40),(x0+75,y0+h)],fill=(40,30,30,255),width=4)
    d.text((x0+18,y0+14),texte[:int(len(texte)*u)+1],fill=(40,30,40,255),font=f)
def parle(t):
    texte='ls -la ?!'
    syl=abs(math.sin(t*2*math.pi*5))*(t<0.75)   # rythme des syllabes
    u=min(1,t/0.6)
    return compo({'tete':{'y':-6*syl,'a':3*math.sin(t*2*math.pi*2.5)*(t<0.75)},'bras':{'a':6*syl},
                  'aile_g':{'a':-2*syl},'aile_d':{'a':2*syl},'souffle':1+0.008*syl},
                 lambda c: bulle(c,texte,u))
ANIMS=[('statique',statique),('mange',mange),('attaque',attaque),('salut',salut),('dort',dort),('parle',parle)]

import numpy as np
FB=lambda n: ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',n)
TETE=(PAD+312,PAD+120)   # centre de la tête sur le calque
def teinte(c,rgb,force):
    a=np.asarray(c).astype(float); al=a[...,3:4]/255
    a[...,:3]=a[...,:3]*(1-force)+np.array(rgb)*force*al
    return Image.fromarray(a.clip(0,255).astype('uint8'),'RGBA')
def content(t):
    h=abs(math.sin(t*2*math.pi))*40
    o=min(1,h/40)
    def eff(c):
        d=ImageDraw.Draw(c)
        for i in range(5):
            a=t*6+i*1.25; x=TETE[0]+math.cos(a)*170; y=TETE[1]-40+math.sin(a)*40
            d.text((x,y),'♪' if i%2 else '✦',fill=(255,220,120,200),font=FB(30))
    return compo({'saut':-h,'aile_g':{'a':-16*o},'aile_d':{'a':16*o},'tete':{'y':-6*o},'bras':{'a':-10*o},
                  'souffle':1-0.03*(1-o)},eff)
def affame(t):
    s=math.sin(t*2*math.pi)
    def eff(c):
        d=ImageDraw.Draw(c); x,y=PAD+300,PAD+330
        if (t*4)%1<0.6:
            for i in range(3): d.arc([x-60-i*18,y-20-i*10,x+60+i*18,y+40+i*10],20,160,fill=(255,200,120,170-i*50),width=4)
        d.text((TETE[0]+140,TETE[1]-60+6*s),'…',fill=(220,220,255,230),font=FB(54))
    return compo({'tete':{'y':28+3*s,'a':-7},'aile_g':{'a':14},'aile_d':{'a':-14},'bras':{'a':10},'souffle':0.985+0.008*s,
                  'secousse':(math.sin(t*120)*2,0)},eff,assombrir=0.82)
def confus(t):
    sec=math.sin(t*2*math.pi*3)*9*(t<0.5)
    def eff(c):
        d=ImageDraw.Draw(c); b=abs(math.sin(t*2*math.pi*2))*12
        d.text((TETE[0]+120,TETE[1]-150-b),'?',fill=(255,230,120,255),font=FB(80))
        if t>0.4: d.text((TETE[0]-180,TETE[1]-110),'?',fill=(255,230,120,int(255*min(1,(t-0.4)*4))),font=FB(52))
    return compo({'tete':{'a':sec,'y':4},'bras':{'a':8*(t>0.5)},'aile_g':{'a':4},'aile_d':{'a':-4}},eff)
def colere(t):
    k=min(1,t/0.4)
    def eff(c):
        d=ImageDraw.Draw(c); rnd=random.Random(3)
        for i in range(8):
            u=(t*1.5+i/8)%1; cx=(PAD+240 if i%2 else PAD+385)+rnd.uniform(-15,15)+u*20*(1 if i%2 else -1)
            cy=PAD+20-u*130; r=10+u*28
            d.ellipse([cx-r,cy-r,cx+r,cy+r],fill=(110,110,120,int(170*(1-u))))
    return compo({'secousse':(math.sin(t*140)*7*k,math.cos(t*110)*4*k),'tete':{'y':6*k},'aile_g':{'a':-10*k},'aile_d':{'a':10*k},
                  'bras':{'a':14*k},'post':lambda c: teinte(c,(255,40,20),0.25*k*(0.7+0.3*math.sin(t*20)))},eff)
def victoire(t):
    o=ease(t/0.3)
    def rayons(bg):
        d=ImageDraw.Draw(bg); cx,cy=bg.width/2,bg.height*0.42
        for i in range(16):
            a=i/16*2*math.pi+t*1.5; a2=a+0.12
            d.polygon([(cx,cy),(cx+math.cos(a)*700,cy+math.sin(a)*700),(cx+math.cos(a2)*700,cy+math.sin(a2)*700)],
                      fill=(70,55,25,255) if i%2 else (40,32,20,255))
    def eff(c):
        d=ImageDraw.Draw(c); rnd=random.Random(int(t*N))
        for _ in range(int(14*o)):
            x,y=rnd.uniform(PAD,c.width-PAD),rnd.uniform(0,c.height*0.6)
            d.text((x,y),'✦',fill=rnd.choice([(255,220,90,255),(255,255,255,255)]),font=FB(rnd.randint(16,30)))
    return compo({'derriere':rayons,'echelle':1+0.06*o,'aile_g':{'a':-22*o},'aile_d':{'a':22*o},'tete':{'y':-14*o,'a':2*math.sin(t*12)},
                  'bras':{'a':-15*o},'saut':-10*abs(math.sin(t*4*math.pi))*o},eff)
def ko(t):
    u=ease(t/0.35)
    def post(c):
        c=ImageEnhance.Color(c).enhance(1-0.7*u)
        big=c.rotate(-14*u,center=(c.width/2,c.height),resample=Image.BICUBIC)
        sq=big.resize((c.width,int(c.height*(1-0.25*u))),Image.BICUBIC); out=Image.new('RGBA',c.size); out.alpha_composite(sq,(0,c.height-sq.height)); return out
    def eff(c):
        if t>0.35:
            d=ImageDraw.Draw(c)
            for i in range(4):
                a=t*9+i*math.pi/2; d.text((TETE[0]-15+math.cos(a)*110,TETE[1]+50+math.sin(a)*30),'★',fill=(255,230,100,255),font=FB(30))
    return compo({'tete':{'y':40*u,'a':-14*u},'aile_g':{'a':20*u},'aile_d':{'a':-20*u},'bras':{'a':22*u},'post':post},eff,assombrir=1-0.2*u)
def evolution(t):
    if t<0.65:
        f=(math.sin(t**2*60)*0.5+0.5)*min(1,t/0.4); g=1
    else:
        u=(t-0.65)/0.35; f=max(0,1-u*1.6); g=1.12
    def eff(c):
        if t>0.62:
            d=ImageDraw.Draw(c); u=(t-0.62)/0.38; cx,cy=c.width/2,c.height*0.5
            for i in range(24):
                a=i/24*2*math.pi; r=60+u*420
                d.ellipse([cx+math.cos(a)*r-6,cy+math.sin(a)*r-6,cx+math.cos(a)*r+6,cy+math.sin(a)*r+6],fill=(255,255,255,int(255*(1-u))))
    return compo({'echelle':g,'post':lambda c: teinte(c,(255,255,255),f),'aile_g':{'a':-10*(t>0.65)},'aile_d':{'a':10*(t>0.65)}},eff)
def capture(t):
    if t<0.55: u=ease(t/0.55); g=1-0.95*u; f=u
    else: g=0.05; f=1
    def eff(c):
        d=ImageDraw.Draw(c); cx,cy=c.width/2,c.height*0.85
        if t>0.5:
            u=(t-0.5)/0.5
            for i in range(10):
                a=i/10*2*math.pi; r=10+u*160
                d.text((cx+math.cos(a)*r,cy-60+math.sin(a)*r*0.5),'✦',fill=(140,255,200,int(255*(1-u))),font=FB(24))
            d.rounded_rectangle([cx-70,cy-10,cx+70,cy+40],12,outline=(140,255,200,int(255*(1-u*0.5))),width=5)
            d.text((cx-38,cy-4),'nid/',fill=(140,255,200,int(255*(1-u*0.5))),font=FB(28))
    return compo({'echelle':g,'post':lambda c: teinte(c,(160,255,220),0.8*f)},eff)
def hue(c,dec=0.5):
    rgb=c.convert('RGB').convert('HSV'); h,s_,v=rgb.split()
    h=h.point(lambda x:(x+int(dec*255))%256); out=Image.merge('HSV',(h,s_,v)).convert('RGB').convert('RGBA'); out.putalpha(c.getchannel('A')); return out
def shiny(t):
    s=math.sin(2*math.pi*t)
    def eff(c):
        d=ImageDraw.Draw(c); rnd=random.Random(7)
        for i in range(9):
            u=(t*2+i/9)%1; x=rnd.uniform(PAD+60,c.width-PAD-60); y=rnd.uniform(PAD,c.height-PAD-80)
            k=math.sin(u*math.pi); r=4+16*k
            d.polygon([(x,y-r*2),(x+r*0.5,y-r*0.5),(x+r*2,y),(x+r*0.5,y+r*0.5),(x,y+r*2),(x-r*0.5,y+r*0.5),(x-r*2,y),(x-r*0.5,y-r*0.5)],fill=(255,255,255,int(255*k)))
    return compo({'souffle':1+0.012*s,'tete':{'y':-5*s},'aile_g':{'a':-3*s},'aile_d':{'a':3*s},'post':hue},eff)
def glitch(t):
    i=int(t*N); actif=i%6 in (2,3) or i in (11,12,13)
    s=math.sin(2*math.pi*t)
    def post(c):
        if not actif: return c
        rnd=random.Random(i); a=np.asarray(c).copy()
        for _ in range(7):
            y0=rnd.randrange(0,a.shape[0]-30); hh=rnd.randrange(6,40); dx=rnd.randrange(-50,50)
            a[y0:y0+hh]=np.roll(a[y0:y0+hh],dx,axis=1)
        r=np.roll(a[...,0],8,axis=1); b=np.roll(a[...,2],-8,axis=1); a[...,0]=r; a[...,2]=b
        return Image.fromarray(a,'RGBA')
    return compo({'souffle':1+0.012*s,'tete':{'y':-5*s},'post':post,'secousse':((6 if actif else 0),0)})
ANIMS=[('statique',statique),('mange',mange),('attaque',attaque),('salut',salut),('dort',dort),('parle',parle),
       ('content',content),('affamé',affame),('confus',confus),('colère',colere),('victoire',victoire),('KO',ko),
       ('évolution',evolution),('capture',capture),('shiny',shiny),('glitch',glitch)]

# ------------------------------------------------------------------ v3
from scipy import ndimage as _nd
_YX=np.mgrid[0:H,0:W].astype(float)
def plier(im,ang,piv,R=110):
    # l'angle croît avec la distance à l'épaule : la base reste attachée, le bout tourne entièrement
    py,px=piv[1],piv[0]; dy=_YX[0]-py; dx=_YX[1]-px; r=np.hypot(dx,dy)
    th=-math.radians(ang)*np.clip(r/R,0,1)**1.3
    # PIL : angle positif = sens anti-horaire à l'écran
    c,s_=np.cos(th),np.sin(th)
    sx=px+dx*c+dy*s_; sy=py-dx*s_+dy*c
    a=np.asarray(im); out=np.zeros_like(a)
    for ch in range(4): out[...,ch]=_nd.map_coordinates(a[...,ch],[sy,sx],order=1,mode='constant')
    return Image.fromarray(out,'RGBA')
def tourner(k,im,ang):
    if k.startswith('aile'): return plier(im,ang,PIV[k])
    return im.rotate(ang,center=PIV.get(k,(W/2,H)),resample=Image.BICUBIC)
YEUX=[(288,158),(345,158)]   # sur le calque, mi-résolution
def compo(p, effets=None, fond=FOND, assombrir=1.0):
    c=Image.new('RGBA',(W+2*PAD,H+2*PAD),(0,0,0,0))
    sy=p.get('souffle',1.0); dyc=H*(1-sy)
    jeu=p.get('calques',L)
    for k in ['aile_g','aile_d','corps','bras','tete']:
        q=p.get(k,{})
        im=jeu[k]
        if k=='tete' and p.get('deco_tete'): im=im.copy(); p['deco_tete'](im)
        if k=='corps' and sy!=1.0:
            r=im.resize((W,max(1,int(H*sy))),Image.NEAREST); im=Image.new('RGBA',(W,H)); im.paste(r,(0,H-r.height))
        if q.get('a'): im=tourner(k,im,q['a'])
        dx,dy=q.get('x',0),q.get('y',0)
        if k!='corps': dy+=dyc*0.9
        c.alpha_composite(im,(int(PAD+dx),int(PAD+dy)))
    g=p.get('echelle',1.0)
    if g!=1.0:
        nw,nh=int(c.width*g),int(c.height*g); big=c.resize((nw,nh),Image.BICUBIC)
        c2=Image.new('RGBA',c.size)
        if g<1: c2.alpha_composite(big,((c.width-nw)//2,c.height-nh-int(PAD*0.6*(1-g))))
        else: c2.alpha_composite(big.crop(((nw-c.width)//2,nh-c.height,(nw-c.width)//2+c.width,nh)),(0,0))
        c=c2
    if effets: effets(c)
    if p.get('post'): c=p['post'](c)
    bg=Image.new('RGBA',c.size,fond)
    if p.get('derriere'): p['derriere'](bg)
    ox,oy=p.get('secousse',(0,0)); oy+=p.get('saut',0); bg.alpha_composite(c,(int(ox),int(oy)))
    if assombrir!=1.0: bg=ImageEnhance.Brightness(bg).enhance(assombrir)
    return bg

def spirales(phase):
    def deco(im):
        d=ImageDraw.Draw(im)
        for (x,y) in YEUX:
            R=24
            d.ellipse([x-R-4,y-R-4,x+R+4,y+R+4],fill=(10,5,10,255))
            d.ellipse([x-R,y-R,x+R,y+R],fill=(255,255,240,255))
            pts=[]
            for i in range(90):
                u=i/89; a=phase+u*5*math.pi; r=u*(R-3)
                pts.append((x+math.cos(a)*r,y+math.sin(a)*r))
            d.line(pts,fill=(90,0,140,255),width=5)
    return deco
def confus(t):
    tour=math.sin(t*2*math.pi*2)*7
    def eff(c):
        d=ImageDraw.Draw(c)
        for i in range(3):
            a=t*2*math.pi*2+i*2.1; x=TETE[0]+math.cos(a)*120; y=TETE[1]-70+math.sin(a)*28
            d.text((x,y),'✦',fill=(255,230,120,230),font=FB(26))
    return compo({'tete':{'a':tour,'y':4+2*math.sin(t*8*math.pi)},'deco_tete':spirales(t*2*math.pi*3),
                  'secousse':(math.sin(t*2*math.pi*2)*6,0),'aile_g':{'a':5},'aile_d':{'a':-5},'bras':{'a':6}},eff)

def croix(im):
    d=ImageDraw.Draw(im)
    for (x,y) in YEUX:
        R=20; d.ellipse([x-R-5,y-R-5,x+R+5,y+R+5],fill=(10,5,10,255))
        for s in (1,-1):
            d.line([(x-R,y-R*s),(x+R,y+R*s)],fill=(10,5,10,255),width=13)
            d.line([(x-R,y-R*s),(x+R,y+R*s)],fill=(255,255,245,255),width=7)
def crane(d,cx,cy,k,alpha):
    a=int(255*alpha); B=(250,248,240,a); N_=(10,5,10,a)
    r=int(60*k)
    d.ellipse([cx-r*1.7,cy-r*1.4,cx+r*1.7,cy+r*1.9],fill=(140,40,200,int(90*alpha)))
    d.ellipse([cx-r-6,cy-r-6,cx+r+6,cy+r*0.9+6],fill=N_); d.rounded_rectangle([cx-r*0.6-6,cy+r*0.55-6,cx+r*0.6+6,cy+r*1.25+6],8,fill=N_)
    d.ellipse([cx-r,cy-r,cx+r,cy+r*0.9],fill=B,outline=N_,width=3)
    d.rounded_rectangle([cx-r*0.6,cy+r*0.55,cx+r*0.6,cy+r*1.25],6,fill=B,outline=N_,width=3)
    for s in (-1,1): d.ellipse([cx+s*r*0.42-r*0.25,cy-r*0.05,cx+s*r*0.42+r*0.25,cy+r*0.45],fill=N_)
    d.polygon([(cx,cy+r*0.45),(cx-r*0.1,cy+r*0.65),(cx+r*0.1,cy+r*0.65)],fill=N_)
    for i in (-1,0,1): d.line([(cx+i*r*0.2,cy+r*0.8),(cx+i*r*0.2,cy+r*1.2)],fill=N_,width=5)
def ko(t):
    if t<0.18:
        u=t/0.18; p={'secousse':(math.sin(u*40)*14*(1-u),0),'tete':{'y':-10*math.sin(u*math.pi)}}
    else:
        u=ease((t-0.18)/0.3)
        p={'tete':{'y':30*u,'a':-12*u},'aile_g':{'a':18*u},'aile_d':{'a':-18*u},'bras':{'a':16*u},'souffle':1-0.03*u,
           'deco_tete':croix,'post':lambda c: ImageEnhance.Color(c).enhance(1-0.55*u)}
    def eff(c):
        if t>0.3:
            v=min(1,(t-0.3)/0.15); pop=1+0.35*math.sin(v*math.pi)  # grossit puis se pose
            d=ImageDraw.Draw(c)
            crane(d,TETE[0]+15,TETE[1]-135+6*math.sin(t*12),0.9*pop*v+0.1,min(1,v*2))
    return compo(p,eff,assombrir=0.9 if t>0.18 else 1)

def victoire(t):
    mont=ease(t/0.25) if t<0.8 else ease((1-t)/0.2)
    bat=math.sin(t*2*math.pi*4)
    def derriere(bg):
        d=ImageDraw.Draw(bg); sol=bg.height-PAD*0.55
        for i in range(6):
            u=(t*2+i/6)%1; x=bg.width/2+(i-2.5)*95*(0.6+u); r=20+40*u
            d.ellipse([x-r,sol-r*0.5,x+r,sol+r*0.5],fill=(60,55,70,int(200*(1-u)*mont)))
    def eff(c):
        d=ImageDraw.Draw(c); rnd=random.Random(11)
        for i in range(16):
            u=(t*1.5+i/16)%1; x=rnd.uniform(PAD,c.width-PAD); y=c.height-PAD-u*(c.height-PAD)
            d.text((x,y),'✦',fill=(255,210,80,int(255*math.sin(u*math.pi))),font=FB(rnd.randint(14,26)))
        if t>0.3:
            u=min(1,(t-0.3)/0.4); d.text((c.width/2+150,PAD+150-50*u),'+100 XP',fill=(255,225,110,int(255*min(1,(1-u)*3))),font=FB(46))
    return compo({'saut':-70*mont,'aile_g':{'a':-8-20*bat*mont},'aile_d':{'a':8+20*bat*mont},'tete':{'y':-10*mont,'a':3*mont},
                  'bras':{'a':-12*mont},'derriere':derriere},eff)

# --- forme évoluée : ailes plus grandes, 2e paire de cornes, peau embrasée
def carte_gradient(im):
    a=np.asarray(im).astype(float); lum=(a[...,0]*0.4+a[...,1]*0.4+a[...,2]*0.2)/255
    st=[(0,(8,0,10)),(0.22,(70,5,30)),(0.42,(150,15,30)),(0.62,(235,80,25)),(0.85,(255,200,90)),(1,(255,250,210))]
    out=np.zeros(a.shape[:2]+(3,))
    for (x0,c0),(x1,c1) in zip(st,st[1:]):
        m=(lum>=x0)&(lum<=x1); u=((lum-x0)/(x1-x0))[...,None]
        out[m]=(np.array(c0)*(1-u)+np.array(c1)*u)[m]
    a[...,:3]=out; return Image.fromarray(a.astype('uint8'),'RGBA')
def mise_echelle(im,piv,f):
    big=im.resize((int(im.width*f),int(im.height*f)),Image.BICUBIC); out=Image.new('RGBA',im.size)
    out.alpha_composite(big,(int(piv[0]-piv[0]*f),int(piv[1]-piv[1]*f))) if f<=1 else None
    if f>1:
        ox,oy=int(piv[0]*f-piv[0]),int(piv[1]*f-piv[1])
        out.alpha_composite(big.crop((ox,oy,ox+im.width,oy+im.height)),(0,0))
    return out
EVO={}
for k in L:
    im=L[k]
    if k.startswith('aile'): im=mise_echelle(im,PIV[k],1.3).rotate(-8 if k=='aile_g' else 8,center=PIV[k],resample=Image.BICUBIC)
    if k=='tete':
        im=mise_echelle(im,PIV['tete'],1.06)
        sup=Image.new('RGBA',im.size)
        cg=im.crop((205,5,290,110)); cd=im.crop((350,5,435,110))
        cg=cg.resize((int(cg.width*0.85),int(cg.height*0.85)),Image.BICUBIC).rotate(48,expand=True,resample=Image.BICUBIC)
        cd=cd.resize((int(cd.width*0.85),int(cd.height*0.85)),Image.BICUBIC).rotate(-48,expand=True,resample=Image.BICUBIC)
        sup.alpha_composite(cg,(205-cg.width+30,95)); sup.alpha_composite(cd,(435-30,95))
        sup.alpha_composite(im); im=sup
    EVO[k]=carte_gradient(im)
from PIL import ImageFilter
def aura(c,t,force=1):
    al=c.getchannel('A').filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(14))
    k=(0.75+0.25*math.sin(t*2*math.pi*2))*force
    al=al.point(lambda v:int(v*k))
    glow=Image.new('RGBA',c.size,(255,110,20,0)); glow.putalpha(al)
    out=Image.new('RGBA',c.size); out.alpha_composite(glow); out.alpha_composite(c); return out
def yeux_ardents(im):
    d=ImageDraw.Draw(im)
    for (x,y) in YEUX:
        d.ellipse([x-6,y-5,x+6,y+5],fill=(120,255,255,255)); d.ellipse([x-2,y-2,x+2,y+2],fill=(255,255,255,255))
def flammes(c,t,force=1):
    d=ImageDraw.Draw(c); rnd=random.Random(5)
    for i in range(26):
        u=(t*2+i/26)%1; x=rnd.uniform(PAD+60,c.width-PAD-60); y=c.height-PAD-rnd.uniform(0,c.height*0.7)-u*80
        r=(1-u)*14+3; d.ellipse([x-r,y-r*1.6,x+r,y+r],fill=(255,int(120+100*u),40,int(160*(1-u)*force)))
def evolution(t):
    if t<0.55:
        f=(math.sin(t**2*70)*0.5+0.5)*min(1,t/0.35); jeu=L; g=1; ef=None
    else:
        u=(t-0.55)/0.45; f=max(0,1-u*2.2); jeu=EVO; g=1.08
        s=math.sin(2*math.pi*u*2)
        def ef(c):
            if u<0.5:
                d=ImageDraw.Draw(c); cx,cy=c.width/2,c.height*0.5
                for i in range(28):
                    a=i/28*2*math.pi; r=60+u*900
                    d.ellipse([cx+math.cos(a)*r-7,cy+math.sin(a)*r-7,cx+math.cos(a)*r+7,cy+math.sin(a)*r+7],fill=(255,240,200,int(255*(1-u*2))))
        return compo({'calques':EVO,'echelle':g,'post':lambda c: teinte(aura(c,t,min(1,u*2)),(255,255,255),f),'deco_tete':yeux_ardents,'souffle':1+0.012*s,
                      'tete':{'y':-5*s},'aile_g':{'a':-3*s},'aile_d':{'a':3*s}},ef)
    return compo({'post':lambda c: teinte(c,(255,255,255),f),'secousse':(math.sin(t*90)*4*min(1,t/0.4),0)})
def evoluee(t):
    s=math.sin(2*math.pi*t)
    return compo({'calques':EVO,'echelle':1.08,'souffle':1+0.012*s,'tete':{'y':-5*s,'a':1.2*s},'aile_g':{'a':-4*s},'aile_d':{'a':4*s},
                  'deco_tete':yeux_ardents,'post':lambda c: aura(c,t)})

def shiny_de(dec, etoile):
    def anim(t):
        s=math.sin(2*math.pi*t)
        def eff(c):
            d=ImageDraw.Draw(c); rnd=random.Random(7)
            for i in range(9):
                u=(t*2+i/9)%1; x=rnd.uniform(PAD+60,c.width-PAD-60); y=rnd.uniform(PAD,c.height-PAD-80)
                k=math.sin(u*math.pi); r=4+16*k
                d.polygon([(x,y-r*2),(x+r*0.5,y-r*0.5),(x+r*2,y),(x+r*0.5,y+r*0.5),(x,y+r*2),(x-r*0.5,y+r*0.5),(x-r*2,y),(x-r*0.5,y-r*0.5)],fill=etoile+(int(255*k),))
        return compo({'souffle':1+0.012*s,'tete':{'y':-5*s},'aile_g':{'a':-3*s},'aile_d':{'a':3*s},'post':lambda c: hue(c,dec)},eff)
    return anim
ANIMS_V3=[('confus',confus),('victoire',victoire),('KO',ko),('évolution',evolution),
          ('forme évoluée',evoluee),('shiny n°1',shiny_de(0.5,(255,255,255))),('shiny n°2',shiny_de(0.72,(255,215,90))),('shiny n°3',shiny_de(0.2,(140,220,255)))]
