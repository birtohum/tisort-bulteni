"""Tema ilgisi sinyalleri.

1. Mevsimsellik: kalıcı tişört temalarının İngilizce Wikipedia aylık görüntülenmesi (resmî Wikimedia API).
   Önümüzdeki iki ayın GEÇEN YILKİ değeri / geçen yılın aylık ortalaması = mevsimsel yükseliş.
   Son 3 ay / geçen yılın aynı 3 ayı = ivme.
   Bu, Etsy'deki talebin doğrudan ölçüsü değildir; bir konuya genel ilginin vekilidir.
2. Gündem: Google Trends günlük RSS (ABD). Çoğu kişi, takım, dizi adıdır; yalnızca risk filtresinden
   geçenler fikir kaynağı olur (fikir.py).
"""
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

UA = {"User-Agent": "tisort-fikir/0.1 (kisisel proje; https://github.com)"}
ONBELLEK = Path(__file__).parent / "veri" / "wiki_onbellek.json"

# tema -> Wikipedia makalesi. Marka/karakter içermeyen, tişörtte sık görülen kalıcı nişler.
TEMALAR = {
    "cat": "Cat", "dog": "Dog", "coffee": "Coffee", "camping": "Camping", "fishing": "Fishing",
    "hiking": "Hiking", "gardening": "Gardening", "yoga": "Yoga", "reading books": "Reading",
    "nurse": "Nursing", "teacher": "Teacher", "dinosaur": "Dinosaur", "frog": "Frog", "capybara": "Capybara",
    "axolotl": "Axolotl", "mushroom": "Mushroom", "astronaut / space": "Astronaut", "moon": "Moon",
    "skiing": "Skiing", "snowboarding": "Snowboarding", "pickleball": "Pickleball", "chess": "Chess",
    "guitar": "Guitar", "vinyl records": "Phonograph_record", "taco": "Taco", "pizza": "Pizza",
    "bigfoot": "Bigfoot", "ufo / alien": "Unidentified_flying_object", "camper van": "Campervan",
    "motorcycle": "Motorcycle", "honey bee": "Honey_bee", "sloth": "Sloth", "owl": "Owl", "raccoon": "Raccoon",
    "highland cow": "Highland_cattle", "goose": "Goose", "crochet": "Crochet", "knitting": "Knitting",
    "running": "Running", "weightlifting": "Weightlifting", "birdwatching": "Birdwatching",
    "astrology": "Astrology", "tarot": "Tarot", "witch": "Witchcraft", "gingerbread": "Gingerbread",
    "snowman": "Snowman", "christmas tree": "Christmas_tree", "reindeer": "Reindeer", "turkey (bird)": "Wild_turkey",
    "pumpkin": "Pumpkin", "skeleton": "Human_skeleton", "ghost": "Ghost", "hot cocoa": "Hot_chocolate",
    "beer": "Beer", "wine": "Wine", "bbq": "Barbecue", "baseball": "Baseball", "basketball": "Basketball",
    "american football": "American_football", "soccer": "Association_football", "video games": "Video_game",
    "anime style": "Anime", "retro 80s": "1980s_in_music", "national parks": "National_parks_of_the_United_States",
}


def _al(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read()


def aylik(makale, bas="20240101", son=None):
    son = son or date.today().replace(day=1).strftime("%Y%m%d")
    onb = json.loads(ONBELLEK.read_text(encoding="utf-8")) if ONBELLEK.exists() else {}
    anahtar = f"{makale}:{bas}:{son}"
    if anahtar not in onb:
        url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/"
               f"{urllib.parse.quote(makale, safe='')}/monthly/{bas}/{son}")
        onb[anahtar] = {x["timestamp"][:6]: x["views"] for x in json.loads(_al(url))["items"]}
        ONBELLEK.parent.mkdir(exist_ok=True)
        ONBELLEK.write_text(json.dumps(onb), encoding="utf-8")
        time.sleep(0.2)
    return onb[anahtar]


def _ay(y, m):
    y, m = y + (m - 1) // 12, (m - 1) % 12 + 1
    return f"{y}{m:02d}"


def mevsimsellik(bugun=None):
    """Her tema için yükseliş (önümüzdeki 2 ay, geçen yıla göre) ve ivme."""
    bugun = bugun or date.today()
    y, m = bugun.year, bugun.month
    sonuc = []
    for tema, makale in TEMALAR.items():
        try:
            v = aylik(makale)
        except Exception as e:
            sonuc.append({"tema": tema, "hata": str(e)[:80]})
            continue
        gecen_yil = [v.get(_ay(y - 1, a)) for a in range(m, m + 12)]  # geçen yıl bu aydan başlayan 12 ay
        gecen_yil = [x for x in gecen_yil if x]
        if len(gecen_yil) < 10:
            continue
        ort = sum(gecen_yil) / len(gecen_yil)
        hedef = [v.get(_ay(y - 1, a), 0) for a in (m, m + 1)]  # alıcının alışveriş yapacağı iki ay, geçen yıl
        son3 = [v.get(_ay(y, a), 0) for a in (m - 3, m - 2, m - 1)]
        gecen3 = [v.get(_ay(y - 1, a), 0) for a in (m - 3, m - 2, m - 1)]
        sonuc.append({"tema": tema, "makale": makale, "aylik_ort": round(ort),
                      "yukselis": round(sum(hedef) / 2 / ort, 2),
                      "ivme": round(sum(son3) / max(1, sum(gecen3)), 2)})
    return sorted(sonuc, key=lambda x: -x.get("yukselis", 0))


def gundem(ulke="US"):
    """Google Trends günlük RSS: [(başlık, yaklaşık trafik, haber başlıkları)]."""
    xml = _al(f"https://trends.google.com/trending/rss?geo={ulke}").decode("utf-8", "replace")
    ogeler = []
    for oge in re.findall(r"<item>(.*?)</item>", xml, flags=re.S):
        baslik = re.search(r"<title>(.*?)</title>", oge, flags=re.S).group(1).strip()
        trafik = (re.search(r"<ht:approx_traffic>(.*?)</ht:approx_traffic>", oge) or [None, ""])[1]
        haberler = re.findall(r"<ht:news_item_title>(.*?)</ht:news_item_title>", oge, flags=re.S)
        ogeler.append({"baslik": baslik, "trafik": trafik, "haberler": [re.sub(r"<!\[CDATA\[|\]\]>", "", h)[:120] for h in haberler[:2]]})
    return ogeler


if __name__ == "__main__":
    for s in mevsimsellik()[:20]:
        print(s)
    print()
    for g in gundem()[:10]:
        print(g["baslik"], g["trafik"], g["haberler"][:1])
