"""Basit arayüzün arka yüzü: arka planda çalışan işler (ilerleme adımlarıyla), Türkçe fikri anlama,
fikir önerileri, tasarım geçmişi ve yerel kullanım kaydı.

Kullanım kaydı (kayitlar/kullanim.jsonl) yalnızca bu bilgisayarda tutulur, hiçbir yere gönderilmez; hangi adımda
takılındığını görmek için /kullanim sayfası özetler. Kullanıcı az olduğu için buradan çıkan sayılar kesin sonuç
değildir; arayüzde yaptığımız tek "veriye göre değişme" kişiseldir (en çok seçilen tişört rengi varsayılan olur,
en çok dokunulan fikirler öne çıkar, bekleme süresi tahmini geçmiş sürelerin ortancasıdır).
"""
import json
import re
import statistics
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import takvim
from api import gorsel_uret, resim
from fikir import RISKLI, _sor_json
from tasarim import hazirla

KOK = Path(__file__).parent
KAYIT = KOK / "kayitlar"
SURELER = KAYIT / "sureler.jsonl"
GECMIS = KAYIT / "tasarimlar.jsonl"
KULLANIM = KAYIT / "kullanim.jsonl"
VARSAYILAN_SURE = {"anla": 15, "ciz": 50, "koyu": 50, "metin": 25}
_kilit = threading.Lock()
isler = {}

ANLA_ISTEM = """A t-shirt designer who sells on Etsy (US buyers) describes a design idea, usually in Turkish. The text
may be short, informal or misspelled. Idea: "{fikir}"

Return JSON only:
{{"konu_en": "clear English brief for an image model: subject, action, mood, composition; max 40 words; keep the
designer's idea, add nothing branded",
 "anlasilan_tr": "one short, plain Turkish sentence saying what you will draw, so the designer can confirm",
 "sloganlar": [{{"slogan": "ORIGINAL English slogan, max 6 words, fits the idea, funny or warm",
                 "anlam_tr": "short Turkish meaning"}}],
 "marka": false}}
Give exactly 3 slogans. No brand, franchise, character, team or celebrity references, no famous existing slogans,
memes or lyrics. "marka" is true only if the idea itself names a brand, franchise character, team or celebrity."""

STIL = "bold retro illustration with clean thick outlines and a touch of humor, limited 3-4 color palette"

# Takvimdeki günlerin Türkçe adı ve tek dokunuşluk fikir metni; olmayanlar (indirim günleri gibi) öneri olmaz.
GUN_FIKIR = {
    "Halloween": ("🎃", "Cadılar Bayramı", "Cadılar Bayramı için sevimli, komik bir kabak"),
    "Thanksgiving": ("🦃", "Şükran Günü", "Şükran Günü için yemekten kaçmaya çalışan komik bir hindi"),
    "Christmas": ("🎄", "Noel", "Noel için kahve içen neşeli bir kardan adam"),
    "New Year": ("🎆", "Yılbaşı", "Yılbaşı için havai fişekler ve neşeli bir yazı"),
    "Valentine's Day": ("❤️", "Sevgililer Günü", "Sevgililer Günü için birbirine sarılan iki kedi"),
    "St. Patrick's Day": ("☘️", "St. Patrick Günü", "St. Patrick Günü için yeşil yonca tutan şirin bir köpek"),
    "Easter": ("🐰", "Paskalya", "Paskalya için yumurta taşıyan sevimli bir tavşan"),
    "Earth Day": ("🌍", "Dünya Günü", "Dünya Günü için ağaç diken gülümseyen bir dünya"),
    "Mother's Day (US)": ("💐", "Anneler Günü", "Anneler Günü için çiçekli, sıcak bir 'en iyi anne' tasarımı"),
    "Father's Day (US)": ("🎣", "Babalar Günü", "Babalar Günü için balık tutan komik bir baba"),
    "Independence Day (US)": ("🎇", "4 Temmuz", "Amerikan Bağımsızlık Günü için retro havai fişek ve kartal"),
    "Back to School": ("🍎", "Okula Dönüş", "Öğretmenler için elma ve kitaplı neşeli bir tasarım"),
}
HER_ZAMAN = [
    ("☕", "Kahve seven kedi", "Kocaman bir fincandan kahve içen uykulu bir kedi"),
    ("🎣", "Balıkçı dede", "Gölde balık tutan mutlu bir dede, gün batımı"),
    ("🌻", "Bahçıvan nine", "Bahçesinde çiçek yetiştiren neşeli bir nine"),
    ("🧘", "Yoga yapan tembel hayvan", "Gün doğarken yoga yapan tembel hayvan"),
    ("🏕️", "Kamp ateşi", "Kamp ateşinde marshmallow kızartan bir ayı"),
    ("🐶", "Köpek sevenler", "Kocaman gülümseyen, dili dışarıda mutlu bir köpek"),
]

IPUCLARI = [
    "Başlığın ilk kelimeleri en önemlisi: alıcının arama kutusuna yazacağı sözcükle başlayın.",
    "Etsy her ilana 13 etiket izin verir; hepsini kullanmak aramada daha çok yerde çıkmanızı sağlar.",
    "Marka, çizgi film karakteri ya da ünlü adı kullanmayın: ilan kaldırılabilir, mağaza kapanabilir.",
    "Yapay zekâ ile hazırlanan tasarımlarda ilanda bunu belirtmek gerekiyor. Etsy yazısını hazırlarken biz ekliyoruz.",
    "Koyu tişörtte koyu çizgiler kaybolur. Tasarımı siyah tişörtte deneyin; uyarı çıkarsa koyu sürümünü hazırlayın.",
    "Etsy çoğu üründe en az bir gerçek ürün fotoğrafı istiyor; çizilmiş tişört resmi ek görsel olabilir.",
    "Aynı fikri birkaç kez çizdirmek ucuzdur; en iyisini seçmek, ilkine razı olmaktan iyidir.",
    "Kısa, okunaklı yazılar uzaktan da okunur. Altı kelimeden kısa bir slogan tişörtte daha iyi durur.",
]


# ---------------------------------------------------------------- arka plan işleri

def _sure_tahmini(tur):
    if SURELER.exists():
        son = [json.loads(s)["sn"] for s in SURELER.read_text(encoding="utf-8").splitlines() if s and f'"{tur}"' in s][-10:]
        if son:
            return round(statistics.median(son))
    return VARSAYILAN_SURE[tur]


def is_baslat(tur, adimlar, calis):
    """calis(is_) arka planda çalışır; is_['adim'] ve is_['ara'] (ara sonuç) güncellenebilir."""
    is_ = {"id": uuid.uuid4().hex[:12], "tur": tur, "adimlar": adimlar, "adim": 0, "basla": time.time(),
           "tahmini_sn": _sure_tahmini(tur), "bitti": False, "sonuc": None, "hata": None, "ara": []}
    isler[is_["id"]] = is_

    def sar():
        try:
            is_["sonuc"] = calis(is_)
            sn = round(time.time() - is_["basla"], 1)
            with _kilit:
                KAYIT.mkdir(exist_ok=True)
                with open(SURELER, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"tur": tur, "sn": sn, "t": int(time.time())}) + "\n")
        except SystemExit as h:
            is_["hata"] = "Harcama sınırına ulaşıldı. " + str(h)
        except Exception as h:
            is_["hata"] = str(h)[:300]
        is_["adim"] = len(adimlar)
        is_["bitti"] = True

    threading.Thread(target=sar, daemon=True).start()
    return durum(is_["id"])


def durum(is_id):
    is_ = isler[is_id]
    return {k: is_[k] for k in ("id", "tur", "adimlar", "adim", "tahmini_sn", "bitti", "sonuc", "hata", "ara")} | {
        "gecen_sn": round(time.time() - is_["basla"], 1)}


# ---------------------------------------------------------------- işler

FOTO_EK = """
A photo of the designer's (or customer's) pet is attached. In konu_en describe the animal precisely (species, likely
breed, fur colors, markings, expression) so it stays recognizable; in anlasilan_tr name the animal plainly
(e.g. "turuncu tekir bir kedi"); make the slogans fit this animal."""


def anla(fikir, foto: bytes | None = None):
    """Türkçe fikir (ve varsa evcil hayvan fotoğrafı) -> İngilizce çizim tarifi, ne anlaşıldığı ve 3 slogan önerisi."""
    fikir = fikir.strip()[:500]
    istem = ANLA_ISTEM.format(fikir=fikir.replace('"', "'"))
    if foto:
        tur = "webp" if foto[8:12] == b"WEBP" else "png" if foto[:4] == b"\x89PNG" else "jpeg"
        istem = [{"type": "text", "text": istem + FOTO_EK}, resim(foto, tur)]
    j = _sor_json(istem, "anla")
    sloganlar = [s for s in j.get("sloganlar", []) if s.get("slogan") and len(s["slogan"].split()) <= 8
                 and not re.search(RISKLI, s["slogan"], flags=re.I)][:3]
    marka = bool(j.get("marka")) or bool(re.search(RISKLI, fikir + " " + j.get("konu_en", ""), flags=re.I))
    return {"fikir": fikir, "konu_en": j.get("konu_en", fikir), "anlasilan_tr": j.get("anlasilan_tr", fikir),
            "sloganlar": sloganlar, "marka": marka}


def _istem(konu_en, slogan, tarz, foto):
    stil = tarz["stil_istemi"] if tarz else STIL
    yazi = f'Text in the design exactly: "{slogan}". ' if slogan else "No text. "
    if foto:
        return ("Turn the pet in this photo into a t-shirt print illustration. Keep the pet recognizable: same breed, "
                f"fur colors, markings and face shape. Idea: {konu_en}. Style: {stil}. {yazi}"
                "Only the pet (head and shoulders), isolated on plain pure white background, no t-shirt.")
    return (f"T-shirt print design about: {konu_en}. Style: {stil}. {yazi}"
            "Isolated on plain pure white background, no t-shirt, no mockup.")


def ciz(is_, cikti: Path, konu_en, slogan="", fikir="", foto=None, tarz=None, ornekler=(), kac=2):
    """`kac` farklı tasarımı aynı anda çizer; biten her tasarım hemen is_['ara']'ya eklenir."""
    referanslar = [foto] if foto else list(ornekler[:2])
    istem = _istem(konu_en, slogan, tarz, foto)
    if tarz and not foto:
        istem = istem.replace("T-shirt print design", "NEW t-shirt print design matching the reference designs' "
                              "style exactly (do not copy their subjects)", 1)
    damga = time.strftime("%Y%m%d_%H%M%S")
    is_["adim"] = 1

    def bir(i):
        ad = f"kolay_{damga}_{is_['id'][:4]}_{i}"
        ham, _ = gorsel_uret(istem + ("" if i == 0 else " Use a different composition and color palette than usual."),
                             etiket="kolay", referanslar=referanslar)
        is_["adim"] = max(is_["adim"], 2)
        (cikti / f"{ad}.orijinal.webp").write_bytes(ham)
        s = hazirla(ham, cikti / ad) | {"ad": ad, "orijinal": f"{ad}.orijinal.webp", "sira": i}
        kayit = {"ad": ad, "t": int(time.time()), "fikir": fikir, "konu_en": konu_en, "slogan": slogan,
                 "foto": bool(foto), "onizleme": s["onizleme"], "baski": s["baski"], "orijinal": s["orijinal"]}
        with _kilit:
            KAYIT.mkdir(exist_ok=True)
            with open(GECMIS, "a", encoding="utf-8") as f:
                f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
        is_["ara"].append(s)
        return s

    with ThreadPoolExecutor(kac) as h:
        gelecekler = [h.submit(bir, i) for i in range(kac)]
        sonuclar, hatalar = [], []
        for g in gelecekler:
            try:
                sonuclar.append(g.result())
            except Exception as e:
                hatalar.append(str(e)[:200])
    if not sonuclar:
        raise RuntimeError(hatalar[0] if hatalar else "tasarım çıkmadı")
    is_["adim"] = 3
    return {"kartlar": sorted(sonuclar, key=lambda s: s["sira"]), "eksik": len(hatalar)}


# ---------------------------------------------------------------- öneriler, geçmiş, kullanım

def _olaylar():
    if not KULLANIM.exists():
        return []
    return [json.loads(s) for s in KULLANIM.read_text(encoding="utf-8").splitlines() if s]


def olay_yaz(o):
    o = {k: v for k, v in o.items() if isinstance(v, (str, int, float, bool)) and len(str(v)) < 200}
    o["t"] = int(time.time())
    with _kilit:
        KAYIT.mkdir(exist_ok=True)
        with open(KULLANIM, "a", encoding="utf-8") as f:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")


def oneriler(bugun=None):
    """Tek dokunuşluk fikirler: yaklaşan özel günler (önce) + her zaman satan konular.
    Kullanıcının daha önce dokunduğu öneriler aynı grup içinde öne alınır."""
    tik = {}
    for o in _olaylar():
        if o.get("ad") == "oneri":
            tik[o.get("baslik")] = tik.get(o.get("baslik"), 0) + 1
    gunler = []
    for g in takvim.yaklasanlar(bugun, hafta=12):
        if g["ad"] in GUN_FIKIR and g["durum"] != "geç kalındı":
            emoji, ad, metin = GUN_FIKIR[g["ad"]]
            gunler.append({"emoji": emoji, "baslik": ad, "fikir": metin, "gun_kaldi": g["gun_kaldi"],
                           "durum": g["durum"], "en_gec": g["en_gec_liste"]})
    hepsi = [{"emoji": e, "baslik": b, "fikir": f} for e, b, f in HER_ZAMAN]
    hepsi.sort(key=lambda x: -tik.get(x["baslik"], 0))
    return gunler[:3] + hepsi[:6 - min(3, len(gunler))]


def gecmis(n=12):
    if not GECMIS.exists():
        return []
    begeni = {}
    for o in _olaylar():
        if o.get("ad") == "begen":
            begeni[o.get("tasarim")] = bool(o.get("deger"))
    satirlar = [json.loads(s) for s in GECMIS.read_text(encoding="utf-8").splitlines() if s]
    return [s | {"begeni": begeni.get(s["ad"], False)} for s in reversed(satirlar[-n:])]


def tercih_rengi():
    sayi = {}
    for o in _olaylar():
        if o.get("ad") == "renk":
            sayi[o.get("renk")] = sayi.get(o.get("renk"), 0) + 1
    return max(sayi, key=sayi.get) if sayi else None


def kullanim_ozeti():
    o = _olaylar()
    say = lambda ad: sum(1 for x in o if x.get("ad") == ad)
    ciz_sn = [x["sn"] for x in o if x.get("ad") == "ciz_bitti" and isinstance(x.get("sn"), (int, float))]
    oneri = {}
    for x in o:
        if x.get("ad") == "oneri":
            oneri[x.get("baslik")] = oneri.get(x.get("baslik"), 0) + 1
    renk = {}
    for x in o:
        if x.get("ad") == "renk":
            renk[x.get("renk")] = renk.get(x.get("renk"), 0) + 1
    return {
        "huni": [("Sayfa açıldı", say("acildi")), ("Fikir yazıldı / seçildi", say("devam")),
                 ("Yazı seçildi, çizim başladı", say("ciz_basla")), ("Çizim bitti", say("ciz_bitti")),
                 ("Bir tasarım seçildi", say("sec")), ("Baskı dosyası kaydedildi", say("indir")),
                 ("Etsy yazısı hazırlandı", say("metin"))],
        "beklerken_ayrildi": say("bekleme_gizlendi"),
        "hata": say("hata"),
        "fikir_kaynagi": {"Kendisi yazdı": sum(1 for x in o if x.get("ad") == "devam" and x.get("kaynak") == "yazi"),
                          "Öneriye dokundu": sum(1 for x in o if x.get("ad") == "devam" and x.get("kaynak") == "oneri"),
                          "Sesle söyledi": sum(1 for x in o if x.get("ad") == "devam" and x.get("kaynak") == "ses"),
                          "Fotoğraf yükledi": sum(1 for x in o if x.get("ad") == "devam" and x.get("kaynak") == "foto")},
        "yazi_secimi": {k: sum(1 for x in o if x.get("ad") == "ciz_basla" and x.get("yazi") == k)
                        for k in ("oneri", "kendi", "yok")},
        "ciz_ortanca_sn": round(statistics.median(ciz_sn)) if ciz_sn else None,
        "oneriler": sorted(oneri.items(), key=lambda kv: -kv[1]),
        "renkler": sorted(renk.items(), key=lambda kv: -kv[1]),
        "olay_sayisi": len(o),
        "ilk": date.fromtimestamp(o[0]["t"]).isoformat() if o else None,
    }
