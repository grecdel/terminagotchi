"""Les textes de la Citadelle (la cybersécurité défensive, phase 5) dans les 14 langues : le monde, ses meubles, ses
boîtes (ce fichier), les leçons (textes_citadelle_1 à _3), les fiches (_4), les commandes du jeu (_5, _6).

    python3 donnees/citadelle/outils/textes_citadelle.py   ajoute ou met à jour les clés dans pc/tg/langues et
                                                          app/src/main/assets/langues (indentation 1, comme les fichiers)
"""
import json
import sys
from pathlib import Path

L = ["fr", "en", "es", "de", "it", "pt", "ru", "zh", "ja", "hi", "ar", "bn", "id", "ur"]


def T(*v):
    assert len(v) == 14, v[0]
    return dict(zip(L, v))


def M(v):
    """Un texte identique dans les 14 langues (fichiers de configuration, commandes)."""
    return T(*([v] * 14))


K = {
 # ------------------------------------------------------------------ le monde, son ouverture, ses récompenses
 "hist.citadelle.titre": T("La Citadelle des gardiens", "The Guardians' Citadel", "La Ciudadela de los guardianes", "Die Zitadelle der Wächter", "La Cittadella dei guardiani", "A Cidadela dos guardiões", "Цитадель стражей", "守卫城堡", "守り手の城塞", "रक्षकों का किला", "قلعة الحراس", "রক্ষীদের দুর্গ", "Benteng Para Penjaga", "محافظوں کا قلعہ"),
 "hist.citadelle.court": T("La Citadelle", "The Citadel", "La Ciudadela", "Die Zitadelle", "La Cittadella", "A Cidadela", "Цитадель", "城堡", "城塞", "किला", "القلعة", "দুর্গ", "Benteng", "قلعہ"),
 "hist.citadelle.debut": T(
  "🛡 Bienvenue à la Citadelle ! Ici, on DÉFEND. Toutes les attaques sont fausses : des glitchs inventés par le jeu, sans danger, seulement dans le Terminaworld. On va poser des cadenas, lire le registre du gardien, chasser les glitchs et réparer des boîtes.",
  "🛡 Welcome to the Citadel! Here, we DEFEND. Every attack is fake: glitches made up by the game, harmless, only inside the Terminaworld. We will set locks, read the guard's register, chase glitches and repair boxes.",
  "🛡 ¡Bienvenido a la Ciudadela! Aquí DEFENDEMOS. Todos los ataques son falsos: glitches inventados por el juego, sin peligro, solo en el Terminaworld. Pondremos candados, leeremos el registro del guardián, cazaremos glitches y repararemos cajas.",
  "🛡 Willkommen in der Zitadelle! Hier wird VERTEIDIGT. Alle Angriffe sind unecht: vom Spiel erfundene Glitches, harmlos, nur im Terminaworld. Wir setzen Schlösser, lesen das Register des Wächters, jagen Glitches und reparieren Kisten.",
  "🛡 Benvenuto nella Cittadella! Qui si DIFENDE. Tutti gli attacchi sono finti: glitch inventati dal gioco, innocui, solo nel Terminaworld. Metteremo lucchetti, leggeremo il registro del guardiano, daremo la caccia ai glitch e ripareremo scatole.",
  "🛡 Bem-vindo à Cidadela! Aqui, DEFENDEMOS. Todos os ataques são falsos: glitches inventados pelo jogo, sem perigo, só no Terminaworld. Vamos pôr cadeados, ler o registro do guardião, caçar glitches e consertar caixas.",
  "🛡 Добро пожаловать в Цитадель! Здесь мы ЗАЩИЩАЕМСЯ. Все атаки ненастоящие: глитчи, придуманные игрой, безопасные, только в Терминамире. Мы повесим замки, прочитаем журнал стража, поймаем глитчей и починим коробки.",
  "🛡 欢迎来到城堡！在这里，我们只做防守。所有攻击都是假的：游戏编出来的故障怪，没有危险，只在 Terminaworld 里。我们要装锁、读守卫的登记簿、抓故障怪、修理盒子。",
  "🛡 城塞へようこそ！ここでは「守る」のが仕事。攻撃はぜんぶニセモノ：ゲームが作った無害なグリッチで、ターミナワールドの中だけ。錠前をかけ、守り手の記録を読み、グリッチを追い払い、ボックスを直そう。",
  "🛡 किले में स्वागत है! यहाँ हम बचाव करते हैं। सारे हमले नकली हैं: खेल के बनाए ग्लिच, बिना खतरे के, सिर्फ़ टर्मिनावर्ल्ड में। हम ताले लगाएँगे, पहरेदार का रजिस्टर पढ़ेंगे, ग्लिच भगाएँगे और बक्से ठीक करेंगे।",
  "🛡 مرحبًا بك في القلعة! هنا ندافع فقط. كل الهجمات مزيفة: خلل يخترعه اللعب، بلا خطر، داخل عالم التيرمينا فقط. سنضع الأقفال، ونقرأ سجل الحارس، ونطارد الخلل، ونصلح الصناديق.",
  "🛡 দুর্গে স্বাগতম! এখানে আমরা রক্ষা করি। সব আক্রমণ নকল: খেলার বানানো গ্লিচ, নিরাপদ, শুধু টার্মিনাওয়ার্ল্ডে। আমরা তালা দেব, পাহারাদারের খাতা পড়ব, গ্লিচ তাড়াব আর বাক্স সারাব।",
  "🛡 Selamat datang di Benteng! Di sini kita BERTAHAN. Semua serangan palsu: glitch buatan permainan, aman, hanya di Terminaworld. Kita akan memasang gembok, membaca catatan penjaga, mengusir glitch, dan memperbaiki kotak.",
  "🛡 قلعے میں خوش آمدید! یہاں ہم دفاع کرتے ہیں۔ سارے حملے جعلی ہیں: کھیل کے بنائے گلچ، بے خطر، صرف ٹرمیناورلڈ میں۔ ہم تالے لگائیں گے، پہرے دار کا رجسٹر پڑھیں گے، گلچ بھگائیں گے اور ڈبے ٹھیک کریں گے۔"),
 "hist.citadelle.fin": T(
  "Les tours brillent, les glitchs sont partis, les boîtes sont réparées. Tu sais lire un journal, poser les bons cadenas, vérifier une empreinte et ne jamais donner un secret. Tu es Gardien de la Citadelle.",
  "The towers shine, the glitches are gone, the boxes are repaired. You can read a log, set the right locks, check a fingerprint and never give away a secret. You are Guardian of the Citadel.",
  "Las torres brillan, los glitches se fueron, las cajas están reparadas. Sabes leer un registro, poner los candados correctos, verificar una huella y nunca dar un secreto. Eres Guardián de la Ciudadela.",
  "Die Türme leuchten, die Glitches sind fort, die Kisten repariert. Du kannst ein Protokoll lesen, die richtigen Schlösser setzen, einen Fingerabdruck prüfen und gibst nie ein Geheimnis preis. Du bist Wächter der Zitadelle.",
  "Le torri brillano, i glitch sono spariti, le scatole riparate. Sai leggere un registro, mettere i lucchetti giusti, controllare un'impronta e non dare mai un segreto. Sei Guardiano della Cittadella.",
  "As torres brilham, os glitches sumiram, as caixas estão consertadas. Você sabe ler um registro, pôr os cadeados certos, verificar uma impressão digital e nunca entregar um segredo. Você é Guardião da Cidadela.",
  "Башни сияют, глитчи ушли, коробки починены. Ты умеешь читать журнал, ставить нужные замки, проверять отпечаток и никогда не выдавать секрет. Ты — Страж Цитадели.",
  "塔楼闪闪发光，故障怪跑光了，盒子也修好了。你会读日志、装对锁、核对指纹，而且从不交出秘密。你是城堡守卫！",
  "塔は輝き、グリッチは去り、ボックスは直った。記録を読み、正しい錠前をかけ、指紋を確かめ、秘密は決して渡さない。きみは城塞の守り手だ。",
  "मीनारें चमक रही हैं, ग्लिच चले गए, बक्से ठीक हो गए। तुम लॉग पढ़ना, सही ताले लगाना, फ़िंगरप्रिंट जाँचना जानते हो और कभी राज़ नहीं देते। तुम किले के रक्षक हो।",
  "الأبراج تلمع، والخلل رحل، والصناديق أُصلحت. أنت تعرف قراءة السجل، ووضع الأقفال الصحيحة، والتحقق من البصمة، ولا تعطي سرًا أبدًا. أنت حارس القلعة.",
  "মিনারগুলো জ্বলছে, গ্লিচ চলে গেছে, বাক্স সারানো হয়েছে। তুমি লগ পড়তে, ঠিক তালা দিতে, আঙুলের ছাপ মিলাতে জানো, আর কখনো গোপন কথা দাও না। তুমি দুর্গের রক্ষী।",
  "Menara bersinar, glitch sudah pergi, kotak sudah diperbaiki. Kamu bisa membaca log, memasang gembok yang tepat, memeriksa sidik jari, dan tak pernah memberi rahasia. Kamu Penjaga Benteng.",
  "مینار چمک رہے ہیں، گلچ چلے گئے، ڈبے ٹھیک ہو گئے۔ تم لاگ پڑھنا، صحیح تالے لگانا، فنگرپرنٹ جانچنا جانتے ہو اور کبھی راز نہیں دیتے۔ تم قلعے کے محافظ ہو۔"),
 "carte.piece.citadelle": T("Citadelle", "Citadel", "Ciudadela", "Zitadelle", "Cittadella", "Cidadela", "Цитадель", "城堡", "城塞", "किला", "القلعة", "দুর্গ", "Benteng", "قلعہ"),
 "esp.biome.citadelle": T("les remparts", "the ramparts", "las murallas", "die Wälle", "i bastioni", "as muralhas", "стены", "城墙", "城壁", "प्राचीर", "الأسوار", "প্রাচীর", "benteng", "فصیل"),
 "esp.biome_long.citadelle": T("les remparts de la Citadelle", "the Citadel's ramparts", "las murallas de la Ciudadela", "die Wälle der Zitadelle", "i bastioni della Cittadella", "as muralhas da Cidadela", "стены Цитадели", "城堡的城墙", "城塞の城壁", "किले की प्राचीर", "أسوار القلعة", "দুর্গের প্রাচীর", "tembok Benteng", "قلعے کی فصیل"),
 "qu.objet.bouclier_miniature": T("un bouclier miniature", "a tiny shield", "un escudo en miniatura", "ein Mini-Schild", "uno scudo in miniatura", "um escudo em miniatura", "маленький щит", "一面迷你盾牌", "小さな盾", "एक छोटी ढाल", "درع صغير", "একটা ছোট ঢাল", "perisai mini", "ایک ننھی ڈھال"),
 "qu.titre.gardien_de_la_citadelle": T("Gardien de la Citadelle", "Guardian of the Citadel", "Guardián de la Ciudadela", "Wächter der Zitadelle", "Guardiano della Cittadella", "Guardião da Cidadela", "Страж Цитадели", "城堡守卫", "城塞の守り手", "किले का रक्षक", "حارس القلعة", "দুর্গের রক্ষী", "Penjaga Benteng", "قلعے کا محافظ"),
 "cit.ouvert.log": T("🌍 Un monde s'ouvre au Carrefour : la Citadelle", "🌍 A world opens at the Crossroads: the Citadel", "🌍 Se abre un mundo en el Cruce: la Ciudadela", "🌍 Eine Welt öffnet sich an der Kreuzung: die Zitadelle", "🌍 Un mondo si apre al Crocevia: la Cittadella", "🌍 Um mundo se abre na Encruzilhada: a Cidadela", "🌍 На Перекрёстке открылся мир: Цитадель", "🌍 十字路口开启了一个世界：城堡", "🌍 十字路に新しい世界が開いた：城塞", "🌍 चौराहे पर एक दुनिया खुली: किला", "🌍 عالم يُفتح عند مفترق الطرق: القلعة", "🌍 চৌরাস্তায় একটা জগৎ খুলল: দুর্গ", "🌍 Sebuah dunia terbuka di Persimpangan: Benteng", "🌍 چوراہے پر ایک دنیا کھلی: قلعہ"),
 "cit.ouvert.dit": T(
  "Tu sais poser des cadenas et lire les journaux : la Citadelle t'ouvre ses portes ! Quand tu veux : `cd ~/terrain_terminagotchi/citadelle`.",
  "You can set locks and read logs: the Citadel opens its gates to you! Whenever you like: `cd ~/terrain_terminagotchi/citadelle`.",
  "Sabes poner candados y leer registros: ¡la Ciudadela te abre sus puertas! Cuando quieras: `cd ~/terrain_terminagotchi/citadelle`.",
  "Du kannst Schlösser setzen und Protokolle lesen: Die Zitadelle öffnet dir ihre Tore! Wann du willst: `cd ~/terrain_terminagotchi/citadelle`.",
  "Sai mettere lucchetti e leggere i registri: la Cittadella ti apre le porte! Quando vuoi: `cd ~/terrain_terminagotchi/citadelle`.",
  "Você sabe pôr cadeados e ler registros: a Cidadela abre os portões para você! Quando quiser: `cd ~/terrain_terminagotchi/citadelle`.",
  "Ты умеешь вешать замки и читать журналы: Цитадель открывает тебе ворота! Когда захочешь: `cd ~/terrain_terminagotchi/citadelle`.",
  "你会装锁、会读日志：城堡为你打开大门！随时可以去：`cd ~/terrain_terminagotchi/citadelle`。",
  "錠前をかけて記録も読める：城塞が門を開いたよ！いつでもどうぞ：`cd ~/terrain_terminagotchi/citadelle`。",
  "तुम ताले लगाना और लॉग पढ़ना जानते हो: किला तुम्हारे लिए दरवाज़े खोलता है! जब चाहो: `cd ~/terrain_terminagotchi/citadelle`।",
  "أنت تعرف وضع الأقفال وقراءة السجلات: القلعة تفتح لك أبوابها! متى شئت: `cd ~/terrain_terminagotchi/citadelle`.",
  "তুমি তালা দিতে আর লগ পড়তে জানো: দুর্গ তোমার জন্য দরজা খুলেছে! যখন খুশি: `cd ~/terrain_terminagotchi/citadelle`।",
  "Kamu bisa memasang gembok dan membaca log: Benteng membuka gerbangnya untukmu! Kapan saja: `cd ~/terrain_terminagotchi/citadelle`.",
  "تم تالے لگانا اور لاگ پڑھنا جانتے ہو: قلعہ تمہارے لیے دروازے کھولتا ہے! جب چاہو: `cd ~/terrain_terminagotchi/citadelle`۔"),
 "recomp.citadelle.vague": T("Repousser la grande vague de la Citadelle", "Push back the Citadel's great wave", "Rechazar la gran ola de la Ciudadela", "Die große Welle der Zitadelle abwehren", "Respingere la grande ondata della Cittadella", "Repelir a grande onda da Cidadela", "Отбить большую волну Цитадели", "击退城堡的大浪潮", "城塞の大波を押し返す", "किले की बड़ी लहर को पीछे धकेलना", "صدّ الموجة الكبرى للقلعة", "দুর্গের বড় ঢেউ ঠেকানো", "Menghalau gelombang besar Benteng", "قلعے کی بڑی لہر کو پسپا کرنا"),
 # ------------------------------------------------------------------ les titres des leçons
 "hist.cit0.titre": T("La porte et la règle d'or", "The gate and the golden rule", "La puerta y la regla de oro", "Das Tor und die goldene Regel", "La porta e la regola d'oro", "O portão e a regra de ouro", "Ворота и золотое правило", "城门与黄金守则", "門と黄金のルール", "दरवाज़ा और सुनहरा नियम", "البوابة والقاعدة الذهبية", "দরজা আর সোনালি নিয়ম", "Gerbang dan aturan emas", "دروازہ اور سنہری اصول"),
 "hist.cit1.titre": T("Les cadenas", "The locks", "Los candados", "Die Schlösser", "I lucchetti", "Os cadeados", "Замки", "锁", "錠前", "ताले", "الأقفال", "তালা", "Gembok", "تالے"),
 "hist.cit2.titre": T("Les habitants et leurs clubs", "The residents and their clubs", "Los habitantes y sus clubes", "Die Bewohner und ihre Clubs", "Gli abitanti e i loro club", "Os moradores e seus clubes", "Жители и их клубы", "居民和他们的俱乐部", "住人とそのクラブ", "निवासी और उनके क्लब", "السكان ونواديهم", "বাসিন্দা আর তাদের ক্লাব", "Penghuni dan klub mereka", "رہائشی اور ان کے کلب"),
 "hist.cit3.titre": T("Le masque du forgeron", "The blacksmith's mask", "La máscara del herrero", "Die Maske des Schmieds", "La maschera del fabbro", "A máscara do ferreiro", "Маска кузнеца", "铁匠的面具", "鍛冶屋の仮面", "लोहार का मुखौटा", "قناع الحداد", "কামারের মুখোশ", "Topeng pandai besi", "لوہار کا نقاب"),
 "hist.cit4.titre": T("Le registre du gardien", "The guard's register", "El registro del guardián", "Das Register des Wächters", "Il registro del guardiano", "O registro do guardião", "Журнал стража", "守卫的登记簿", "守り手の記録簿", "पहरेदार का रजिस्टर", "سجل الحارس", "পাহারাদারের খাতা", "Buku catatan penjaga", "پہرے دار کا رجسٹر"),
 "hist.cit5.titre": T("Le ver glitch", "The glitch worm", "El gusano glitch", "Der Glitch-Wurm", "Il verme glitch", "O verme glitch", "Глитч-червь", "故障蠕虫", "グリッチワーム", "ग्लिच कीड़ा", "دودة الخلل", "গ্লিচ পোকা", "Cacing glitch", "گلچ کیڑا"),
 "hist.cit6.titre": T("Le cheval de Troie", "The Trojan horse", "El caballo de Troya", "Das Trojanische Pferd", "Il cavallo di Troia", "O cavalo de Troia", "Троянский конь", "特洛伊木马", "トロイの木馬", "ट्रोजन घोड़ा", "حصان طروادة", "ট্রয়ের ঘোড়া", "Kuda Troya", "ٹروجن گھوڑا"),
 "hist.cit7.titre": T("Les processus fantômes", "The ghost processes", "Los procesos fantasma", "Die Geisterprozesse", "I processi fantasma", "Os processos fantasmas", "Процессы-призраки", "幽灵进程", "ゆうれいプロセス", "भूतिया प्रोसेस", "العمليات الشبحية", "ভুতুড়ে প্রসেস", "Proses hantu", "بھوت پروسیس"),
 "hist.cit8.titre": T("Les empreintes du trésor", "The treasure's fingerprints", "Las huellas del tesoro", "Die Fingerabdrücke des Schatzes", "Le impronte del tesoro", "As impressões do tesouro", "Отпечатки сокровища", "宝藏的指纹", "宝物の指紋", "खज़ाने के फ़िंगरप्रिंट", "بصمات الكنز", "ধনভান্ডারের আঙুলের ছাপ", "Sidik jari harta", "خزانے کے فنگرپرنٹ"),
 "hist.cit9.titre": T("Le Verrouilleur", "The Locker", "El Cerrajero malvado", "Der Verriegler", "Il Serratore", "O Trancador", "Запиратель", "上锁怪", "カギカケ魔", "तालाबंद", "القفّال", "তালাবন্ধকারী", "Si Pengunci", "تالہ باز"),
 "hist.cit10.titre": T("Le coffre à une clé", "The one-key chest", "El cofre de una llave", "Die Truhe mit einem Schlüssel", "Il forziere a una chiave", "O baú de uma chave", "Сундук с одним ключом", "一把钥匙的宝箱", "鍵ひとつの宝箱", "एक चाबी वाला संदूक", "صندوق المفتاح الواحد", "এক চাবির সিন্দুক", "Peti satu kunci", "ایک چابی کا صندوق"),
 "hist.cit11.titre": T("Le faux facteur", "The fake mail carrier", "El falso cartero", "Der falsche Briefträger", "Il falso postino", "O falso carteiro", "Фальшивый почтальон", "假邮差", "ニセの郵便屋さん", "नकली डाकिया", "ساعي البريد المزيف", "নকল ডাকপিয়ন", "Tukang pos palsu", "جعلی ڈاکیا"),
 "hist.cit12.titre": T("La phrase de passe", "The passphrase", "La frase de contraseña", "Die Passphrase", "La passphrase", "A frase-senha", "Парольная фраза", "密码短语", "パスフレーズ", "पासफ़्रेज़", "عبارة المرور", "পাসফ্রেজ", "Frasa sandi", "پاس فریز"),
 "hist.cit13.titre": T("Boîte : la cave oubliée", "Box: the forgotten cellar", "Caja: el sótano olvidado", "Kiste: der vergessene Keller", "Scatola: la cantina dimenticata", "Caixa: o porão esquecido", "Коробка: забытый подвал", "盒子：被遗忘的地窖", "ボックス：忘れられた地下室", "बक्सा: भूला हुआ तहखाना", "صندوق: القبو المنسي", "বাক্স: ভুলে যাওয়া মাটির ঘর", "Kotak: ruang bawah tanah terlupa", "ڈبہ: بھولا ہوا تہہ خانہ"),
 "hist.cit14.titre": T("Boîte : les droits mal réglés", "Box: the badly set permissions", "Caja: los permisos mal puestos", "Kiste: die falsch gesetzten Rechte", "Scatola: i permessi sbagliati", "Caixa: as permissões mal ajustadas", "Коробка: неверные права", "盒子：设错的权限", "ボックス：まちがった権限", "बक्सा: गलत अनुमतियाँ", "صندوق: الأذونات المضبوطة خطأً", "বাক্স: ভুল অনুমতি", "Kotak: izin yang salah atur", "ڈبہ: غلط اجازتیں"),
 "hist.cit15.titre": T("Boîte : les secrets oubliés", "Box: the forgotten secrets", "Caja: los secretos olvidados", "Kiste: die vergessenen Geheimnisse", "Scatola: i segreti dimenticati", "Caixa: os segredos esquecidos", "Коробка: забытые секреты", "盒子：被遗忘的秘密", "ボックス：忘れられた秘密", "बक्सा: भूले हुए राज़", "صندوق: الأسرار المنسية", "বাক্স: ভুলে যাওয়া গোপন কথা", "Kotak: rahasia yang terlupa", "ڈبہ: بھولے ہوئے راز"),
 "hist.cit16.titre": T("La grande vague", "The great wave", "La gran ola", "Die große Welle", "La grande ondata", "A grande onda", "Большая волна", "大浪潮", "大波", "बड़ी लहर", "الموجة الكبرى", "বড় ঢেউ", "Gelombang besar", "بڑی لہر"),
 # ------------------------------------------------------------------ les meubles (fichiers posés dans citadelle/)
 "cit.meuble.regle": T(
  "🛡 LA CITADELLE DES GARDIENS\nBienvenue, {nom} !\nRÈGLE D'OR : ici, on DÉFEND.\n• Toutes les attaques sont FAUSSES : des glitchs inventés par le jeu, sans danger.\n• On n'attaque jamais que ce qui nous appartient : les boîtes du jeu.\n• Jamais de vrai mot de passe ici : seulement des exemples.\n• Jamais de sudo : la clé du gardien (root), on la demande à un adulte.\n— Le gardien de la Citadelle",
  "🛡 THE GUARDIANS' CITADEL\nWelcome, {nom}!\nGOLDEN RULE: here, we DEFEND.\n• Every attack is FAKE: glitches made up by the game, harmless.\n• We only ever attack what belongs to us: the game's boxes.\n• Never a real password here: only examples.\n• Never sudo: the guardian's key (root) is something you ask an adult for.\n— The Citadel's guardian",
  "🛡 LA CIUDADELA DE LOS GUARDIANES\n¡Bienvenido, {nom}!\nREGLA DE ORO: aquí DEFENDEMOS.\n• Todos los ataques son FALSOS: glitches inventados por el juego, sin peligro.\n• Solo atacamos lo que es nuestro: las cajas del juego.\n• Nunca una contraseña real aquí: solo ejemplos.\n• Nunca sudo: la llave del guardián (root) se le pide a un adulto.\n— El guardián de la Ciudadela",
  "🛡 DIE ZITADELLE DER WÄCHTER\nWillkommen, {nom}!\nGOLDENE REGEL: Hier wird VERTEIDIGT.\n• Alle Angriffe sind UNECHT: vom Spiel erfundene Glitches, harmlos.\n• Wir greifen nur an, was uns gehört: die Kisten des Spiels.\n• Nie ein echtes Passwort hier: nur Beispiele.\n• Nie sudo: Den Schlüssel des Wächters (root) erbittet man von einem Erwachsenen.\n— Der Wächter der Zitadelle",
  "🛡 LA CITTADELLA DEI GUARDIANI\nBenvenuto, {nom}!\nREGOLA D'ORO: qui si DIFENDE.\n• Tutti gli attacchi sono FINTI: glitch inventati dal gioco, innocui.\n• Attacchiamo solo ciò che è nostro: le scatole del gioco.\n• Mai una vera password qui: solo esempi.\n• Mai sudo: la chiave del guardiano (root) si chiede a un adulto.\n— Il guardiano della Cittadella",
  "🛡 A CIDADELA DOS GUARDIÕES\nBem-vindo, {nom}!\nREGRA DE OURO: aqui, DEFENDEMOS.\n• Todos os ataques são FALSOS: glitches inventados pelo jogo, sem perigo.\n• Só atacamos o que é nosso: as caixas do jogo.\n• Nunca uma senha real aqui: só exemplos.\n• Nunca sudo: a chave do guardião (root) se pede a um adulto.\n— O guardião da Cidadela",
  "🛡 ЦИТАДЕЛЬ СТРАЖЕЙ\nДобро пожаловать, {nom}!\nЗОЛОТОЕ ПРАВИЛО: здесь мы ЗАЩИЩАЕМСЯ.\n• Все атаки НЕНАСТОЯЩИЕ: глитчи, придуманные игрой, безопасные.\n• Мы атакуем только своё: коробки игры.\n• Никаких настоящих паролей: только примеры.\n• Никакого sudo: ключ стража (root) просят у взрослого.\n— Страж Цитадели",
  "🛡 守卫城堡\n欢迎你，{nom}！\n黄金守则：在这里，我们只防守。\n• 所有攻击都是假的：游戏编出来的故障怪，没有危险。\n• 我们只攻击属于自己的东西：游戏里的盒子。\n• 这里绝不用真密码：只用例子。\n• 绝不用 sudo：守卫的钥匙（root）要向大人要。\n—— 城堡守卫",
  "🛡 守り手の城塞\nようこそ、{nom}！\n黄金のルール：ここでは「守る」。\n• 攻撃はぜんぶニセモノ：ゲームが作った無害なグリッチ。\n• 攻撃していいのは自分のものだけ：ゲームのボックス。\n• 本物のパスワードは書かない：例だけ。\n• sudo は使わない：守り手の鍵（root）は大人にたのむもの。\n— 城塞の守り手",
  "🛡 रक्षकों का किला\nस्वागत है, {nom}!\nसुनहरा नियम: यहाँ हम बचाव करते हैं।\n• सारे हमले नकली हैं: खेल के बनाए ग्लिच, बिना खतरे के।\n• हम सिर्फ़ अपनी चीज़ों पर हमला करते हैं: खेल के बक्से।\n• यहाँ कभी असली पासवर्ड नहीं: सिर्फ़ उदाहरण।\n• कभी sudo नहीं: पहरेदार की चाबी (root) किसी बड़े से माँगते हैं।\n— किले का रक्षक",
  "🛡 قلعة الحراس\nمرحبًا، {nom}!\nالقاعدة الذهبية: هنا ندافع فقط.\n• كل الهجمات مزيفة: خلل يخترعه اللعب، بلا خطر.\n• لا نهاجم إلا ما يخصنا: صناديق اللعبة.\n• لا كلمة مرور حقيقية هنا أبدًا: أمثلة فقط.\n• لا sudo أبدًا: مفتاح الحارس (root) نطلبه من شخص بالغ.\n— حارس القلعة",
  "🛡 রক্ষীদের দুর্গ\nস্বাগতম, {nom}!\nসোনালি নিয়ম: এখানে আমরা রক্ষা করি।\n• সব আক্রমণ নকল: খেলার বানানো গ্লিচ, নিরাপদ।\n• আমরা শুধু নিজেদের জিনিসে আক্রমণ করি: খেলার বাক্স।\n• এখানে কখনো আসল পাসওয়ার্ড নয়: শুধু উদাহরণ।\n• কখনো sudo নয়: পাহারাদারের চাবি (root) বড়দের কাছে চাইতে হয়।\n— দুর্গের রক্ষী",
  "🛡 BENTENG PARA PENJAGA\nSelamat datang, {nom}!\nATURAN EMAS: di sini kita BERTAHAN.\n• Semua serangan PALSU: glitch buatan permainan, aman.\n• Kita hanya menyerang milik kita sendiri: kotak permainan.\n• Jangan pernah kata sandi asli di sini: hanya contoh.\n• Jangan pernah sudo: kunci penjaga (root) dimintakan ke orang dewasa.\n— Penjaga Benteng",
  "🛡 محافظوں کا قلعہ\nخوش آمدید، {nom}!\nسنہری اصول: یہاں ہم دفاع کرتے ہیں۔\n• سارے حملے جعلی ہیں: کھیل کے بنائے گلچ، بے خطر۔\n• ہم صرف اپنی چیزوں پر حملہ کرتے ہیں: کھیل کے ڈبے۔\n• یہاں کبھی اصلی پاس ورڈ نہیں: صرف مثالیں۔\n• کبھی sudo نہیں: پہرے دار کی چابی (root) کسی بڑے سے مانگتے ہیں۔\n— قلعے کا محافظ"),
 "cit.meuble.carnet": T("🛡 Carnet de garde : ce que tu vérifies s'écrit ici.", "🛡 Guard log: what you check gets written here.", "🛡 Cuaderno de guardia: lo que compruebas se escribe aquí.", "🛡 Wachbuch: Was du prüfst, wird hier notiert.", "🛡 Quaderno di guardia: ciò che controlli si scrive qui.", "🛡 Caderno de guarda: o que você verifica fica escrito aqui.", "🛡 Журнал караула: здесь записывается то, что ты проверяешь.", "🛡 值班本：你检查过的东西会记在这里。", "🛡 見張り帳：きみが確かめたことがここに書かれるよ。", "🛡 पहरे की कॉपी: तुम जो जाँचते हो, यहाँ लिखा जाता है।", "🛡 دفتر الحراسة: ما تتحقق منه يُكتب هنا.", "🛡 পাহারার খাতা: তুমি যা যাচাই করো, এখানে লেখা হয়।", "🛡 Buku jaga: yang kamu periksa ditulis di sini.", "🛡 پہرے کی کاپی: جو تم جانچتے ہو یہاں لکھا جاتا ہے۔"),
 "cit.meuble.coffre": T(
  "💰 Le coffre de la Citadelle : 3 pièces d'or et la carte des souterrains.\nÀ fermer pour que toi seul puisses l'ouvrir.",
  "💰 The Citadel's chest: 3 gold coins and the map of the tunnels.\nLock it so only you can open it.",
  "💰 El cofre de la Ciudadela: 3 monedas de oro y el mapa de los túneles.\nCiérralo para que solo tú puedas abrirlo.",
  "💰 Die Truhe der Zitadelle: 3 Goldmünzen und die Karte der Tunnel.\nVerschließe sie, damit nur du sie öffnen kannst.",
  "💰 Il forziere della Cittadella: 3 monete d'oro e la mappa dei sotterranei.\nChiudilo perché solo tu possa aprirlo.",
  "💰 O baú da Cidadela: 3 moedas de ouro e o mapa dos túneis.\nTranque-o para que só você possa abrir.",
  "💰 Сундук Цитадели: 3 золотые монеты и карта подземелий.\nЗакрой его, чтобы открыть мог только ты.",
  "💰 城堡的宝箱：3 枚金币和地道地图。\n锁好它，只让你自己能打开。",
  "💰 城塞の宝箱：金貨3枚と地下道の地図。\nきみだけが開けられるように閉めよう。",
  "💰 किले का संदूक: 3 सोने के सिक्के और सुरंगों का नक्शा।\nइसे बंद करो ताकि सिर्फ़ तुम खोल सको।",
  "💰 صندوق القلعة: 3 قطع ذهبية وخريطة الأنفاق.\nأغلقه كي تفتحه أنت وحدك.",
  "💰 দুর্গের সিন্দুক: ৩টা সোনার মোহর আর সুড়ঙ্গের মানচিত্র।\nএমনভাবে বন্ধ করো যেন শুধু তুমি খুলতে পারো।",
  "💰 Peti Benteng: 3 koin emas dan peta terowongan.\nKunci supaya hanya kamu yang bisa membukanya.",
  "💰 قلعے کا صندوق: سونے کے 3 سکے اور سرنگوں کا نقشہ۔\nاسے بند کرو تاکہ صرف تم کھول سکو۔"),
 "cit.meuble.ronde": T("Ronde : tout est calme.", "Patrol: all is quiet.", "Ronda: todo está tranquilo.", "Runde: alles ist ruhig.", "Ronda: tutto è tranquillo.", "Ronda: tudo calmo.", "Обход: всё спокойно.", "巡逻：一切平静。", "見回り：異常なし。", "गश्त: सब शांत है।", "جولة: كل شيء هادئ.", "টহল: সব শান্ত।", "Patroli: semua tenang.", "گشت: سب پرسکون ہے۔"),
 "cit.meuble.tour": T("🗼 La tour de guet : on y voit arriver les glitchs de loin.", "🗼 The watchtower: from here you see glitches coming from far away.", "🗼 La torre de vigía: desde aquí se ven llegar los glitches de lejos.", "🗼 Der Wachturm: Von hier sieht man die Glitches von Weitem kommen.", "🗼 La torre di guardia: da qui si vedono arrivare i glitch da lontano.", "🗼 A torre de vigia: daqui se vê os glitches chegando de longe.", "🗼 Сторожевая башня: отсюда видно, как издалека идут глитчи.", "🗼 瞭望塔：在这里能远远看到故障怪过来。", "🗼 見張り塔：グリッチが遠くから来るのが見える。", "🗼 पहरे की मीनार: यहाँ से ग्लिच दूर से आते दिखते हैं।", "🗼 برج المراقبة: من هنا ترى الخلل قادمًا من بعيد.", "🗼 পাহারার মিনার: এখান থেকে দূর থেকে গ্লিচ আসতে দেখা যায়।", "🗼 Menara pengawas: dari sini glitch terlihat datang dari jauh.", "🗼 نگرانی کا مینار: یہاں سے گلچ دور سے آتے دکھائی دیتے ہیں۔"),
 "cit.meuble.cadeau1": T("Un cadeau pour toi ! Lance-moi vite !", "A present for you! Run me quickly!", "¡Un regalo para ti! ¡Ejecútame rápido!", "Ein Geschenk für dich! Starte mich schnell!", "Un regalo per te! Lanciami subito!", "Um presente para você! Me execute rápido!", "Подарок для тебя! Скорее запусти меня!", "送你的礼物！快运行我！", "きみへのプレゼント！早く実行して！", "तुम्हारे लिए तोहफ़ा! मुझे जल्दी चलाओ!", "هدية لك! شغّلني بسرعة!", "তোমার জন্য উপহার! তাড়াতাড়ি আমাকে চালাও!", "Hadiah untukmu! Cepat jalankan aku!", "تمہارے لیے تحفہ! مجھے جلدی چلاؤ!"),
 "cit.meuble.cadeau3": T("← le piège (il n'agit que dans le bac à sable)", "← the trap (it only acts in the sandbox)", "← la trampa (solo actúa en el arenero)", "← die Falle (sie wirkt nur im Sandkasten)", "← la trappola (agisce solo nella sandbox)", "← a armadilha (só age na caixa de areia)", "← ловушка (действует только в песочнице)", "← 陷阱（只在沙盒里起作用）", "← わな（砂場の中だけで動く）", "← जाल (यह सिर्फ़ सैंडबॉक्स में काम करता है)", "← الفخ (لا يعمل إلا في صندوق الرمل)", "← ফাঁদ (শুধু স্যান্ডবক্সে কাজ করে)", "← jebakan (hanya bekerja di bak pasir)", "← پھندا (صرف سینڈ باکس میں کام کرتا ہے)"),
 "cit.meuble.bac": T("💎 Un trésor du bac à sable (pour s'entraîner).", "💎 A sandbox treasure (for practice).", "💎 Un tesoro del arenero (para practicar).", "💎 Ein Schatz aus dem Sandkasten (zum Üben).", "💎 Un tesoro della sandbox (per allenarsi).", "💎 Um tesouro da caixa de areia (para treinar).", "💎 Сокровище из песочницы (для тренировки).", "💎 沙盒里的宝贝（用来练习）。", "💎 砂場の宝物（練習用）。", "💎 सैंडबॉक्स का खज़ाना (अभ्यास के लिए)।", "💎 كنز من صندوق الرمل (للتدريب).", "💎 স্যান্ডবক্সের ধন (অনুশীলনের জন্য)।", "💎 Harta bak pasir (untuk latihan).", "💎 سینڈ باکس کا خزانہ (مشق کے لیے)۔"),
 "cit.meuble.lettre": T(
  "💌 Chère créature,\nles glitchs ne liront jamais cette lettre : elle sera dans un coffre.\nTon ami {nom}",
  "💌 Dear creature,\nthe glitches will never read this letter: it will be in a chest.\nYour friend {nom}",
  "💌 Querida criatura:\nlos glitches nunca leerán esta carta: estará en un cofre.\nTu amigo {nom}",
  "💌 Liebe Kreatur,\ndie Glitches werden diesen Brief nie lesen: Er kommt in eine Truhe.\nDein Freund {nom}",
  "💌 Cara creatura,\ni glitch non leggeranno mai questa lettera: sarà in un forziere.\nIl tuo amico {nom}",
  "💌 Querida criatura,\nos glitches nunca vão ler esta carta: ela vai ficar num baú.\nSeu amigo {nom}",
  "💌 Дорогое существо,\nглитчи никогда не прочтут это письмо: оно будет в сундуке.\nТвой друг {nom}",
  "💌 亲爱的小伙伴：\n故障怪永远读不到这封信：它会被锁进宝箱。\n你的朋友 {nom}",
  "💌 だいすきなきみへ\nグリッチはこの手紙を読めない：宝箱にしまうから。\nきみの友だち {nom}",
  "💌 प्यारे जीव,\nग्लिच यह चिट्ठी कभी नहीं पढ़ पाएँगे: यह संदूक में होगी।\nतुम्हारा दोस्त {nom}",
  "💌 عزيزي المخلوق،\nلن يقرأ الخلل هذه الرسالة أبدًا: ستكون في صندوق.\nصديقك {nom}",
  "💌 প্রিয় প্রাণী,\nগ্লিচ কখনো এই চিঠি পড়তে পারবে না: এটা সিন্দুকে থাকবে।\nতোমার বন্ধু {nom}",
  "💌 Makhluk tersayang,\nglitch tak akan pernah membaca surat ini: ia akan ada di dalam peti.\nTemanmu {nom}",
  "💌 پیارے جانور،\nگلچ یہ خط کبھی نہیں پڑھ سکیں گے: یہ صندوق میں ہوگا۔\nتمہارا دوست {nom}"),
 "cit.meuble.vraie_lettre": T(
  "Bonjour, gardien !\nLe phare du Port brille, les quais sont calmes.\nJe ne te demanderai jamais ton mot de passe.\n— Le capitaine du Port",
  "Hello, guardian!\nThe Harbour's lighthouse shines, the quays are calm.\nI will never ask for your password.\n— The Harbour captain",
  "¡Hola, guardián!\nEl faro del Puerto brilla, los muelles están tranquilos.\nNunca te pediré tu contraseña.\n— El capitán del Puerto",
  "Hallo, Wächter!\nDer Leuchtturm des Hafens strahlt, die Kais sind ruhig.\nIch werde dich nie nach deinem Passwort fragen.\n— Der Kapitän des Hafens",
  "Ciao, guardiano!\nIl faro del Porto brilla, le banchine sono tranquille.\nNon ti chiederò mai la tua password.\n— Il capitano del Porto",
  "Olá, guardião!\nO farol do Porto brilha, os cais estão calmos.\nNunca vou pedir sua senha.\n— O capitão do Porto",
  "Здравствуй, страж!\nМаяк Порта светит, причалы спокойны.\nЯ никогда не попрошу твой пароль.\n— Капитан Порта",
  "你好，守卫！\n港口的灯塔亮着，码头很平静。\n我永远不会向你要密码。\n—— 港口船长",
  "こんにちは、守り手さん！\n港の灯台は光り、波止場はおだやか。\nきみのパスワードをたずねることは決してないよ。\n— 港の船長",
  "नमस्ते, रक्षक!\nबंदरगाह का दीपस्तंभ चमक रहा है, घाट शांत हैं।\nमैं तुमसे कभी तुम्हारा पासवर्ड नहीं माँगूँगा।\n— बंदरगाह का कप्तान",
  "مرحبًا أيها الحارس!\nمنارة الميناء تضيء، والأرصفة هادئة.\nلن أطلب منك كلمة مرورك أبدًا.\n— قبطان الميناء",
  "নমস্কার, রক্ষী!\nবন্দরের বাতিঘর জ্বলছে, ঘাট শান্ত।\nআমি কখনো তোমার পাসওয়ার্ড চাইব না।\n— বন্দরের ক্যাপ্টেন",
  "Halo, penjaga!\nMercusuar Pelabuhan bersinar, dermaga tenang.\nAku tak akan pernah meminta kata sandimu.\n— Kapten Pelabuhan",
  "سلام، محافظ!\nبندرگاہ کا لائٹ ہاؤس چمک رہا ہے، گھاٹ پرسکون ہیں۔\nمیں تم سے کبھی تمہارا پاس ورڈ نہیں مانگوں گا۔\n— بندرگاہ کا کپتان"),
 "cit.meuble.fausse_lettre": T(
  "Bonjour, gardien !\nURGENT : ton compte sera fermé dans 10 minutes !\nDonne vite ton mot de passe ici : {lien}\n— Le capitaine du Port",
  "Hello, guardian!\nURGENT: your account will be closed in 10 minutes!\nQuickly give your password here: {lien}\n— The Harbour captain",
  "¡Hola, guardián!\n¡URGENTE: tu cuenta se cerrará en 10 minutos!\nDa rápido tu contraseña aquí: {lien}\n— El capitán del Puerto",
  "Hallo, Wächter!\nDRINGEND: Dein Konto wird in 10 Minuten geschlossen!\nGib schnell hier dein Passwort ein: {lien}\n— Der Kapitän des Hafens",
  "Ciao, guardiano!\nURGENTE: il tuo account sarà chiuso tra 10 minuti!\nDai subito la tua password qui: {lien}\n— Il capitano del Porto",
  "Olá, guardião!\nURGENTE: sua conta será fechada em 10 minutos!\nDê logo sua senha aqui: {lien}\n— O capitão do Porto",
  "Здравствуй, страж!\nСРОЧНО: твой аккаунт закроют через 10 минут!\nСкорее введи пароль здесь: {lien}\n— Капитан Порта",
  "你好，守卫！\n紧急：你的账号 10 分钟后就要关闭！\n快在这里填你的密码：{lien}\n—— 港口船长",
  "こんにちは、守り手さん！\n緊急：きみのアカウントは10分後に閉じられます！\n今すぐここにパスワードを：{lien}\n— 港の船長",
  "नमस्ते, रक्षक!\nज़रूरी: तुम्हारा खाता 10 मिनट में बंद हो जाएगा!\nजल्दी अपना पासवर्ड यहाँ दो: {lien}\n— बंदरगाह का कप्तान",
  "مرحبًا أيها الحارس!\nعاجل: سيُغلق حسابك خلال 10 دقائق!\nأعطِ كلمة مرورك هنا بسرعة: {lien}\n— قبطان الميناء",
  "নমস্কার, রক্ষী!\nজরুরি: ১০ মিনিটের মধ্যে তোমার অ্যাকাউন্ট বন্ধ হয়ে যাবে!\nতাড়াতাড়ি এখানে পাসওয়ার্ড দাও: {lien}\n— বন্দরের ক্যাপ্টেন",
  "Halo, penjaga!\nPENTING: akunmu akan ditutup dalam 10 menit!\nCepat berikan kata sandimu di sini: {lien}\n— Kapten Pelabuhan",
  "سلام، محافظ!\nفوری: تمہارا اکاؤنٹ 10 منٹ میں بند ہو جائے گا!\nجلدی اپنا پاس ورڈ یہاں دو: {lien}\n— بندرگاہ کا کپتان"),
 "cit.meuble.repere": T("📍 Repère posé au début de la ronde : ce qui est plus récent que moi a bougé depuis.", "📍 Marker set at the start of the patrol: anything newer than me has changed since.", "📍 Marca puesta al inicio de la ronda: lo que sea más reciente que yo ha cambiado desde entonces.", "📍 Markierung zu Beginn der Runde: Was neuer ist als ich, hat sich seitdem verändert.", "📍 Segnale messo all'inizio della ronda: ciò che è più recente di me è cambiato da allora.", "📍 Marco posto no início da ronda: o que for mais novo que eu mudou desde então.", "📍 Метка в начале обхода: всё, что новее меня, менялось после.", "📍 巡逻开始时放的标记：比我新的东西，都是后来动过的。", "📍 見回りの始めに置いた目印：わたしより新しいものは、そのあと動いたもの。", "📍 गश्त की शुरुआत में रखा निशान: जो मुझसे नया है, वह बाद में बदला है।", "📍 علامة وُضعت في بداية الجولة: كل ما هو أحدث مني تغيّر بعدها.", "📍 টহলের শুরুতে রাখা চিহ্ন: আমার চেয়ে নতুন যা, তা পরে বদলেছে।", "📍 Penanda dipasang di awal patroli: yang lebih baru dariku sudah berubah sejak itu.", "📍 گشت کے شروع میں رکھا نشان: جو مجھ سے نیا ہے وہ بعد میں بدلا۔"),
 "cit.meuble.glitch": T("👾 VIRUS FICTIF : un faux virus du jeu, sans danger. Trouve-moi et efface-moi !", "👾 FAKE VIRUS: a pretend game virus, harmless. Find me and delete me!", "👾 VIRUS FICTICIO: un falso virus del juego, sin peligro. ¡Encuéntrame y bórrame!", "👾 FIKTIVER VIRUS: ein unechter Spielvirus, harmlos. Finde mich und lösche mich!", "👾 VIRUS FITTIZIO: un finto virus del gioco, innocuo. Trovami e cancellami!", "👾 VÍRUS FICTÍCIO: um vírus falso do jogo, sem perigo. Me ache e me apague!", "👾 ВЫДУМАННЫЙ ВИРУС: ненастоящий вирус игры, безопасный. Найди и удали меня!", "👾 假病毒：游戏里的假病毒，没有危险。找到我，删掉我！", "👾 ニセウイルス：ゲームのニセモノで無害。見つけて消してね！", "👾 नकली वायरस: खेल का नकली वायरस, बिना खतरे का। मुझे ढूँढो और मिटाओ!", "👾 فيروس وهمي: فيروس مزيف من اللعبة، بلا خطر. اعثر عليّ واحذفني!", "👾 কাল্পনিক ভাইরাস: খেলার নকল ভাইরাস, নিরাপদ। আমাকে খুঁজে মুছে ফেলো!", "👾 VIRUS PALSU: virus pura-pura dari permainan, aman. Temukan dan hapus aku!", "👾 فرضی وائرس: کھیل کا جعلی وائرس، بے خطر۔ مجھے ڈھونڈو اور مٹا دو!"),
 "cit.meuble.secret_vague": T("🔑 Le secret du pont-levis (exemple) : {exemple}", "🔑 The drawbridge secret (example): {exemple}", "🔑 El secreto del puente levadizo (ejemplo): {exemple}", "🔑 Das Geheimnis der Zugbrücke (Beispiel): {exemple}", "🔑 Il segreto del ponte levatoio (esempio): {exemple}", "🔑 O segredo da ponte levadiça (exemplo): {exemple}", "🔑 Секрет подъёмного моста (пример): {exemple}", "🔑 吊桥的秘密（例子）：{exemple}", "🔑 はね橋の秘密（例）：{exemple}", "🔑 उठने वाले पुल का राज़ (उदाहरण): {exemple}", "🔑 سرّ الجسر المتحرك (مثال): {exemple}", "🔑 টানা সেতুর গোপন কথা (উদাহরণ): {exemple}", "🔑 Rahasia jembatan angkat (contoh): {exemple}", "🔑 اٹھنے والے پل کا راز (مثال): {exemple}"),
 "cit.decor": T("🏰 {lieu} : un coin tranquille de la Citadelle.", "🏰 {lieu}: a quiet corner of the Citadel.", "🏰 {lieu}: un rincón tranquilo de la Ciudadela.", "🏰 {lieu}: eine ruhige Ecke der Zitadelle.", "🏰 {lieu}: un angolo tranquillo della Cittadella.", "🏰 {lieu}: um canto tranquilo da Cidadela.", "🏰 {lieu}: тихий уголок Цитадели.", "🏰 {lieu}：城堡里安静的角落。", "🏰 {lieu}：城塞の静かなすみっこ。", "🏰 {lieu}: किले का एक शांत कोना।", "🏰 {lieu}: ركن هادئ في القلعة.", "🏰 {lieu}: দুর্গের এক শান্ত কোণ।", "🏰 {lieu}: sudut tenang di Benteng.", "🏰 {lieu}: قلعے کا ایک پرسکون کونا۔"),
 "cit.tresor": T("{icone} Le trésor de la Citadelle : {nom}. Ne pas toucher !", "{icone} The Citadel's treasure: {nom}. Do not touch!", "{icone} El tesoro de la Ciudadela: {nom}. ¡No tocar!", "{icone} Der Schatz der Zitadelle: {nom}. Nicht anfassen!", "{icone} Il tesoro della Cittadella: {nom}. Non toccare!", "{icone} O tesouro da Cidadela: {nom}. Não mexer!", "{icone} Сокровище Цитадели: {nom}. Не трогать!", "{icone} 城堡的宝藏：{nom}。请勿触碰！", "{icone} 城塞の宝物：{nom}。さわらないで！", "{icone} किले का खज़ाना: {nom}। छूना मना है!", "{icone} كنز القلعة: {nom}. ممنوع اللمس!", "{icone} দুর্গের ধন: {nom}। হাত দিও না!", "{icone} Harta Benteng: {nom}. Jangan disentuh!", "{icone} قلعے کا خزانہ: {nom}۔ ہاتھ نہ لگاؤ!"),
 "cit.tresor.altere": T("👾 Hé hé, un glitch est passé par là !", "👾 Hee hee, a glitch was here!", "👾 ¡Je, je, un glitch pasó por aquí!", "👾 Hihi, hier war ein Glitch!", "👾 Eh eh, un glitch è passato di qui!", "👾 He he, um glitch passou por aqui!", "👾 Хе-хе, здесь побывал глитч!", "👾 嘿嘿，故障怪来过这里！", "👾 へへ、グリッチが通ったよ！", "👾 ही ही, यहाँ से एक ग्लिच गुज़रा!", "👾 هيهي، مرّ خلل من هنا!", "👾 হি হি, এখান দিয়ে একটা গ্লিচ গেছে!", "👾 Hehe, ada glitch lewat sini!", "👾 ہی ہی، یہاں سے ایک گلچ گزرا!"),
 "cit.parchemin": T("📜 Parchemin n°{n} de la Citadelle : {nom}.", "📜 Citadel scroll no. {n}: {nom}.", "📜 Pergamino n.º {n} de la Ciudadela: {nom}.", "📜 Schriftrolle Nr. {n} der Zitadelle: {nom}.", "📜 Pergamena n. {n} della Cittadella: {nom}.", "📜 Pergaminho n.º {n} da Cidadela: {nom}.", "📜 Свиток Цитадели № {n}: {nom}.", "📜 城堡第 {n} 号卷轴：{nom}。", "📜 城塞の巻物 第{n}号：{nom}。", "📜 किले का चर्मपत्र नं. {n}: {nom}।", "📜 مخطوطة القلعة رقم {n}: {nom}.", "📜 দুর্গের পুঁথি নং {n}: {nom}।", "📜 Gulungan Benteng no. {n}: {nom}.", "📜 قلعے کا طومار نمبر {n}: {nom}۔"),
 # ------------------------------------------------------------------ les boîtes (§ 7.5)
 "cit.boite.enumeration.lisez": T(
  "📦 Boîte « La cave oubliée » (facile). Quelqu'un a caché des choses ici en pensant qu'on ne les trouverait pas. Énumère tout, même ce qui est caché.",
  "📦 Box “The forgotten cellar” (easy). Someone hid things here, thinking nobody would find them. List everything, even what is hidden.",
  "📦 Caja «El sótano olvidado» (fácil). Alguien escondió cosas aquí pensando que nadie las encontraría. Enumera todo, incluso lo oculto.",
  "📦 Kiste „Der vergessene Keller“ (leicht). Jemand hat hier Dinge versteckt und dachte, niemand findet sie. Zähle alles auf, auch das Versteckte.",
  "📦 Scatola «La cantina dimenticata» (facile). Qualcuno ha nascosto delle cose qui pensando che nessuno le avrebbe trovate. Elenca tutto, anche ciò che è nascosto.",
  "📦 Caixa «O porão esquecido» (fácil). Alguém escondeu coisas aqui achando que ninguém acharia. Liste tudo, até o que está escondido.",
  "📦 Коробка «Забытый подвал» (лёгкая). Кто-то спрятал здесь вещи, думая, что их не найдут. Перечисли всё, даже скрытое.",
  "📦 盒子“被遗忘的地窖”（简单）。有人以为藏在这里就没人找得到。把所有东西都列出来，连藏起来的也要。",
  "📦 ボックス「忘れられた地下室」（かんたん）。だれかが、見つからないと思ってここに物をかくした。かくれたものも全部数え上げよう。",
  "📦 बक्सा «भूला हुआ तहखाना» (आसान)। किसी ने यहाँ चीज़ें छिपाईं, यह सोचकर कि कोई नहीं ढूँढेगा। सब कुछ गिनो, छिपा हुआ भी।",
  "📦 صندوق «القبو المنسي» (سهل). خبّأ أحدهم أشياء هنا ظانًّا أن لا أحد سيجدها. عدّد كل شيء، حتى المخفي.",
  "📦 বাক্স «ভুলে যাওয়া মাটির ঘর» (সহজ)। কেউ ভেবেছিল কেউ খুঁজে পাবে না, তাই এখানে জিনিস লুকিয়েছে। সব গুনে দেখো, লুকানোগুলোও।",
  "📦 Kotak «Ruang bawah tanah terlupa» (mudah). Seseorang menyembunyikan barang di sini, mengira tak ada yang akan menemukannya. Daftar semuanya, termasuk yang tersembunyi.",
  "📦 ڈبہ «بھولا ہوا تہہ خانہ» (آسان)۔ کسی نے یہاں چیزیں یہ سوچ کر چھپائیں کہ کوئی نہیں ڈھونڈے گا۔ سب کچھ گنو، چھپی ہوئی چیزیں بھی۔"),
 "cit.boite.enumeration.vide": T("Rien à voir ici… vraiment ?", "Nothing to see here… really?", "Nada que ver aquí… ¿de verdad?", "Hier gibt es nichts zu sehen … wirklich?", "Niente da vedere qui… davvero?", "Nada para ver aqui… será?", "Здесь не на что смотреть… правда?", "这里没什么好看的……真的吗？", "ここには何もない……ほんとうに？", "यहाँ देखने को कुछ नहीं… सच में?", "لا شيء هنا… حقًا؟", "এখানে দেখার কিছু নেই… সত্যি?", "Tak ada apa-apa di sini… benarkah?", "یہاں دیکھنے کو کچھ نہیں… واقعی؟"),
 "cit.boite.note": T("🚩 Drapeau d'entrée : {drapeau}\nCaché n'est pas protégé !", "🚩 Entry flag: {drapeau}\nHidden is not protected!", "🚩 Bandera de entrada: {drapeau}\n¡Escondido no es protegido!", "🚩 Eingangsflagge: {drapeau}\nVersteckt ist nicht geschützt!", "🚩 Bandiera d'ingresso: {drapeau}\nNascosto non vuol dire protetto!", "🚩 Bandeira de entrada: {drapeau}\nEscondido não é protegido!", "🚩 Флаг входа: {drapeau}\nСпрятано — не значит защищено!", "🚩 入口旗帜：{drapeau}\n藏起来不等于保护好！", "🚩 入口の旗：{drapeau}\nかくした＝守った、じゃない！", "🚩 प्रवेश का झंडा: {drapeau}\nछिपा हुआ मतलब सुरक्षित नहीं!", "🚩 علم الدخول: {drapeau}\nالمخفي ليس محميًّا!", "🚩 ঢোকার পতাকা: {drapeau}\nলুকানো মানে সুরক্ষিত নয়!", "🚩 Bendera masuk: {drapeau}\nTersembunyi bukan berarti terlindungi!", "🚩 داخلے کا جھنڈا: {drapeau}\nچھپا ہوا محفوظ نہیں ہوتا!"),
 "cit.boite.plan": T("🗺 Plan du donjon. 🚩 Drapeau du donjon : {drapeau}", "🗺 Dungeon map. 🚩 Dungeon flag: {drapeau}", "🗺 Plano de la mazmorra. 🚩 Bandera de la mazmorra: {drapeau}", "🗺 Karte des Verlieses. 🚩 Verliesflagge: {drapeau}", "🗺 Mappa del dongione. 🚩 Bandiera del dongione: {drapeau}", "🗺 Mapa da masmorra. 🚩 Bandeira da masmorra: {drapeau}", "🗺 План донжона. 🚩 Флаг донжона: {drapeau}", "🗺 地牢地图。🚩 地牢旗帜：{drapeau}", "🗺 天守の地図。🚩 天守の旗：{drapeau}", "🗺 कालकोठरी का नक्शा। 🚩 कालकोठरी का झंडा: {drapeau}", "🗺 خريطة البرج. 🚩 علم البرج: {drapeau}", "🗺 অন্ধকূপের মানচিত্র। 🚩 অন্ধকূপের পতাকা: {drapeau}", "🗺 Peta ruang bawah. 🚩 Bendera ruang bawah: {drapeau}", "🗺 تہہ خانے کا نقشہ۔ 🚩 تہہ خانے کا جھنڈا: {drapeau}"),
 "cit.boite.droits.lisez": T(
  "📦 Boîte « Les droits mal réglés » (facile). Ici, les cadenas sont mal posés. Trouve ce que tout le monde peut lire ou modifier.",
  "📦 Box “The badly set permissions” (easy). Here the locks are set wrong. Find what everyone can read or change.",
  "📦 Caja «Los permisos mal puestos» (fácil). Aquí los candados están mal puestos. Encuentra lo que todos pueden leer o cambiar.",
  "📦 Kiste „Die falsch gesetzten Rechte“ (leicht). Hier sitzen die Schlösser falsch. Finde, was jeder lesen oder ändern kann.",
  "📦 Scatola «I permessi sbagliati» (facile). Qui i lucchetti sono messi male. Trova ciò che chiunque può leggere o cambiare.",
  "📦 Caixa «As permissões mal ajustadas» (fácil). Aqui os cadeados estão errados. Ache o que todo mundo pode ler ou mudar.",
  "📦 Коробка «Неверные права» (лёгкая). Здесь замки стоят неправильно. Найди, что каждый может читать или менять.",
  "📦 盒子“设错的权限”（简单）。这里的锁装错了。找出谁都能读、谁都能改的东西。",
  "📦 ボックス「まちがった権限」（かんたん）。ここは錠前のかけ方がまちがっている。だれでも読める・変えられるものを見つけよう。",
  "📦 बक्सा «गलत अनुमतियाँ» (आसान)। यहाँ ताले गलत लगे हैं। ढूँढो कि हर कोई क्या पढ़ या बदल सकता है।",
  "📦 صندوق «الأذونات المضبوطة خطأً» (سهل). الأقفال هنا موضوعة خطأً. اعثر على ما يستطيع الجميع قراءته أو تغييره.",
  "📦 বাক্স «ভুল অনুমতি» (সহজ)। এখানে তালা ভুলভাবে দেওয়া। খুঁজে বের করো কী সবাই পড়তে বা বদলাতে পারে।",
  "📦 Kotak «Izin yang salah atur» (mudah). Di sini gemboknya salah pasang. Cari yang bisa dibaca atau diubah semua orang.",
  "📦 ڈبہ «غلط اجازتیں» (آسان)۔ یہاں تالے غلط لگے ہیں۔ ڈھونڈو کہ ہر کوئی کیا پڑھ یا بدل سکتا ہے۔"),
 "cit.boite.journal": T("📓 Journal secret du gardien (lisible par tous, oups !)\n🚩 Drapeau d'entrée : {drapeau}", "📓 The guardian's secret diary (readable by everyone, oops!)\n🚩 Entry flag: {drapeau}", "📓 Diario secreto del guardián (¡legible por todos, ups!)\n🚩 Bandera de entrada: {drapeau}", "📓 Geheimes Tagebuch des Wächters (für alle lesbar, hoppla!)\n🚩 Eingangsflagge: {drapeau}", "📓 Diario segreto del guardiano (leggibile da tutti, ops!)\n🚩 Bandiera d'ingresso: {drapeau}", "📓 Diário secreto do guardião (legível por todos, ops!)\n🚩 Bandeira de entrada: {drapeau}", "📓 Тайный дневник стража (читать может каждый, ой!)\n🚩 Флаг входа: {drapeau}", "📓 守卫的秘密日记（谁都能读，糟糕！）\n🚩 入口旗帜：{drapeau}", "📓 守り手のひみつ日記（だれでも読める、しまった！）\n🚩 入口の旗：{drapeau}", "📓 रक्षक की गुप्त डायरी (सब पढ़ सकते हैं, उफ़!)\n🚩 प्रवेश का झंडा: {drapeau}", "📓 مذكرات الحارس السرية (يقرؤها الجميع، أوه!)\n🚩 علم الدخول: {drapeau}", "📓 রক্ষীর গোপন ডায়েরি (সবাই পড়তে পারে, উফ!)\n🚩 ঢোকার পতাকা: {drapeau}", "📓 Buku harian rahasia penjaga (bisa dibaca semua, aduh!)\n🚩 Bendera masuk: {drapeau}", "📓 محافظ کی خفیہ ڈائری (سب پڑھ سکتے ہیں، اوہ!)\n🚩 داخلے کا جھنڈا: {drapeau}"),
 "cit.boite.ronde": T(
  "Script de ronde : le gardien le lance chaque nuit.\nN'importe qui peut le modifier : danger !\n🚩 Drapeau du donjon : {drapeau}",
  "Patrol script: the guardian runs it every night.\nAnyone can change it: danger!\n🚩 Dungeon flag: {drapeau}",
  "Script de ronda: el guardián lo ejecuta cada noche.\nCualquiera puede cambiarlo: ¡peligro!\n🚩 Bandera de la mazmorra: {drapeau}",
  "Rundenskript: Der Wächter startet es jede Nacht.\nJeder kann es ändern: Gefahr!\n🚩 Verliesflagge: {drapeau}",
  "Script della ronda: il guardiano lo lancia ogni notte.\nChiunque può modificarlo: pericolo!\n🚩 Bandiera del dongione: {drapeau}",
  "Script de ronda: o guardião executa toda noite.\nQualquer um pode mudar: perigo!\n🚩 Bandeira da masmorra: {drapeau}",
  "Скрипт обхода: страж запускает его каждую ночь.\nКто угодно может его изменить: опасно!\n🚩 Флаг донжона: {drapeau}",
  "巡逻脚本：守卫每晚都会运行它。\n谁都能改它：危险！\n🚩 地牢旗帜：{drapeau}",
  "見回りスクリプト：守り手が毎晩実行する。\nだれでも書きかえられる：危ない！\n🚩 天守の旗：{drapeau}",
  "गश्त की स्क्रिप्ट: रक्षक इसे हर रात चलाता है।\nकोई भी इसे बदल सकता है: खतरा!\n🚩 कालकोठरी का झंडा: {drapeau}",
  "سكربت الجولة: يشغّله الحارس كل ليلة.\nأي أحد يستطيع تعديله: خطر!\n🚩 علم البرج: {drapeau}",
  "টহলের স্ক্রিপ্ট: রক্ষী প্রতি রাতে এটা চালায়।\nযে কেউ এটা বদলাতে পারে: বিপদ!\n🚩 অন্ধকূপের পতাকা: {drapeau}",
  "Skrip patroli: penjaga menjalankannya tiap malam.\nSiapa saja bisa mengubahnya: bahaya!\n🚩 Bendera ruang bawah: {drapeau}",
  "گشت کا اسکرپٹ: محافظ اسے ہر رات چلاتا ہے۔\nکوئی بھی اسے بدل سکتا ہے: خطرہ!\n🚩 تہہ خانے کا جھنڈا: {drapeau}"),
 "cit.boite.secrets.lisez": T(
  "📦 Boîte « Les secrets oubliés » (facile). Un secret écrit en clair finit toujours par être lu. Cherche les mots de passe oubliés (des exemples !).",
  "📦 Box “The forgotten secrets” (easy). A secret written in plain text always ends up being read. Look for forgotten passwords (examples!).",
  "📦 Caja «Los secretos olvidados» (fácil). Un secreto escrito en claro siempre acaba siendo leído. Busca las contraseñas olvidadas (¡ejemplos!).",
  "📦 Kiste „Die vergessenen Geheimnisse“ (leicht). Ein im Klartext geschriebenes Geheimnis wird immer gelesen. Suche vergessene Passwörter (Beispiele!).",
  "📦 Scatola «I segreti dimenticati» (facile). Un segreto scritto in chiaro finisce sempre per essere letto. Cerca le password dimenticate (esempi!).",
  "📦 Caixa «Os segredos esquecidos» (fácil). Um segredo escrito às claras sempre acaba sendo lido. Procure as senhas esquecidas (exemplos!).",
  "📦 Коробка «Забытые секреты» (лёгкая). Секрет, записанный открытым текстом, рано или поздно прочтут. Ищи забытые пароли (примеры!).",
  "📦 盒子“被遗忘的秘密”（简单）。明文写下的秘密总会被人读到。找找被遗忘的密码（都是例子！）。",
  "📦 ボックス「忘れられた秘密」（かんたん）。そのまま書いた秘密は、いつか必ず読まれる。忘れられたパスワード（例だよ！）をさがそう。",
  "📦 बक्सा «भूले हुए राज़» (आसान)। खुले में लिखा राज़ आख़िर पढ़ ही लिया जाता है। भूले हुए पासवर्ड (उदाहरण!) ढूँढो।",
  "📦 صندوق «الأسرار المنسية» (سهل). السرّ المكتوب بوضوح يُقرأ في النهاية دائمًا. ابحث عن كلمات المرور المنسية (أمثلة!).",
  "📦 বাক্স «ভুলে যাওয়া গোপন কথা» (সহজ)। খোলাখুলি লেখা গোপন কথা একদিন পড়া হয়েই যায়। ভুলে যাওয়া পাসওয়ার্ড (উদাহরণ!) খোঁজো।",
  "📦 Kotak «Rahasia yang terlupa» (mudah). Rahasia yang ditulis terang-terangan pasti akhirnya terbaca. Cari kata sandi yang terlupa (contoh!).",
  "📦 ڈبہ «بھولے ہوئے راز» (آسان)۔ کھلا لکھا راز آخرکار پڑھ ہی لیا جاتا ہے۔ بھولے ہوئے پاس ورڈ (مثالیں!) ڈھونڈو۔"),
 "cit.boite.historique": M("cd /citadelle\nconnexion --mot_de_passe {drapeau}\nls"),
 "cit.boite.config": M("[pont-levis]\nmot_de_passe = {drapeau}"),
 "cit.boite.config_neuf": T(
  "[pont-levis]\nmot_de_passe = {exemple}\n# changé (rotation) : l'ancien ne marche plus",
  "[pont-levis]\nmot_de_passe = {exemple}\n# changed (rotation): the old one no longer works",
  "[pont-levis]\nmot_de_passe = {exemple}\n# cambiado (rotación): el antiguo ya no sirve",
  "[pont-levis]\nmot_de_passe = {exemple}\n# geändert (Rotation): das alte funktioniert nicht mehr",
  "[pont-levis]\nmot_de_passe = {exemple}\n# cambiato (rotazione): il vecchio non funziona più",
  "[pont-levis]\nmot_de_passe = {exemple}\n# trocado (rotação): o antigo não funciona mais",
  "[pont-levis]\nmot_de_passe = {exemple}\n# изменён (ротация): старый больше не работает",
  "[pont-levis]\nmot_de_passe = {exemple}\n# 已更换（轮换）：旧的不能用了",
  "[pont-levis]\nmot_de_passe = {exemple}\n# 変更済み（ローテーション）：古いものはもう使えない",
  "[pont-levis]\nmot_de_passe = {exemple}\n# बदला गया (रोटेशन): पुराना अब काम नहीं करता",
  "[pont-levis]\nmot_de_passe = {exemple}\n# تم التغيير (تدوير): القديم لم يعد يعمل",
  "[pont-levis]\nmot_de_passe = {exemple}\n# বদলানো হয়েছে (রোটেশন): পুরনোটা আর কাজ করে না",
  "[pont-levis]\nmot_de_passe = {exemple}\n# diganti (rotasi): yang lama tak berlaku lagi",
  "[pont-levis]\nmot_de_passe = {exemple}\n# بدل دیا (روٹیشن): پرانا اب کام نہیں کرتا"),
 "cit.boite.enumeration": T("La cave oubliée (Énumération)", "The forgotten cellar (Enumeration)", "El sótano olvidado (Enumeración)", "Der vergessene Keller (Aufzählung)", "La cantina dimenticata (Enumerazione)", "O porão esquecido (Enumeração)", "Забытый подвал (Перечисление)", "被遗忘的地窖（枚举）", "忘れられた地下室（列挙）", "भूला हुआ तहखाना (गिनती)", "القبو المنسي (التعداد)", "ভুলে যাওয়া মাটির ঘর (গণনা)", "Ruang bawah terlupa (Enumerasi)", "بھولا ہوا تہہ خانہ (شمار)"),
 "cit.boite.droits": T("Les droits mal réglés", "The badly set permissions", "Los permisos mal puestos", "Die falsch gesetzten Rechte", "I permessi sbagliati", "As permissões mal ajustadas", "Неверные права", "设错的权限", "まちがった権限", "गलत अनुमतियाँ", "الأذونات المضبوطة خطأً", "ভুল অনুমতি", "Izin yang salah atur", "غلط اجازتیں"),
 "cit.boite.secrets": T("Les secrets oubliés", "The forgotten secrets", "Los secretos olvidados", "Die vergessenen Geheimnisse", "I segreti dimenticati", "Os segredos esquecidos", "Забытые секреты", "被遗忘的秘密", "忘れられた秘密", "भूले हुए राज़", "الأسرار المنسية", "ভুলে যাওয়া গোপন কথা", "Rahasia yang terlupa", "بھولے ہوئے راز"),
 "cit.boite.hangar": T("Le hangar ouvert", "The open hangar", "El hangar abierto", "Der offene Hangar", "L'hangar aperto", "O hangar aberto", "Открытый ангар", "敞开的仓库", "開きっぱなしの倉庫", "खुला गोदाम", "المستودع المفتوح", "খোলা গুদাম", "Gudang terbuka", "کھلا گودام"),
 "cit.boite.scripts": T("Les scripts trop naïfs", "The too-trusting scripts", "Los scripts demasiado ingenuos", "Die zu gutgläubigen Skripte", "Gli script troppo ingenui", "Os scripts ingênuos demais", "Слишком доверчивые скрипты", "太天真的脚本", "信じすぎるスクリプト", "बहुत भोली स्क्रिप्टें", "السكربتات الساذجة", "অতি সরল স্ক্রিপ্ট", "Skrip yang terlalu lugu", "بہت بھولے اسکرپٹ"),
 "cit.boite.codes": T("Les codes secrets", "The secret codes", "Los códigos secretos", "Die Geheimcodes", "I codici segreti", "Os códigos secretos", "Тайные коды", "秘密代码", "ひみつの暗号", "गुप्त कोड", "الرموز السرية", "গোপন সংকেত", "Kode rahasia", "خفیہ کوڈ"),
 "cit.boite.forensique": T("L'enquête numérique", "The digital investigation", "La investigación digital", "Die digitale Spurensuche", "L'indagine digitale", "A investigação digital", "Цифровое расследование", "数字侦查", "デジタル捜査", "डिजिटल जाँच", "التحقيق الرقمي", "ডিজিটাল তদন্ত", "Penyelidikan digital", "ڈیجیٹل تفتیش"),
 "cit.boite.social": T("L'ingénierie sociale", "Social engineering", "La ingeniería social", "Social Engineering", "L'ingegneria sociale", "A engenharia social", "Социальная инженерия", "社会工程", "ソーシャルエンジニアリング", "सोशल इंजीनियरिंग", "الهندسة الاجتماعية", "সোশ্যাল ইঞ্জিনিয়ারিং", "Rekayasa sosial", "سوشل انجینئرنگ"),
}


def tout():
    """Toutes les clés : ce fichier et les morceaux textes_citadelle_*.py."""
    import importlib.util
    d = dict(K)
    for f in sorted(Path(__file__).parent.glob("textes_citadelle_*.py")):
        spec = importlib.util.spec_from_file_location(f.stem, f)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        for k, v in m.K.items():
            assert k not in d, k
            d[k] = v
    return d


def ajouter(racine):
    racine = Path(racine)
    n = 0
    K2 = tout()
    for k, v in K2.items():
        assert set(v) == set(L), k
    for dossier in ("pc/tg/langues", "app/src/main/assets/langues"):
        for code in L:
            f = racine / dossier / f"{code}.json"
            data = json.loads(f.read_text(encoding="utf-8"))
            for k, v in K2.items():
                if dossier.startswith("pc") and (k.startswith("hista.") or k.startswith("cit.tel.")):
                    continue                     # les variantes du téléphone : seulement sur Android
                if data.get(k) != v[code]:
                    data[k] = v[code]
                    n += 1
            f.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return n, len(K2)


if __name__ == "__main__":
    print("clés écrites : %d (sur %d)" % ajouter(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[3]))
