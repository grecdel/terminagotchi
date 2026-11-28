"""Le PDF des fiches enseignant : docs/classe/fiches_enseignant.md → docs/classe/fiches_enseignant.pdf.

    python3 pc/outils/fiches_classe.py      (demande pandoc et wkhtmltopdf ; le PDF est rangé dans le dépôt)

Le texte fait foi dans le .md ; le PDF est sa version à imprimer (A4, une fiche par page, « \\newpage » = saut de page).
Les codes de séance et les noms des leçons des fiches sont vérifiés par pc/outils/test_classe.py.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
MD = RACINE / "docs/classe/fiches_enseignant.md"
PDF = MD.with_suffix(".pdf")

CSS = """
body { font-family: "DejaVu Sans", sans-serif; font-size: 10.5pt; line-height: 1.38; color: #111; margin: 0; }
header { text-align: center; margin: 120px 0 40px; }
header .title { font-size: 26pt; margin-bottom: 10px; }
header .subtitle { font-size: 13pt; color: #444; }
h1 { font-size: 17pt; border-bottom: 3px solid #2d7d46; padding-bottom: 4px; margin-top: 0; color: #1d5a31; }
h2 { font-size: 13pt; color: #1d5a31; margin-top: 18px; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 12px; page-break-inside: avoid; }
td, th { border: 1px solid #9ab; padding: 4px 7px; vertical-align: top; text-align: left; }
th { background: #e6f2ea; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 9.5pt; background: #f1f4f2; padding: 0 2px; }
blockquote { border: 2px solid #2d7d46; background: #f4faf6; margin: 8px 0; padding: 6px 12px; page-break-inside: avoid; }
.saut { page-break-after: always; }
"""


def main():
    if not shutil.which("pandoc") or not shutil.which("wkhtmltopdf"):
        print("Il faut pandoc et wkhtmltopdf.")
        return 1
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "fiches.md"
        src.write_text(MD.read_text(encoding="utf-8").replace("\\newpage", '<div class="saut"></div>'), encoding="utf-8")
        (Path(d) / "style.css").write_text(CSS, encoding="utf-8")
        html = Path(d) / "fiches.html"
        subprocess.run(["pandoc", str(src), "-s", "-o", str(html), "--css", "style.css", "--metadata", "lang=fr",
                        "-f", "markdown-implicit_figures"], check=True, cwd=d)
        subprocess.run(["wkhtmltopdf", "--quiet", "--enable-local-file-access", "-s", "A4", "-T", "16mm", "-B", "16mm",
                        "-L", "15mm", "-R", "15mm", "--title", "Terminagotchi en classe — fiches enseignant",
                        str(html), str(PDF)], check=True, cwd=d)
    print(f"{PDF.relative_to(RACINE)} : {PDF.stat().st_size // 1024} Ko")
    return 0


if __name__ == "__main__":
    sys.exit(main())
