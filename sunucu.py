"""Tasarım atölyesi arayüzü: python sunucu.py  ->  http://127.0.0.1:8792

Yalnızca bu bilgisayardan erişilir (127.0.0.1). Üretilen dosyalar cikti/atolye/ altına yazılır.
"""
import base64
import json
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import atolye
import bulten
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
    return json.loads(TARZ.read_text(encoding="utf-8")), ornekler


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
        TARZ_ORNEK.mkdir(parents=True, exist_ok=True)
        for p in TARZ_ORNEK.glob("*"):
            p.unlink()
        for i, b in enumerate(gorseller):
            (TARZ_ORNEK / f"ornek_{i}.img").write_bytes(b)
        TARZ.write_text(json.dumps(tarz, ensure_ascii=False, indent=1), encoding="utf-8")
        return {"tarz": tarz}
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
            return self._gonder(200, (KOK / "atolye.html").read_bytes(), "text/html; charset=utf-8")
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
