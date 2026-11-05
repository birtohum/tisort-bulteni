"""Tişört Atölyesi herkese açık demo: yalnız basit akış (fikir → yazı → çizim → renk → Etsy metni), sıkı sınırlarla.
Caddy önde HTTPS'i yapar, /tisort/* isteklerini 127.0.0.1:8793'e iletir.

Demoda kapalı olanlar: uzman araçları, kullanım özeti, satış dosyası, aile/seri, evcil hayvan fotoğrafı,
tarz örnekleri ve başkalarının tasarımları. Eniştenin ürün bilgisi ve tasarımları bu sunucuda yok.

Sınırlar (ortam değişkeniyle):
  TISORT_IP_CIZIM   bir IP'nin günlük çizim sayısı (her çizim 2 tasarım)  (3)
  TISORT_GUN_CIZIM  tüm ziyaretçiler, günlük çizim                       (40)
  TISORT_IP_METIN   bir IP'nin günlük fikir/metin isteği                   (20)
  TISORT_TAVAN      toplam model harcaması, $ (api.py)                     (5)
Üretilen görseller 24 saat sonra silinir.
"""
import hashlib
import json
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer

os.environ.setdefault("TISORT_TAVAN", "5")

import sunucu  # noqa: E402
from api import harcanan, TAVAN  # noqa: E402

PORT = int(os.environ.get("TISORT_PORT", "8793"))
IP_CIZIM = int(os.environ.get("TISORT_IP_CIZIM", "3"))
GUN_CIZIM = int(os.environ.get("TISORT_GUN_CIZIM", "40"))
IP_METIN = int(os.environ.get("TISORT_IP_METIN", "20"))
TR = timezone(timedelta(hours=3))
_kilit = threading.Lock()
_sayac = {"gun": None, "cizim": 0, "ip_cizim": {}, "ip_metin": {}}
ACIK_POST = {"/api/k/anla": "metin", "/api/k/metin": "metin", "/api/k/ciz": "cizim", "/api/k/koyu": "cizim"}

DEMO_NOT = """<div style="background:#1f1d1a;color:#fbf8f2;font:15px/1.5 system-ui,sans-serif;padding:10px 16px;text-align:center">
Herkese açık demo. Bu atölyeyi Etsy'de tişört satan eniştem için yaptım; burada kişi başı günde {ic} çizim hakkı var.
Fotoğraf yükleme ve uzman araçları kapalı. Çizimler 24 saat sonra silinir. <a href="https://github.com/birtohum/tisort-bulteni" style="color:#ffd28a">Kaynak kod</a></div>"""


def _ip(isleyici):
    ip = (isleyici.headers.get("X-Forwarded-For") or isleyici.client_address[0]).split(",")[0].strip()
    return hashlib.sha256(("tisort-demo:" + ip).encode()).hexdigest()[:16]


def _hak(ozet, tur):
    with _kilit:
        bugun = datetime.now(TR).date().isoformat()
        if _sayac["gun"] != bugun:
            _sayac.update({"gun": bugun, "cizim": 0, "ip_cizim": {}, "ip_metin": {}})
        if tur == "cizim":
            if _sayac["ip_cizim"].get(ozet, 0) >= IP_CIZIM:
                return f"Bugünlük çizim hakkınız doldu ({IP_CIZIM}). Yarın yeniden deneyebilirsiniz."
            if _sayac["cizim"] >= GUN_CIZIM:
                return "Demo bugünkü çizim sınırına ulaştı. Yarın yeniden deneyebilirsiniz."
            _sayac["ip_cizim"][ozet] = _sayac["ip_cizim"].get(ozet, 0) + 1
            _sayac["cizim"] += 1
        else:
            if _sayac["ip_metin"].get(ozet, 0) >= IP_METIN:
                return "Bugünlük deneme hakkınız doldu. Yarın yeniden deneyebilirsiniz."
            _sayac["ip_metin"][ozet] = _sayac["ip_metin"].get(ozet, 0) + 1
        return None


def sayfa():
    h = (sunucu.KOK / "kolay.html").read_text(encoding="utf-8")
    # /tisort/ altında çalışsın diye mutlak yollar göreli yapılır
    h = h.replace('"/api/', '"api/').replace('"/dosya/', '"dosya/')
    h = re.sub(r'<span><a href="/uzman">.*?</span>', "", h, count=1, flags=re.S)
    h = h.replace("<body>", "<body>" + DEMO_NOT.format(ic=IP_CIZIM), 1)
    # fotoğraf düğmesi demoda yok
    h = h.replace("</style>", "#foto-dugme,#harcama{display:none!important}</style>", 1)
    h = h.replace("Önce bir fikir yazın ya da fotoğraf ekleyin.", "Önce bir fikir yazın.")
    return h.encode("utf-8")


def temizle():
    while True:
        sinir = time.time() - 24 * 3600
        for p in sunucu.CIKTI.glob("*"):
            try:
                if p.is_file() and p.stat().st_mtime < sinir:
                    p.unlink()
            except OSError:
                pass
        time.sleep(1800)


class CanliIsleyici(sunucu.Isleyici):
    def do_GET(self):
        yol = self.path.split("?")[0]
        if yol in ("/", "/index.html"):
            return self._gonder(200, sayfa(), "text/html; charset=utf-8")
        if yol == "/api/baslangic":
            return self._gonder(200, {"oneriler": sunucu.kolay.oneriler(), "gecmis": [], "renk": "Beyaz",
                                      "ipuclari": sunucu.kolay.IPUCLARI, "tarz": False, "harcanan": 0})
        if yol.startswith("/api/is/") or yol.startswith("/dosya/"):
            return super().do_GET()
        return self._gonder(404, {"hata": "bulunamadı"})

    def do_POST(self):
        yol = self.path.split("?")[0]
        if yol == "/api/olay":  # demoda kullanım kaydı tutulmaz
            self.rfile.read(min(int(self.headers.get("Content-Length", 0) or 0), 20000))
            return self._gonder(200, {})
        tur = ACIK_POST.get(yol)
        if not tur:
            return self._gonder(404, {"hata": "Bu işlem demoda kapalı."})
        uzunluk = int(self.headers.get("Content-Length", 0) or 0)
        if uzunluk > 20000:
            return self._gonder(413, {"hata": "İstek çok büyük. (Demoda fotoğraf yüklenemez.)"})
        govde = self.rfile.read(uzunluk)
        try:
            g = json.loads(govde or b"{}")
        except ValueError:
            return self._gonder(400, {"hata": "istek okunamadı"})
        g.pop("foto", None)
        if yol == "/api/k/anla" and len(str(g.get("fikir", ""))) > 400:
            return self._gonder(400, {"hata": "Fikri biraz daha kısa yazın."})
        if harcanan() >= TAVAN:
            return self._gonder(503, {"hata": "Demonun harcama sınırı doldu. Kod açık; kendi anahtarınızla çalıştırabilirsiniz."})
        neden = _hak(_ip(self), tur)
        if neden:
            return self._gonder(429, {"hata": neden})
        try:
            if yol == "/api/k/ciz":
                sonuc = sunucu.kolay.is_baslat("ciz", ["Hazırlanıyor", "Yapay zekâ çiziyor", "Arka plan temizleniyor"],
                                               lambda is_: sunucu.kolay.ciz(is_, sunucu.CIKTI, str(g["konu_en"])[:600], str(g.get("slogan", ""))[:80],
                                                                           str(g.get("fikir", ""))[:400], None, None, ()))
                return self._gonder(200, sonuc)
            return self._gonder(200, sunucu.islem(yol, g))
        except KeyError as h:
            return self._gonder(400, {"hata": f"eksik alan: {h}"})
        except ValueError as h:
            return self._gonder(400, {"hata": str(h)})
        except FileNotFoundError:
            return self._gonder(404, {"hata": "Tasarım bulunamadı (24 saatten eski olabilir)."})
        except SystemExit as h:
            return self._gonder(503, {"hata": str(h)})


if __name__ == "__main__":
    sunucu.CIKTI.mkdir(parents=True, exist_ok=True)
    threading.Thread(target=temizle, daemon=True).start()
    print(f"tişört demo: 127.0.0.1:{PORT} (IP çizim {IP_CIZIM}, gün {GUN_CIZIM}, tavan {TAVAN} $)")
    ThreadingHTTPServer(("127.0.0.1", PORT), CanliIsleyici).serve_forever()
