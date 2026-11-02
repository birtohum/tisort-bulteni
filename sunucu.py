"""Tasarım atölyesi arayüzü: python sunucu.py  ->  http://127.0.0.1:8792

Ana sayfa basit arayüz (kolay.html); bütün araçlar /uzman sayfasında (atolye.html).
Yalnızca bu bilgisayardan erişilir (127.0.0.1). Üretilen dosyalar cikti/atolye/ altına yazılır.
"""
import html
import base64
import json
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import atolye
import bulten
import kolay
import metin
import satis
import tasarim
from api import harcanan

KOK = Path(__file__).parent
CIKTI = KOK / "cikti" / "atolye"
TARZ = KOK / "veri" / "tarz.json"
TARZ_ORNEK = KOK / "veri" / "tarz_ornekleri"
PORT = 8792
GORSEL_UST = 8 * 1024 * 1024
VARSAYILAN_STIL = "bold retro illustration with clean thick outlines and a touch of humor, limited 3-4 color palette"
bulten_durum = {"calisiyor": False, "son": None, "hata": None}


def _ad(on_ek):
    return f"{on_ek}_{time.strftime('%Y%m%d_%H%M%S')}_{int(time.time() * 1000) % 1000:03d}"


def _gorsel(b64):
    veri = base64.b64decode(b64.split(",", 1)[-1])
    if len(veri) > GORSEL_UST:
        raise ValueError("görsel 8 MB'tan büyük")
    return veri


def _tarz():
    if not TARZ.exists():
        return None, []
    ornekler = [p.read_bytes() for p in sorted(TARZ_ORNEK.glob("*"))][:2]
    tarz = json.loads(TARZ.read_text(encoding="utf-8"))
    return (tarz, ornekler) if tarz.get("stil_istemi") else (None, [])


def _kart(sonuc, ad, tur):
    return sonuc | {"ad": ad, "tur": tur, "orijinal": f"{ad}.orijinal.webp"}


def islem(yol, g):
    CIKTI.mkdir(parents=True, exist_ok=True)
    if yol == "/api/durum":
        tarz, _ = _tarz()
        return {"tarz": tarz, "harcanan": round(harcanan(), 3), "bulten": bulten_durum,
                "satis": json.loads(bulten.SATIS.read_text(encoding="utf-8")) if bulten.SATIS.exists() else None}
    if yol == "/api/tarz":
        gorseller = [_gorsel(x) for x in g["gorseller"][:6]]
        if not gorseller:
            raise ValueError("en az bir örnek tasarım gerekli")
        tarz = atolye.tarz_cikar(gorseller)
        if not tarz.get("stil_istemi"):
            raise ValueError(tarz.get("hata") or "bu görsellerden tarz çıkarılamadı; tişört tasarımı yükleyin")
        TARZ_ORNEK.mkdir(parents=True, exist_ok=True)
        for p in TARZ_ORNEK.glob("*"):
            p.unlink()
        for i, b in enumerate(gorseller):
            (TARZ_ORNEK / f"ornek_{i}.img").write_bytes(b)
        TARZ.write_text(json.dumps(tarz, ensure_ascii=False, indent=1), encoding="utf-8")
        return {"tarz": tarz}
    if yol == "/api/olay":
        kolay.olay_yaz(g)
        return {}
    if yol == "/api/k/anla":
        fikir = g.get("fikir", "").strip()
        if not fikir:
            raise ValueError("fikir boş")
        foto = _gorsel(g["foto"]) if g.get("foto") else None
        return kolay.is_baslat("anla", ["Fikrinizi okuyorum", "Yazı önerileri hazırlanıyor"], lambda is_: kolay.anla(fikir, foto))
    if yol == "/api/k/ciz":
        tarz, ornekler = _tarz()
        foto = _gorsel(g["foto"]) if g.get("foto") else None
        return kolay.is_baslat("ciz", ["Hazırlanıyor", "Yapay zekâ çiziyor", "Arka plan temizleniyor"],
                               lambda is_: kolay.ciz(is_, CIKTI, g["konu_en"], g.get("slogan", ""), g.get("fikir", ""),
                                                    foto, tarz, ornekler))
    if yol == "/api/k/koyu":
        kaynak = (CIKTI / Path(g["orijinal"]).name).read_bytes()

        def koyu(is_):
            ad = _ad("koyu")
            is_["adim"] = 1
            s = atolye.koyu_versiyon(kaynak, CIKTI / ad)
            return s | {"ad": ad, "orijinal": f"{ad}.orijinal.webp"}
        return kolay.is_baslat("koyu", ["Hazırlanıyor", "Koyu tişört için yeniden boyanıyor"], koyu)
    if yol == "/api/k/metin":
        fikir = {"baslik": g["konu_en"], "slogan": g.get("slogan", ""), "prompt": g["konu_en"],
                 "neden_simdi": "", "hedef_alici": ""}
        return kolay.is_baslat("metin", ["Başlık ve etiketler yazılıyor", "Kurallara göre denetleniyor"],
                               lambda is_: metin.yaz(fikir))
    if yol == "/api/slogan":
        return {"adaylar": atolye.sloganlar(g["konu"])}
    if yol == "/api/tasarim":
        tarz, ornekler = _tarz()
        ad = _ad("tasarim")
        if tarz:
            s = atolye.tarzla_uret(g["konu"], tarz, ornekler, CIKTI / ad, g.get("slogan", ""))
        else:
            istem = (f"T-shirt print design about: {g['konu']}. Style: {VARSAYILAN_STIL}. "
                     + (f'Text in the design exactly: "{g["slogan"]}". ' if g.get("slogan") else "No text. ")
                     + "Isolated on plain pure white background, no t-shirt, no mockup.")
            s = tasarim.uret(istem, CIKTI / ad, etiket="tasarim")
        return {"kartlar": [_kart(s, ad, "tasarim")]}
    if yol == "/api/koyu":
        ad = _ad("koyu")
        s = atolye.koyu_versiyon((CIKTI / g["orijinal"]).read_bytes(), CIKTI / ad)
        return {"kartlar": [_kart(s, ad, "koyu")]}
    if yol == "/api/mockup":
        dosya = atolye.mockup((CIKTI / g["orijinal"]).read_bytes(), CIKTI / _ad("m"), g.get("tisort") or "heather grey crew-neck t-shirt")
        return {"mockup": dosya}
    if yol == "/api/evcil":
        tarz, _ = _tarz()
        ad = _ad("evcil")
        s = atolye.evcil_portre(_gorsel(g["foto"]), CIKTI / ad, tarz["stil_istemi"] if tarz else VARSAYILAN_STIL, g.get("yazi", ""))
        return {"kartlar": [_kart(s, ad, "evcil")]}
    if yol == "/api/aile":
        tarz, _ = _tarz()
        klasor_ad = _ad("aile")
        uyeler = [u.strip() for u in g.get("uyeler", "Papa,Mama,Kid,Baby").split(",") if u.strip()][:6]
        s = atolye.aile_seti(g["konsept"], CIKTI / klasor_ad, tuple(uyeler), tarz["stil_istemi"] if tarz else VARSAYILAN_STIL)
        return {"kartlar": [_kart(v, f"{klasor_ad}/aile_{k.lower()}", "aile") for k, v in s.items()]}
    if yol == "/api/seri":
        tarz, _ = _tarz()
        klasor_ad = _ad("seri")
        ogeler = [o.strip() for o in g["ogeler"].split("\n") if o.strip()][:8]
        s = atolye.seri(g["tema"], ogeler, CIKTI / klasor_ad, tarz["stil_istemi"] if tarz else VARSAYILAN_STIL)
        return {"kartlar": [_kart(v, f"{klasor_ad}/{v['baski'][:-4]}", "seri") for v in s.values()]}
    if yol == "/api/satis":
        yol_csv = KOK / "veri" / "son_satis.csv"
        yol_csv.parent.mkdir(exist_ok=True)
        yol_csv.write_bytes(base64.b64decode(g["csv"].split(",", 1)[-1]))
        satirlar, harita, atilan = satis.oku(yol_csv)
        yol_csv.unlink()  # kişisel sütunlar içeren ham dosya saklanmaz
        r = satis.rapor(satirlar)
        bulten.SATIS.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        return {"rapor": r, "atilan_sutunlar": atilan}
    if yol == "/api/bulten":
        if bulten_durum["calisiyor"]:
            return {"bulten": bulten_durum}

        def calis():
            bulten_durum.update(calisiyor=True, hata=None)
            try:
                k, _ = bulten.calistir(8, 6)
                bulten_durum["son"] = f"/bulten/{k.name}/bulten.html"
            except Exception as h:
                bulten_durum["hata"] = str(h)[:300]
            bulten_durum["calisiyor"] = False
        threading.Thread(target=calis, daemon=True).start()
        return {"bulten": bulten_durum | {"calisiyor": True}}
    raise KeyError(yol)


def kullanim_sayfasi():
    o = kolay.kullanim_ozeti()
    e = html.escape
    tablo = lambda satirlar: "".join(f"<tr><td>{e(str(a))}</td><td>{e(str(b))}</td></tr>" for a, b in satirlar)         or "<tr><td colspan=2>henüz yok</td></tr>"
    return f"""<!doctype html><html lang="tr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kullanım özeti</title><style>body{{font:17px/1.5 system-ui,sans-serif;max-width:680px;margin:24px auto;padding:0 16px;
background:#fbf8f2;color:#1f1d1a}}td{{padding:6px 10px;border-bottom:1px solid #e4dfd4}}td:last-child{{text-align:right}}
table{{border-collapse:collapse;width:100%;margin-bottom:24px}}h2{{font-size:18px;margin-top:28px}}p{{color:#5d5950}}</style>
<h1>Kullanım özeti</h1>
<p>Yalnızca bu bilgisayarda tutulur, hiçbir yere gönderilmez. {o['olay_sayisi']} kayıt, ilk kayıt {o['ilk'] or '—'}.
Az kullanıcıyla bu sayılar kesin sonuç değildir; hangi adımda takılındığını görmek içindir.</p>
<h2>Adım adım</h2><table>{tablo(o['huni'])}</table>
<h2>Fikir nereden geldi</h2><table>{tablo(o['fikir_kaynagi'].items())}</table>
<h2>Yazı seçimi</h2><table>{tablo([('Öneri seçti', o['yazi_secimi']['oneri']), ('Kendisi yazdı', o['yazi_secimi']['kendi']), ('Yazısız', o['yazi_secimi']['yok'])])}</table>
<h2>Bekleme</h2><table>{tablo([('Çizim süresi (ortanca, sn)', o['ciz_ortanca_sn'] or '—'), ('Beklerken sayfadan ayrıldı', o['beklerken_ayrildi']), ('Hata', o['hata'])])}</table>
<h2>En çok dokunulan öneriler</h2><table>{tablo(o['oneriler'])}</table>
<h2>Seçilen tişört renkleri</h2><table>{tablo(o['renkler'])}</table>
<p><a href="/">← Atölyeye dön</a></p></html>"""


class Isleyici(BaseHTTPRequestHandler):
    def _gonder(self, kod, govde, tur="application/json; charset=utf-8"):
        veri = govde if isinstance(govde, bytes) else json.dumps(govde, ensure_ascii=False).encode()
        self.send_response(kod)
        self.send_header("Content-Type", tur)
        self.send_header("Content-Length", str(len(veri)))
        self.end_headers()
        self.wfile.write(veri)

    def _dosya(self, kok, goreli):
        p = (kok / goreli).resolve()
        if not str(p).startswith(str(kok.resolve())) or not p.is_file():
            return self._gonder(404, {"hata": "bulunamadı"})
        tur = {".webp": "image/webp", ".png": "image/png", ".html": "text/html; charset=utf-8"}.get(p.suffix, "application/octet-stream")
        self._gonder(200, p.read_bytes(), tur)

    def do_GET(self):
        yol = self.path.split("?")[0]
        if yol in ("/", "/index.html"):
            return self._gonder(200, (KOK / "kolay.html").read_bytes(), "text/html; charset=utf-8")
        if yol == "/uzman":
            return self._gonder(200, (KOK / "atolye.html").read_bytes(), "text/html; charset=utf-8")
        if yol == "/kullanim":
            return self._gonder(200, kullanim_sayfasi().encode(), "text/html; charset=utf-8")
        if yol.startswith("/api/is/"):
            try:
                return self._gonder(200, kolay.durum(yol[len("/api/is/"):]))
            except KeyError:
                return self._gonder(404, {"hata": "iş bulunamadı (sunucu yeniden başlamış olabilir)"})
        if yol == "/api/baslangic":
            tarz, _ = _tarz()
            return self._gonder(200, {"oneriler": kolay.oneriler(), "gecmis": kolay.gecmis(),
                                      "renk": kolay.tercih_rengi(), "ipuclari": kolay.IPUCLARI,
                                      "tarz": bool(tarz), "harcanan": round(harcanan(), 2)})
        if yol.startswith("/dosya/"):
            return self._dosya(CIKTI, yol[len("/dosya/"):])
        if yol.startswith("/bulten/"):
            return self._dosya(KOK / "cikti", yol[len("/bulten/"):])
        if yol == "/api/durum":
            return self._gonder(200, islem(yol, {}))
        self._gonder(404, {"hata": "bulunamadı"})

    def do_POST(self):
        try:
            uzunluk = int(self.headers.get("Content-Length", 0))
            if uzunluk > 60 * 1024 * 1024:
                return self._gonder(413, {"hata": "istek çok büyük"})
            g = json.loads(self.rfile.read(uzunluk) or b"{}")
            self._gonder(200, islem(self.path, g))
        except KeyError as h:
            self._gonder(400, {"hata": f"eksik alan ya da bilinmeyen işlem: {h}"})
        except ValueError as h:
            self._gonder(400, {"hata": str(h)})
        except SystemExit as h:
            self._gonder(503, {"hata": str(h)})
        except Exception as h:
            traceback.print_exc()
            self._gonder(500, {"hata": str(h)[:300]})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Isleyici).serve_forever()
