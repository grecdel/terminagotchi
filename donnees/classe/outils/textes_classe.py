"""Les textes du mode classe (séance guidée, écran projecteur, place de la classe), de la carte de visite et de
« Lecture et confort » (idées 54, 55, 56, 58, 61, 62, 64, 65 ; 3 novembre), dans les 14 langues.
    python3 donnees/classe/outils/textes_classe.py   : les ajoute (ou les met à jour) dans pc/tg/langues et
                                                       app/src/main/assets/langues (écriture atomique, à la fin).
Les contenus des séances (seance.N.*) sont dans textes_seances.py (même principe)."""
import json
import os
import sys
from pathlib import Path

L = ["fr", "en", "es", "de", "it", "pt", "ru", "zh", "ja", "hi", "ar", "bn", "id", "ur"]


def T(*v):
    assert len(v) == 14, v[0]
    return dict(zip(L, v))


K = {
 # ---------------------------------------------------------------- lecture et confort
 "conf.titre": T("Lecture et confort", "Reading and comfort", "Lectura y comodidad", "Lesen und Komfort", "Lettura e comfort", "Leitura e conforto", "Чтение и удобство", "阅读与舒适", "読みやすさ", "पढ़ना और आराम", "القراءة والراحة", "পড়া ও আরাম", "Membaca dan kenyamanan", "پڑھنا اور آرام"),
 "conf.taille": T("Taille du texte", "Text size", "Tamaño del texto", "Textgröße", "Dimensione del testo", "Tamanho do texto", "Размер текста", "文字大小", "文字の大きさ", "अक्षरों का आकार", "حجم النص", "লেখার আকার", "Ukuran teks", "متن کا سائز"),
 "conf.taille.100": T("normal", "normal", "normal", "normal", "normale", "normal", "обычный", "正常", "ふつう", "सामान्य", "عادي", "সাধারণ", "normal", "عام"),
 "conf.taille.125": T("grand", "large", "grande", "groß", "grande", "grande", "крупный", "大", "大きい", "बड़ा", "كبير", "বড়", "besar", "بڑا"),
 "conf.taille.150": T("très grand", "very large", "muy grande", "sehr groß", "molto grande", "muito grande", "очень крупный", "特大", "とても大きい", "बहुत बड़ा", "كبير جدًا", "খুব বড়", "sangat besar", "بہت بڑا"),
 "conf.taille.aide": T("tout l'espace grandit ; Ctrl + / Ctrl − aussi", "the whole space grows; Ctrl + / Ctrl − too", "todo el espacio crece; también Ctrl + / Ctrl −", "der ganze Platz wächst; auch Strg + / Strg −", "tutto lo spazio cresce; anche Ctrl + / Ctrl −", "todo o espaço cresce; Ctrl + / Ctrl − também", "всё пространство растёт; также Ctrl + / Ctrl −", "整个空间都会变大；也可按 Ctrl + / Ctrl −", "スペース全体が大きくなる。Ctrl + / Ctrl − でも", "पूरी जगह बड़ी होती है; Ctrl + / Ctrl − से भी", "تكبر المساحة كلها؛ وأيضًا Ctrl + / Ctrl −", "পুরো জায়গা বড় হয়; Ctrl + / Ctrl − দিয়েও", "seluruh ruang membesar; Ctrl + / Ctrl − juga", "پوری جگہ بڑی ہوتی ہے؛ Ctrl + / Ctrl − سے بھی"),
 "conf.taille.terminal": T("dans un vrai terminal : Ctrl Maj +", "in a real terminal: Ctrl Shift +", "en un terminal real: Ctrl Mayús +", "in einem echten Terminal: Strg Umschalt +", "in un vero terminale: Ctrl Maiusc +", "num terminal de verdade: Ctrl Shift +", "в настоящем терминале: Ctrl Shift +", "在真正的终端里：Ctrl Shift +", "本物のターミナルでは Ctrl Shift +", "असली टर्मिनल में: Ctrl Shift +", "في طرفية حقيقية: Ctrl Shift +", "আসল টার্মিনালে: Ctrl Shift +", "di terminal sungguhan: Ctrl Shift +", "اصلی ٹرمینل میں: Ctrl Shift +"),
 "conf.police": T("Police", "Font", "Letra", "Schrift", "Carattere", "Fonte", "Шрифт", "字体", "フォント", "फ़ॉन्ट", "الخط", "ফন্ট", "Huruf", "فونٹ"),
 "conf.police.normale": T("Normale", "Normal", "Normal", "Normal", "Normale", "Normal", "Обычный", "普通", "ふつう", "सामान्य", "عادي", "সাধারণ", "Normal", "عام"),
 "conf.police.facile": T("Lecture facile", "Easy reading", "Lectura fácil", "Leicht lesen", "Lettura facile", "Leitura fácil", "Лёгкое чтение", "易读", "読みやすい", "आसान पढ़ाई", "قراءة سهلة", "সহজ পড়া", "Mudah dibaca", "آسان پڑھائی"),
 "conf.police.facile.titre": T("Police « Lecture facile »", "“Easy reading” font", "Letra «Lectura fácil»", "Schrift „Leicht lesen“", "Carattere «Lettura facile»", "Fonte «Leitura fácil»", "Шрифт «Лёгкое чтение»", "“易读”字体", "「読みやすい」フォント", "“आसान पढ़ाई” फ़ॉन्ट", "خط «قراءة سهلة»", "“সহজ পড়া” ফন্ট", "Huruf “Mudah dibaca”", "“آسان پڑھائی” فونٹ"),
 "conf.police.aide": T("lettres plus distinctes et plus espacées", "clearer letters with more space", "letras más claras y separadas", "deutlichere Buchstaben mit mehr Abstand", "lettere più chiare e distanziate", "letras mais claras e espaçadas", "буквы чётче и шире", "字母更清楚、间距更大", "文字がはっきり、間かくも広く", "साफ़ अक्षर, ज़्यादा जगह", "حروف أوضح ومتباعدة أكثر", "স্পষ্ট অক্ষর, বেশি ফাঁক", "huruf lebih jelas dan berjarak", "صاف حروف، زیادہ فاصلہ"),
 "conf.police.terminal": T("le terminal garde sa police", "the terminal keeps its font", "el terminal conserva su letra", "das Terminal behält seine Schrift", "il terminale tiene il suo carattere", "o terminal mantém a fonte", "терминал сохраняет свой шрифт", "终端保持原字体", "ターミナルはそのまま", "टर्मिनल का फ़ॉन्ट वही रहता है", "تحتفظ الطرفية بخطها", "টার্মিনালের ফন্ট একই থাকে", "terminal tetap memakai hurufnya", "ٹرمینل کا فونٹ وہی رہتا ہے"),
 "conf.police.absente": T("(la police Andika n'est pas encore livrée avec le jeu : le texte est seulement plus grand et plus espacé)", "(the Andika font is not shipped with the game yet: text is only bigger and more spaced)", "(la letra Andika aún no viene con el juego: el texto solo es más grande y espaciado)", "(die Schrift Andika ist noch nicht im Spiel: der Text ist nur größer und weiter)", "(il carattere Andika non è ancora incluso: il testo è solo più grande e spaziato)", "(a fonte Andika ainda não vem com o jogo: o texto só fica maior e mais espaçado)", "(шрифта Andika пока нет в игре: текст только крупнее и шире)", "（游戏里还没有 Andika 字体：文字只是更大、更宽）", "（Andika フォントはまだ入っていません。文字が大きく広くなるだけです）", "(Andika फ़ॉन्ट अभी खेल में नहीं है: अक्षर सिर्फ़ बड़े और खुले हैं)", "(خط Andika ليس مع اللعبة بعد: النص أكبر ومتباعد فقط)", "(Andika ফন্ট এখনো খেলায় নেই: লেখা শুধু বড় আর ফাঁকা)", "(huruf Andika belum disertakan: teks hanya lebih besar dan berjarak)", "(Andika فونٹ ابھی کھیل میں نہیں: متن صرف بڑا اور کھلا ہے)"),
 "conf.formes": T("Couleurs + formes", "Colours + shapes", "Colores + formas", "Farben + Formen", "Colori + forme", "Cores + formas", "Цвета + формы", "颜色 + 形状", "色 + 形", "रंग + आकार", "ألوان + أشكال", "রং + আকার", "Warna + bentuk", "رنگ + شکلیں"),
 "conf.formes.aide": T("jamais une couleur seule pour dire quelque chose", "never a colour alone to say something", "nunca un color solo para decir algo", "nie eine Farbe allein als Hinweis", "mai un colore da solo per dire qualcosa", "nunca uma cor sozinha para dizer algo", "никогда только цвет, чтобы что-то сказать", "从不只靠颜色表达意思", "色だけで伝えない", "सिर्फ़ रंग से कभी कुछ नहीं कहना", "لا لون وحده أبدًا ليقول شيئًا", "শুধু রং দিয়ে কখনো কিছু বলা নয়", "tak pernah hanya warna untuk memberi tahu", "صرف رنگ سے کبھی کچھ نہیں کہنا"),
 "conf.calme": T("Mode calme", "Calm mode", "Modo tranquilo", "Ruhiger Modus", "Modalità calma", "Modo calmo", "Спокойный режим", "安静模式", "おだやかモード", "शांत मोड", "الوضع الهادئ", "শান্ত মোড", "Mode tenang", "پرسکون موڈ"),
 "conf.calme.aide": T("rien ne clignote, rien ne secoue", "nothing blinks, nothing shakes", "nada parpadea, nada se sacude", "nichts blinkt, nichts wackelt", "niente lampeggia, niente scuote", "nada pisca, nada treme", "ничего не мигает и не трясётся", "不闪烁，不抖动", "ちかちかも、ゆれもなし", "कुछ नहीं टिमटिमाता, कुछ नहीं हिलता", "لا شيء يومض ولا شيء يهتز", "কিছু জ্বলে-নেভে না, কিছু কাঁপে না", "tak ada yang berkedip atau berguncang", "کچھ نہیں ٹمٹماتا، کچھ نہیں ہلتا"),
 "conf.auto": T("automatique", "automatic", "automático", "automatisch", "automatico", "automático", "автоматически", "自动", "自動", "अपने-आप", "تلقائي", "স্বয়ংক্রিয়", "otomatis", "خودکار"),
 "conf.aide": T("Change avec `tg confort taille 125`, `tg confort police facile`, `tg confort formes oui`, `tg confort calme oui` (ou `auto`) ; ou dans Options.", "Change with `tg confort taille 125`, `tg confort police facile`, `tg confort formes oui`, `tg confort calme oui` (or `auto`); or in Options.", "Cámbialo con `tg confort taille 125`, `tg confort police facile`, `tg confort formes oui`, `tg confort calme oui` (o `auto`); o en Opciones.", "Ändern mit `tg confort taille 125`, `tg confort police facile`, `tg confort formes oui`, `tg confort calme oui` (oder `auto`); oder in den Optionen.", "Cambia con `tg confort taille 125`, `tg confort police facile`, `tg confort formes oui`, `tg confort calme oui` (o `auto`); oppure in Opzioni.", "Muda com `tg confort taille 125`, `tg confort police facile`, `tg confort formes oui`, `tg confort calme oui` (ou `auto`); ou nas Opções.", "Изменить: `tg confort taille 125`, `tg confort police facile`, `tg confort formes oui`, `tg confort calme oui` (или `auto`); или в Настройках.", "更改：`tg confort taille 125`、`tg confort police facile`、`tg confort formes oui`、`tg confort calme oui`（或 `auto`）；或在选项里。", "変えるには `tg confort taille 125`、`tg confort police facile`、`tg confort formes oui`、`tg confort calme oui`（または `auto`）。オプションからも。", "बदलो: `tg confort taille 125`, `tg confort police facile`, `tg confort formes oui`, `tg confort calme oui` (या `auto`); या विकल्पों में।", "غيّر بـ `tg confort taille 125` و`tg confort police facile` و`tg confort formes oui` و`tg confort calme oui` (أو `auto`)؛ أو في الخيارات.", "বদলাও: `tg confort taille 125`, `tg confort police facile`, `tg confort formes oui`, `tg confort calme oui` (বা `auto`); অথবা অপশনে।", "Ubah dengan `tg confort taille 125`, `tg confort police facile`, `tg confort formes oui`, `tg confort calme oui` (atau `auto`); atau di Opsi.", "بدلو: `tg confort taille 125`، `tg confort police facile`، `tg confort formes oui`، `tg confort calme oui` (یا `auto`)؛ یا آپشنز میں۔"),
 "conf.aide.tel": T("Change avec `confort taille 125`, `confort police facile`, `confort formes oui`, `confort calme oui` (ou `auto`) ; ou dans `options`.", "Change with `confort taille 125`, `confort police facile`, `confort formes oui`, `confort calme oui` (or `auto`); or in `options`.", "Cámbialo con `confort taille 125`, `confort police facile`, `confort formes oui`, `confort calme oui` (o `auto`); o en `options`.", "Ändern mit `confort taille 125`, `confort police facile`, `confort formes oui`, `confort calme oui` (oder `auto`); oder in `options`.", "Cambia con `confort taille 125`, `confort police facile`, `confort formes oui`, `confort calme oui` (o `auto`); oppure in `options`.", "Muda com `confort taille 125`, `confort police facile`, `confort formes oui`, `confort calme oui` (ou `auto`); ou em `options`.", "Изменить: `confort taille 125`, `confort police facile`, `confort formes oui`, `confort calme oui` (или `auto`); или в `options`.", "更改：`confort taille 125`、`confort police facile`、`confort formes oui`、`confort calme oui`（或 `auto`）；或在 `options` 里。", "変えるには `confort taille 125`、`confort police facile`、`confort formes oui`、`confort calme oui`（または `auto`）。`options` からも。", "बदलो: `confort taille 125`, `confort police facile`, `confort formes oui`, `confort calme oui` (या `auto`); या `options` में।", "غيّر بـ `confort taille 125` و`confort police facile` و`confort formes oui` و`confort calme oui` (أو `auto`)؛ أو في `options`.", "বদলাও: `confort taille 125`, `confort police facile`, `confort formes oui`, `confort calme oui` (বা `auto`); অথবা `options`-এ।", "Ubah dengan `confort taille 125`, `confort police facile`, `confort formes oui`, `confort calme oui` (atau `auto`); atau di `options`.", "بدلو: `confort taille 125`، `confort police facile`، `confort formes oui`، `confort calme oui` (یا `auto`)؛ یا `options` میں۔"),
 "conf.ok": T("C'est réglé.", "Done.", "Listo.", "Erledigt.", "Fatto.", "Pronto.", "Готово.", "设置好了。", "設定しました。", "हो गया।", "تم الضبط.", "ঠিক করা হলো।", "Sudah diatur.", "ہو گیا۔"),
 "conf.faux": T("Je n'ai pas compris ce réglage.", "I didn't understand that setting.", "No entendí ese ajuste.", "Diese Einstellung verstehe ich nicht.", "Non ho capito questa impostazione.", "Não entendi esse ajuste.", "Не понял эту настройку.", "我没听懂这个设置。", "その設定はわかりませんでした。", "यह सेटिंग समझ नहीं आई।", "لم أفهم هذا الإعداد.", "এই সেটিং বুঝিনি।", "Aku tidak paham pengaturan itu.", "یہ سیٹنگ سمجھ نہیں آئی۔"),
 "conf.defi": T("⚡ DÉFI : tape « `{cmd}` » (sans chrono, prends ton temps)", "⚡ CHALLENGE: type “`{cmd}`” (no timer, take your time)", "⚡ RETO: escribe «`{cmd}`» (sin reloj, tómate tu tiempo)", "⚡ CHALLENGE: tippe „`{cmd}`“ (ohne Uhr, lass dir Zeit)", "⚡ SFIDA: scrivi «`{cmd}`» (senza tempo, con calma)", "⚡ DESAFIO: digite «`{cmd}`» (sem cronômetro, com calma)", "⚡ ВЫЗОВ: набери «`{cmd}`» (без таймера, не спеши)", "⚡ 挑战：输入“`{cmd}`”（不计时，慢慢来）", "⚡ チャレンジ：「`{cmd}`」と打とう（時間制限なし、ゆっくりでいいよ）", "⚡ चुनौती: “`{cmd}`” लिखो (बिना घड़ी, आराम से)", "⚡ تحدٍّ: اكتب «`{cmd}`» (بلا مؤقت، على مهلك)", "⚡ চ্যালেঞ্জ: “`{cmd}`” লেখো (সময় নেই, ধীরে)", "⚡ TANTANGAN: ketik “`{cmd}`” (tanpa waktu, santai saja)", "⚡ چیلنج: “`{cmd}`” لکھو (بغیر گھڑی، آرام سے)"),
 "conf.defi.dit": T("⚡ Défi ! Tape « `{cmd}` », prends ton temps.", "⚡ Challenge! Type “`{cmd}`”, take your time.", "⚡ ¡Reto! Escribe «`{cmd}`», tómate tu tiempo.", "⚡ Challenge! Tippe „`{cmd}`“, lass dir Zeit.", "⚡ Sfida! Scrivi «`{cmd}`», con calma.", "⚡ Desafio! Digite «`{cmd}`», com calma.", "⚡ Вызов! Набери «`{cmd}`», не спеши.", "⚡ 挑战！输入“`{cmd}`”，慢慢来。", "⚡ チャレンジ！「`{cmd}`」と打とう、ゆっくりでいいよ。", "⚡ चुनौती! “`{cmd}`” लिखो, आराम से।", "⚡ تحدٍّ! اكتب «`{cmd}`» على مهلك.", "⚡ চ্যালেঞ্জ! “`{cmd}`” লেখো, ধীরে।", "⚡ Tantangan! Ketik “`{cmd}`”, santai saja.", "⚡ چیلنج! “`{cmd}`” لکھو، آرام سے۔"),
}

# les autres groupes de textes (mode classe, place, carte de visite) : textes_classe2.py
sys.path.insert(0, str(Path(__file__).resolve().parent))
from textes_classe2 import K2  # noqa: E402
from textes_seances import K3  # noqa: E402

K.update(K2)
K.update(K3)


def ecrire(p, d):
    tmp = str(p) + ".tmp~"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, p)


def ajouter(racine):
    racine = Path(racine)
    n = 0
    for d in ("pc/tg/langues", "app/src/main/assets/langues"):
        for code in L:
            p = racine / d / f"{code}.json"
            data = json.loads(p.read_text(encoding="utf-8"))
            for k, v in K.items():
                if data.get(k) != v[code]:
                    data[k] = v[code]
                    n += 1
            ecrire(p, data)
    return n


if __name__ == "__main__":
    print("clés écrites :", ajouter(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[3]))
