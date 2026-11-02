"""Etsy satış raporu: Shop Manager > Settings > Options > Download Data'dan indirilen "Order Items" CSV'si.

API anahtarı gerekmez. Alıcı adı, adres gibi kişisel sütunlar okunur okunmaz atılır; rapor tamamen yerelde
hesaplanır, hiçbir satış verisi modele gönderilmez.

Etsy'nin CSV sütun adları zamanla değişebildiği için sütunlar esnek eşleştirilir (ör. "Item Name", "Sale Date",
"Quantity", "Item Total" / "Price", "Variations").

Kullanım: python satis.py dosya.csv
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from sinyal import TEMALAR

SUTUN = {
    "urun": ["item name", "title", "listing title"],
    "tarih": ["sale date", "order date", "date paid"],
    "adet": ["quantity"],
    "tutar": ["item total", "price"],
    "secenek": ["variations", "variation"],
    "ilan": ["listing id"],
}
KISISEL = re.compile(r"buyer|ship|name$|address|city|state|zip|country|email|phone|user", re.I)


def _bul(basliklar, adaylar):
    kucuk = {b.lower().strip(): b for b in basliklar}
    return next((kucuk[a] for a in adaylar if a in kucuk), None)


def _tarih(s):
    for bicim in ("%m/%d/%y", "%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s.strip(), bicim).date()
        except ValueError:
            pass
    return None


def _sayi(s):
    s = re.sub(r"[^\d.,-]", "", s or "")
    if "," in s and "." in s:
        s = s.replace(",", "")
    return float(s.replace(",", ".") or 0)


def oku(yol):
    with open(yol, encoding="utf-8-sig", newline="") as f:
        okuyucu = csv.DictReader(f)
        b = okuyucu.fieldnames or []
        harita = {k: _bul(b, v) for k, v in SUTUN.items()}
        if not harita["urun"] or not harita["tarih"]:
            raise ValueError(f"ürün adı / tarih sütunu bulunamadı; sütunlar: {b}")
        satirlar = []
        for r in okuyucu:
            satirlar.append({k: r.get(s, "") for k, s in harita.items() if s})  # kişisel sütunlar hiç alınmaz
    atilan = [x for x in b if KISISEL.search(x) and x not in harita.values()]
    return satirlar, harita, atilan


def rapor(satirlar, bugun=None):
    bugun = bugun or date.today()
    urun = defaultdict(lambda: {"adet": 0, "tutar": 0.0, "son30": 0, "onceki30": 0})
    tema, renk, beden = Counter(), Counter(), Counter()
    for r in satirlar:
        t = _tarih(r.get("tarih", "")) or bugun
        adet = int(_sayi(r.get("adet", "1")) or 1)
        u = urun[r["urun"].strip()]
        u["adet"] += adet
        u["tutar"] += _sayi(r.get("tutar", "0"))
        if t > bugun - timedelta(30):
            u["son30"] += adet
        elif t > bugun - timedelta(60):
            u["onceki30"] += adet
        ad = r["urun"].lower()
        for k in TEMALAR:  # "ufo / alien": seçeneklerden biri; "christmas tree": tüm kelimeler geçmeli
            secenekler = [re.sub(r"\(.*?\)", "", s).split() for s in k.split("/")]
            if any(s and all(re.search(rf"\b{re.escape(w)}s?\b", ad) for w in s) for s in secenekler):
                tema[k] += adet
        sec = r.get("secenek", "")
        if m := re.search(r"(?:colou?r|renk)\s*[:=]\s*([^,;]+)", sec, re.I):
            renk[m.group(1).strip().lower()] += adet
        if m := re.search(r"(?:size|beden)\s*[:=]\s*([^,;]+)", sec, re.I):
            beden[m.group(1).strip().upper()] += adet
    for v in urun.values():
        v["tutar"] = round(v["tutar"], 2)
    sirali = sorted(urun.items(), key=lambda x: -x[1]["adet"])
    yukselen = sorted([(k, v) for k, v in urun.items() if v["son30"] > v["onceki30"]],
                      key=lambda x: -(x[1]["son30"] - x[1]["onceki30"]))
    return {"toplam_adet": sum(v["adet"] for v in urun.values()), "toplam_tutar": round(sum(v["tutar"] for v in urun.values()), 2),
            "en_cok": [{"urun": k, **v} for k, v in sirali[:10]],
            "yukselen": [{"urun": k, **v} for k, v in yukselen[:5]],
            "tema": tema.most_common(10), "renk": renk.most_common(6), "beden": beden.most_common(8)}


if __name__ == "__main__":
    s, h, atilan = oku(sys.argv[1])
    print("eşlenen sütunlar:", h)
    print("okunmadan atılan kişisel sütunlar:", atilan)
    r = rapor(s)
    print(json.dumps(r, ensure_ascii=False, indent=1)[:3000])
    Path(sys.argv[1]).with_suffix(".rapor.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
