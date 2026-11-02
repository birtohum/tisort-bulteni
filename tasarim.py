"""Fikirden baskıya hazır tasarım dosyası.

- muse-image-1.0 ile üretir (webp, ~1344x1792).
- Beyaz arka planı kenarlardan taşma doldurma ile şeffaf yapar (tasarımın içindeki beyazlar korunur).
- 2x büyütür (LANCZOS). Bu gerçek bir "süper çözünürlük" değildir; düz renkli çizimlerde kabul edilebilir,
  ince doku ve fotoğrafik görsellerde bulanıklaşır. Baskı servisinin önerdiği DPI'ı kontrol edin.
- Meta'nın koyduğu köken bilgisi (XMP) PNG'ye aynen taşınır: Meta Kabul Edilebilir Kullanım Politikası
  köken sinyallerinin silinmesini yasaklar.
"""
import io
from pathlib import Path

from PIL import Image, ImageDraw, PngImagePlugin

from api import gorsel_uret

ZEMIN_ESIK = 40  # zemin rengine uzaklık; arka plan sayılacak yakınlık


def seffaf_yap(im, zemin=(255, 255, 255)):
    """Kenarlardan başlayıp zemin rengine (açık tişört tasarımında beyaz, koyuda siyah) yakın bölgeyi siler."""
    im = im.convert("RGBA")
    w, h = im.size
    isaret = im.convert("RGB").copy()
    hedef = (255, 0, 255)
    for nokta in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]:
        piksel = isaret.getpixel(nokta)
        if piksel != hedef and max(abs(a - b) for a, b in zip(piksel, zemin)) <= ZEMIN_ESIK:
            ImageDraw.floodfill(isaret, nokta, hedef, thresh=ZEMIN_ESIK)
    piksel_i, piksel_a = isaret.load(), im.load()
    seffaf = 0
    for y in range(h):
        for x in range(w):
            if piksel_i[x, y] == hedef:
                piksel_a[x, y] = (255, 255, 255, 0)
                seffaf += 1
    return im, seffaf / (w * h)


def uret(istem, hedef_yol: Path, referanslar=(), zemin=(255, 255, 255), etiket="gorsel"):
    """Görseli üretir, Meta'nın verdiği dosyayı dokunmadan saklar ve baskı dosyasını hazırlar."""
    ham, _ = gorsel_uret(istem, etiket=etiket, referanslar=referanslar)
    hedef_yol.parent.mkdir(parents=True, exist_ok=True)
    hedef_yol.with_suffix(".orijinal.webp").write_bytes(ham)
    return hazirla(ham, hedef_yol, zemin)


def hazirla(ham, hedef_yol: Path, zemin=(255, 255, 255)):
    """Baskı dosyası (PNG, şeffaf, tasarım sınırına kırpılmış, 2x) + önizleme (webp) yazar."""
    im = Image.open(io.BytesIO(ham))
    xmp = im.info.get("xmp")
    seffaf, oran = seffaf_yap(im, zemin)
    kutu = seffaf.getchannel("A").getbbox()
    if kutu:  # boş kenarları at, 20 px pay bırak
        kutu = (max(0, kutu[0] - 20), max(0, kutu[1] - 20), min(seffaf.width, kutu[2] + 20), min(seffaf.height, kutu[3] + 20))
        seffaf = seffaf.crop(kutu)
    buyuk = seffaf.resize((seffaf.width * 2, seffaf.height * 2), Image.LANCZOS)
    bilgi = PngImagePlugin.PngInfo()
    if xmp:
        bilgi.add_itxt("XML:com.adobe.xmp", xmp.decode("utf-8", "replace") if isinstance(xmp, bytes) else xmp)
    buyuk.save(hedef_yol.with_suffix(".png"), pnginfo=bilgi)
    on = seffaf.copy()
    on.thumbnail((520, 700))
    on.save(hedef_yol.with_suffix(".onizleme.webp"), quality=85)
    return {"baski": hedef_yol.with_suffix(".png").name, "onizleme": hedef_yol.with_suffix(".onizleme.webp").name,
            "boyut": f"{buyuk.width}x{buyuk.height}", "seffaf_oran": round(oran, 2), "xmp_korundu": bool(xmp),
            "kaybolan_oran": kaybolan_oran(on, zemin)}


def kaybolan_oran(im, tisort_rengi):
    """Tasarımın tişört rengine çok yakın (baskıda görünmeyecek) kısmının oranı. Koyu tişörtte koyu yazı gibi
    sorunları yakalar; 0,20 üstü "kontrol edin" uyarısı verir. Tasarımın içindeki küçük gölgeler de sayıldığı için kaba bir ölçüdür."""
    ton = sum(tisort_rengi) / 3
    pikseller = [p for p in im.convert("RGBA").getdata() if p[3] > 200]
    if not pikseller:
        return 0.0
    yakin = sum(1 for r, g, b, _ in pikseller if abs(0.299 * r + 0.587 * g + 0.114 * b - ton) < 50)
    return round(yakin / len(pikseller), 2)
