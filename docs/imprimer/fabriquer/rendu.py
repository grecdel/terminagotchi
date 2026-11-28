"""HTML -> PDF (format papier) et/ou PNG, avec le Chromium de Playwright (outil de fabrication, pas dans le jeu)."""
import os
from playwright.sync_api import sync_playwright
DEPOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
POL = "file://" + DEPOT + "/site/public/polices/"
POLICES = f"""
@font-face{{font-family:"Press Start 2P";src:url({POL}press-start-2p-latin-400-normal.woff2) format("woff2");unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}}
@font-face{{font-family:"Press Start 2P";src:url({POL}press-start-2p-latin-ext-400-normal.woff2) format("woff2")}}
@font-face{{font-family:"VT323";src:url({POL}vt323-latin-400-normal.woff2) format("woff2");unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}}
@font-face{{font-family:"VT323";src:url({POL}vt323-latin-ext-400-normal.woff2) format("woff2")}}
"""
def rendre(html_path, pdf=None, png=None, largeur=None, hauteur=None, fmt=None, paysage=False, echelle=1):
    with sync_playwright() as p:
        b = p.chromium.launch()
        if pdf:
            pg = b.new_page()
            pg.goto("file://" + html_path, wait_until="networkidle"); pg.wait_for_timeout(300)
            pg.pdf(path=pdf, format=fmt, landscape=paysage, print_background=True, margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
            pg.close()
        if png:
            pg = b.new_page(viewport={"width": largeur, "height": hauteur}, device_scale_factor=echelle)
            pg.goto("file://" + html_path, wait_until="networkidle"); pg.wait_for_timeout(300)
            pg.screenshot(path=png, full_page=True)
        b.close()
