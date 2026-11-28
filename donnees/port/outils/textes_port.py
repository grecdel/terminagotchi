"""Les textes du Port (le monde des réseaux, phase 5) dans les 14 langues : chapitre, leçons PC et Android (« hista » :
la variante du téléphone), fiches notions, pages du phare, commandes du jeu (`port …`), messager de la vue déployée.

    python3 donnees/port/outils/textes_port.py      ajoute ou met à jour les clés dans pc/tg/langues et
                                                    app/src/main/assets/langues (indentation 1, comme les fichiers)
Les autres morceaux sont dans textes_port_2.py, textes_port_3.py… (même format), lus par ce fichier.
"""
import json
import sys
from pathlib import Path

L = ["fr", "en", "es", "de", "it", "pt", "ru", "zh", "ja", "hi", "ar", "bn", "id", "ur"]


def T(*v):
    assert len(v) == 14, v[0]
    return dict(zip(L, v))


K = {
 # ------------------------------------------------------------------ le monde, son ouverture, ses récompenses
 "hist.port.titre": T("Le Port des messagers", "The Messenger Harbour", "El Puerto de los mensajeros", "Der Hafen der Boten", "Il Porto dei messaggeri", "O Porto dos mensageiros", "Порт гонцов", "信使港", "メッセンジャーの港", "संदेशवाहकों का बंदरगाह", "ميناء الرسل", "বার্তাবাহকদের বন্দর", "Pelabuhan Para Pengantar", "قاصدوں کی بندرگاہ"),
 "hist.port.court": T("Le Port", "The Harbour", "El Puerto", "Der Hafen", "Il Porto", "O Porto", "Порт", "港口", "港", "बंदरगाह", "الميناء", "বন্দর", "Pelabuhan", "بندرگاہ"),
 "hist.port.debut": T("⚓ Bienvenue au Port ! Ici, chaque biome du Terminaworld est une machine avec son adresse, et des petits messagers portent des paquets de l'une à l'autre. On va trouver notre adresse, lire l'annuaire, envoyer le facteur et allumer notre propre phare.", "⚓ Welcome to the Harbour! Here, every biome of the Terminaworld is a machine with its own address, and little messengers carry packets from one to another. We'll find our address, read the directory, send the postman and light our own lighthouse.", "⚓ ¡Bienvenido al Puerto! Aquí cada bioma del Terminaworld es una máquina con su dirección, y pequeños mensajeros llevan paquetes de una a otra. Vamos a encontrar nuestra dirección, leer el directorio, enviar al cartero y encender nuestro propio faro.", "⚓ Willkommen im Hafen! Hier ist jedes Biom der Terminaworld eine Maschine mit eigener Adresse, und kleine Boten tragen Pakete von einer zur anderen. Wir finden unsere Adresse, lesen das Verzeichnis, schicken den Briefträger los und zünden unseren eigenen Leuchtturm an.", "⚓ Benvenuto al Porto! Qui ogni bioma del Terminaworld è una macchina con il suo indirizzo, e piccoli messaggeri portano pacchetti dall'una all'altra. Troveremo il nostro indirizzo, leggeremo l'elenco, manderemo il postino e accenderemo il nostro faro.", "⚓ Bem-vindo ao Porto! Aqui, cada bioma do Terminaworld é uma máquina com o seu endereço, e pequenos mensageiros levam pacotes de uma para outra. Vamos descobrir o nosso endereço, ler a lista, mandar o carteiro e acender o nosso próprio farol.", "⚓ Добро пожаловать в Порт! Здесь каждый биом Terminaworld — машина со своим адресом, а маленькие гонцы носят пакеты от одной к другой. Мы найдём свой адрес, прочитаем справочник, отправим почтальона и зажжём свой маяк.", "⚓ 欢迎来到港口！在这里，Terminaworld 的每个生物群落都是一台有自己地址的机器，小信使们把数据包从一台送到另一台。我们要找到自己的地址、查看地址簿、派出邮差，再点亮我们自己的灯塔。", "⚓ 港へようこそ！ここでは Terminaworld の各バイオームが自分のアドレスを持つマシンで、小さなメッセンジャーがパケットを運んでいるよ。自分のアドレスを見つけ、電話帳を読み、郵便屋さんを送り出し、自分の灯台をともそう。", "⚓ बंदरगाह में स्वागत है! यहाँ Terminaworld का हर बायोम अपने पते वाली एक मशीन है, और छोटे संदेशवाहक पैकेट एक से दूसरी तक ले जाते हैं। हम अपना पता खोजेंगे, निर्देशिका पढ़ेंगे, डाकिया भेजेंगे और अपना प्रकाशस्तंभ जलाएँगे।", "⚓ مرحبًا في الميناء! هنا كل منطقة من Terminaworld آلة لها عنوانها، ورسل صغار يحملون الحزم من واحدة إلى أخرى. سنجد عنواننا، ونقرأ الدليل، ونرسل ساعي البريد، ونضيء منارتنا.", "⚓ বন্দরে স্বাগতম! এখানে Terminaworld-এর প্রতিটি বায়োম নিজের ঠিকানাওয়ালা একটা যন্ত্র, আর ছোট বার্তাবাহকেরা এক যন্ত্র থেকে আরেক যন্ত্রে প্যাকেট নিয়ে যায়। আমরা নিজের ঠিকানা খুঁজব, ঠিকানার বই পড়ব, ডাকপিয়ন পাঠাব আর নিজের বাতিঘর জ্বালাব।", "⚓ Selamat datang di Pelabuhan! Di sini setiap bioma Terminaworld adalah mesin dengan alamatnya sendiri, dan pengantar kecil membawa paket dari satu ke yang lain. Kita akan menemukan alamat kita, membaca buku alamat, mengirim tukang pos, dan menyalakan mercusuar kita sendiri.", "⚓ بندرگاہ میں خوش آمدید! یہاں Terminaworld کا ہر بایوم اپنے پتے والی ایک مشین ہے، اور ننھے قاصد پیکٹ ایک سے دوسری تک لے جاتے ہیں۔ ہم اپنا پتہ ڈھونڈیں گے، پتوں کی کتاب پڑھیں گے، ڈاکیا بھیجیں گے اور اپنا لائٹ ہاؤس جلائیں گے۔"),
 "hist.port.fin": T("Les phares brillent tous ! Tu sais où habite chaque machine, comment voyagent les messagers et comment reconnaître un vrai sceau. Tu es Capitaine du Port.", "All the lighthouses are shining! You know where each machine lives, how messengers travel and how to recognise a real seal. You are Harbour Captain.", "¡Todos los faros brillan! Sabes dónde vive cada máquina, cómo viajan los mensajeros y cómo reconocer un sello verdadero. Eres Capitán del Puerto.", "Alle Leuchttürme leuchten! Du weißt, wo jede Maschine wohnt, wie Boten reisen und wie man ein echtes Siegel erkennt. Du bist Hafenkapitän.", "Tutti i fari brillano! Sai dove abita ogni macchina, come viaggiano i messaggeri e come riconoscere un vero sigillo. Sei Capitano del Porto.", "Todos os faróis brilham! Sabes onde mora cada máquina, como viajam os mensageiros e como reconhecer um selo verdadeiro. És Capitão do Porto.", "Все маяки горят! Ты знаешь, где живёт каждая машина, как путешествуют гонцы и как узнать настоящую печать. Ты — Капитан порта.", "所有灯塔都亮了！你知道每台机器住在哪里、信使怎样旅行、怎样认出真正的封印。你是港口船长了。", "灯台がぜんぶ光っている！どのマシンがどこに住んでいるか、メッセンジャーがどう旅するか、本物の封印の見分け方もわかったね。きみは港の船長だ。", "सारे प्रकाशस्तंभ चमक रहे हैं! तुम जानते हो कि हर मशीन कहाँ रहती है, संदेशवाहक कैसे यात्रा करते हैं और असली मुहर कैसे पहचानें। तुम बंदरगाह के कप्तान हो।", "كل المنارات تضيء! تعرف أين تسكن كل آلة، وكيف يسافر الرسل، وكيف تميّز الختم الحقيقي. أنت قبطان الميناء.", "সব বাতিঘর জ্বলছে! তুমি জানো কোন যন্ত্র কোথায় থাকে, বার্তাবাহকেরা কীভাবে চলে আর আসল সিলমোহর কীভাবে চেনা যায়। তুমি এখন বন্দরের ক্যাপ্টেন।", "Semua mercusuar bersinar! Kamu tahu di mana setiap mesin tinggal, bagaimana pengantar bepergian, dan cara mengenali segel asli. Kamu Kapten Pelabuhan.", "سارے لائٹ ہاؤس روشن ہیں! تم جانتے ہو کہ ہر مشین کہاں رہتی ہے، قاصد کیسے سفر کرتے ہیں اور اصلی مہر کیسے پہچانتے ہیں۔ تم بندرگاہ کے کپتان ہو۔"),
 "hist.ecran.monde": T("{icone} Monde · {chapitre}", "{icone} World · {chapitre}", "{icone} Mundo · {chapitre}", "{icone} Welt · {chapitre}", "{icone} Mondo · {chapitre}", "{icone} Mundo · {chapitre}", "{icone} Мир · {chapitre}", "{icone} 世界 · {chapitre}", "{icone} ワールド · {chapitre}", "{icone} दुनिया · {chapitre}", "{icone} عالم · {chapitre}", "{icone} জগৎ · {chapitre}", "{icone} Dunia · {chapitre}", "{icone} دنیا · {chapitre}"),
 "hist.monde.log": T("🌍 Nouveau monde : {chapitre}", "🌍 New world: {chapitre}", "🌍 Nuevo mundo: {chapitre}", "🌍 Neue Welt: {chapitre}", "🌍 Nuovo mondo: {chapitre}", "🌍 Novo mundo: {chapitre}", "🌍 Новый мир: {chapitre}", "🌍 新世界：{chapitre}", "🌍 新しいワールド：{chapitre}", "🌍 नई दुनिया: {chapitre}", "🌍 عالم جديد: {chapitre}", "🌍 নতুন জগৎ: {chapitre}", "🌍 Dunia baru: {chapitre}", "🌍 نئی دنیا: {chapitre}"),
 "carte.piece.port": T("Port", "Harbour", "Puerto", "Hafen", "Porto", "Porto", "Порт", "港口", "港", "बंदरगाह", "الميناء", "বন্দর", "Pelabuhan", "بندرگاہ"),
 "qu.objet.phare_miniature": T("un phare miniature", "a tiny lighthouse", "un faro en miniatura", "ein Mini-Leuchtturm", "un faro in miniatura", "um farol em miniatura", "маленький маяк", "一座迷你灯塔", "ミニ灯台", "एक छोटा प्रकाशस्तंभ", "منارة صغيرة", "একটা ছোট্ট বাতিঘর", "mercusuar mini", "ایک ننھا لائٹ ہاؤس"),
 "qu.titre.capitaine_du_port": T("Capitaine du Port", "Harbour Captain", "Capitán del Puerto", "Hafenkapitän", "Capitano del Porto", "Capitão do Porto", "Капитан порта", "港口船长", "港の船長", "बंदरगाह का कप्तान", "قبطان الميناء", "বন্দরের ক্যাপ্টেন", "Kapten Pelabuhan", "بندرگاہ کا کپتان"),
 "port.ferme": T("{chapitre} : pas encore ouvert. Il faut d'abord finir : {manque}.", "{chapitre}: not open yet. First finish: {manque}.", "{chapitre}: todavía no está abierto. Primero termina: {manque}.", "{chapitre}: noch nicht offen. Beende zuerst: {manque}.", "{chapitre}: non ancora aperto. Prima finisci: {manque}.", "{chapitre}: ainda não está aberto. Primeiro termina: {manque}.", "{chapitre}: пока закрыто. Сначала закончи: {manque}.", "{chapitre}：还没有开放。先完成：{manque}。", "{chapitre}：まだ開いていないよ。先に終わらせよう：{manque}。", "{chapitre}: अभी खुला नहीं है। पहले पूरा करो: {manque}।", "{chapitre}: لم يُفتح بعد. أنهِ أولًا: {manque}.", "{chapitre}: এখনও খোলেনি। আগে শেষ করো: {manque}।", "{chapitre}: belum terbuka. Selesaikan dulu: {manque}.", "{chapitre}: ابھی نہیں کھلا۔ پہلے مکمل کرو: {manque}۔"),
 "port.ferme.court": T("s'ouvre après : {manque}", "opens after: {manque}", "se abre después de: {manque}", "öffnet nach: {manque}", "si apre dopo: {manque}", "abre depois de: {manque}", "откроется после: {manque}", "完成后开放：{manque}", "これの後に開く：{manque}", "इसके बाद खुलेगा: {manque}", "يُفتح بعد: {manque}", "এর পরে খুলবে: {manque}", "terbuka setelah: {manque}", "اس کے بعد کھلے گا: {manque}"),
 "port.ouvert.log": T("🌍 Un monde s'ouvre au Carrefour : le Port", "🌍 A world opens at the Crossroads: the Harbour", "🌍 Un mundo se abre en el Cruce: el Puerto", "🌍 Eine Welt öffnet sich an der Kreuzung: der Hafen", "🌍 Un mondo si apre al Crocevia: il Porto", "🌍 Um mundo abre-se na Encruzilhada: o Porto", "🌍 На Перекрёстке открылся мир: Порт", "🌍 十字路口开启了一个世界：港口", "🌍 交差点で新しいワールドが開いた：港", "🌍 चौराहे पर एक दुनिया खुली: बंदरगाह", "🌍 عالم يُفتح عند مفترق الطرق: الميناء", "🌍 চৌরাস্তায় একটা জগৎ খুলল: বন্দর", "🌍 Sebuah dunia terbuka di Persimpangan: Pelabuhan", "🌍 چوراہے پر ایک دنیا کھلی: بندرگاہ"),
 "port.ouvert.dit": T("Tu sais lire, chercher et brancher des tuyaux : le Port t'ouvre ses quais ! Quand tu veux : `cd ~/terrain_terminagotchi/port`.", "You can read, search and connect pipes: the Harbour opens its docks to you! Whenever you like: `cd ~/terrain_terminagotchi/port`.", "Sabes leer, buscar y conectar tuberías: ¡el Puerto te abre sus muelles! Cuando quieras: `cd ~/terrain_terminagotchi/port`.", "Du kannst lesen, suchen und Pipes verbinden: Der Hafen öffnet dir seine Kais! Wann du willst: `cd ~/terrain_terminagotchi/port`.", "Sai leggere, cercare e collegare tubi: il Porto ti apre le sue banchine! Quando vuoi: `cd ~/terrain_terminagotchi/port`.", "Sabes ler, procurar e ligar canos: o Porto abre-te os seus cais! Quando quiseres: `cd ~/terrain_terminagotchi/port`.", "Ты умеешь читать, искать и соединять трубы: Порт открывает тебе свои причалы! Когда захочешь: `cd ~/terrain_terminagotchi/port`.", "你会读、会找、会接管道了：港口向你打开码头！随时可以去：`cd ~/terrain_terminagotchi/port`。", "読んで、さがして、パイプをつなげるようになったね。港が波止場を開いてくれたよ！いつでもどうぞ：`cd ~/terrain_terminagotchi/port`。", "तुम पढ़ना, खोजना और पाइप जोड़ना जानते हो: बंदरगाह तुम्हारे लिए अपने घाट खोलता है! जब चाहो: `cd ~/terrain_terminagotchi/port`।", "أنت تعرف القراءة والبحث ووصل الأنابيب: الميناء يفتح لك أرصفته! متى شئت: `cd ~/terrain_terminagotchi/port`.", "তুমি পড়তে, খুঁজতে আর পাইপ জুড়তে জানো: বন্দর তোমার জন্য ঘাট খুলে দিল! যখন খুশি: `cd ~/terrain_terminagotchi/port`।", "Kamu bisa membaca, mencari, dan menyambung pipa: Pelabuhan membuka dermaganya untukmu! Kapan saja: `cd ~/terrain_terminagotchi/port`.", "تم پڑھنا، ڈھونڈنا اور پائپ جوڑنا جانتے ہو: بندرگاہ تمہارے لیے اپنی گودیاں کھولتی ہے! جب چاہو: `cd ~/terrain_terminagotchi/port`۔"),
}


def tout():
    """Toutes les clés : ce fichier et les morceaux textes_port_*.py."""
    import importlib.util
    d = dict(K)
    for f in sorted(Path(__file__).parent.glob("textes_port_*.py")):
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
                if dossier.startswith("pc") and k.startswith("hista."):
                    continue                     # les variantes du téléphone : seulement sur Android
                if data.get(k) != v[code]:
                    data[k] = v[code]
                    n += 1
            f.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return n, len(K2)


if __name__ == "__main__":
    print("clés écrites : %d (sur %d)" % ajouter(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[3]))
