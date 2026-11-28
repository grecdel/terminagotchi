"""Les textes du thème « Apprendre en jouant » (idées cochées du 3 novembre) dans les 14 langues : pas de série à perdre,
bac à sable, tableau des rares, maîtrise, révisions, commande du jour, énigmes, mini-jeux, course, limite de temps
douce, dictionnaire illustré, sentier des marmottes, examen et diplôme.

    python3 donnees/apprendre/outils/textes_apprendre.py     ajoute ou met à jour les clés dans pc/tg/langues et
                                                              app/src/main/assets/langues (indentation 1)
Les autres morceaux sont dans textes_apprendre_*.py (même format), lus par ce fichier.
"""
import json
import sys
from pathlib import Path

L = ["fr", "en", "es", "de", "it", "pt", "ru", "zh", "ja", "hi", "ar", "bn", "id", "ur"]


def T(*v):
    assert len(v) == 14, v[0]
    return dict(zip(L, v))


K = {
 # ------------------------------------------------------------------ 50. pas de série à perdre
 "core.defi.rate.dit": T("Le défi s'est envolé… on rejouera !", "The challenge flew away… we'll play again!", "El reto se ha ido volando… ¡volveremos a jugar!", "Die Aufgabe ist davongeflogen… wir spielen nochmal!", "La sfida è volata via… rigiocheremo!", "O desafio voou… vamos jogar outra vez!", "Задание улетело… сыграем ещё!", "挑战飞走啦……我们再玩！", "チャレンジは とんでいっちゃった……また あそぼう！", "चुनौती उड़ गई… फिर खेलेंगे!", "طار التحدي… سنلعب مرة أخرى!", "চ্যালেঞ্জটা উড়ে গেল… আবার খেলব!", "Tantangannya terbang… kita main lagi nanti!", "چیلنج اُڑ گیا… پھر کھیلیں گے!"),
 "core.defi.rate.log": T("⚡ Le défi « `{cmd}` » s'est envolé", "⚡ The “`{cmd}`” challenge flew away", "⚡ El reto «`{cmd}`» se fue volando", "⚡ Die Aufgabe „`{cmd}`“ ist davongeflogen", "⚡ La sfida «`{cmd}`» è volata via", "⚡ O desafio «`{cmd}`» voou", "⚡ Задание «`{cmd}`» улетело", "⚡ 挑战「`{cmd}`」飞走了", "⚡ チャレンジ「`{cmd}`」は とんでいった", "⚡ चुनौती «`{cmd}`» उड़ गई", "⚡ طار تحدي «`{cmd}`»", "⚡ চ্যালেঞ্জ «`{cmd}`» উড়ে গেল", "⚡ Tantangan «`{cmd}`» terbang", "⚡ چیلنج «`{cmd}`» اُڑ گیا"),
 "sat.serie.medaille": T("🏅 {n} jours bien nourrie au total ! Une médaille, et +{xp} XP.", "🏅 {n} well-fed days in total! A medal, and +{xp} XP.", "🏅 ¡{n} días bien alimentada en total! Una medalla y +{xp} XP.", "🏅 Insgesamt {n} gut gefütterte Tage! Eine Medaille und +{xp} EP.", "🏅 {n} giorni ben nutrita in tutto! Una medaglia e +{xp} XP.", "🏅 {n} dias bem alimentada no total! Uma medalha e +{xp} XP.", "🏅 Всего {n} сытых дней! Медаль и +{xp} XP.", "🏅 一共吃饱了 {n} 天！一枚奖牌，还有 +{xp} XP。", "🏅 しっかり食べた日が ぜんぶで {n} 日！メダルと +{xp} XP。", "🏅 कुल {n} दिन अच्छे से खाया! एक पदक, और +{xp} XP।", "🏅 {n} أيام من الشبع في المجموع! ميدالية، و+{xp} XP.", "🏅 মোট {n} দিন ভালো করে খাওয়া! একটি পদক, আর +{xp} XP।", "🏅 Total {n} hari kenyang! Sebuah medali, dan +{xp} XP.", "🏅 کُل {n} دن اچھی طرح کھایا! ایک تمغہ، اور +{xp} XP۔"),
 "sat.ecran.serie": T("Jours bien nourrie : {jours} au total. {medailles} (jamais perdus)", "Well-fed days: {jours} in total. {medailles} (never lost)", "Días bien alimentada: {jours} en total. {medailles} (nunca se pierden)", "Gut gefütterte Tage: insgesamt {jours}. {medailles} (gehen nie verloren)", "Giorni ben nutrita: {jours} in tutto. {medailles} (mai persi)", "Dias bem alimentada: {jours} no total. {medailles} (nunca se perdem)", "Сытых дней: всего {jours}. {medailles} (никогда не теряются)", "吃饱的日子：一共 {jours} 天。{medailles}（永远不会丢）", "しっかり食べた日：ぜんぶで {jours} 日。{medailles}（ぜったい なくならない）", "अच्छे से खाए दिन: कुल {jours}। {medailles} (कभी नहीं खोते)", "أيام الشبع: {jours} في المجموع. {medailles} (لا تضيع أبدًا)", "ভালো করে খাওয়ানো দিন: মোট {jours}। {medailles} (কখনো হারায় না)", "Hari kenyang: total {jours}. {medailles} (tidak pernah hilang)", "اچھی طرح کھلائے دن: کُل {jours}۔ {medailles} (کبھی ضائع نہیں ہوتے)"),
 "recomp.entrainement.serie_parfaite": T("Cinq médailles d'or à la salle d'entraînement", "Five gold medals in the training room", "Cinco medallas de oro en la sala de entrenamiento", "Fünf Goldmedaillen im Trainingsraum", "Cinque medaglie d'oro nella sala d'allenamento", "Cinco medalhas de ouro na sala de treino", "Пять золотых медалей в зале тренировок", "训练室里的五枚金牌", "トレーニング室で 金メダル 5こ", "अभ्यास कक्ष में पाँच स्वर्ण पदक", "خمس ميداليات ذهبية في قاعة التدريب", "অনুশীলন কক্ষে পাঁচটি সোনার পদক", "Lima medali emas di ruang latihan", "مشق کے کمرے میں پانچ سونے کے تمغے"),
}


def tout():
    """Toutes les clés : ce fichier et les morceaux textes_apprendre_*.py."""
    import importlib.util
    d = dict(K)
    for f in sorted(Path(__file__).parent.glob("textes_apprendre_*.py")):
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
                if data.get(k) != v[code]:
                    data[k] = v[code]
                    n += 1
            f.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return n, len(K2)


if __name__ == "__main__":
    print("clés écrites : %d (sur %d)" % ajouter(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[3]))
