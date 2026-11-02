"""Tasarımcının elle kullanacağı araçlar: slogan adayları, koyu tişört versiyonu, mockup, tarz çıkarma,
tarzla üretim, evcil hayvan portresi, aile seti ve seri koleksiyon.

Hepsi muse-image-1.0'ın referans görsel yeteneğine dayanır. Çıktılar taslaktır; yayın kararı tasarımcınındır.
"""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from api import gorsel_uret, resim, sor
from fikir import RISKLI, _sor_json
from tasarim import uret

SIYAH = (0, 0, 0)

SLOGAN_ISTEM = """You write t-shirt slogans for an Etsy shop (US buyers).
Design idea: {fikir}
Write 10 ORIGINAL slogan candidates (max 6 words each): wordplay, puns, relatable humor. No brand/franchise/celebrity
references, no existing famous slogans or memes, no song lyrics. Then act as a tough Etsy buyer and score each 1-10 for
"would I laugh and buy it as a gift". Be honest; most should score below 7.
Return JSON only: {{"adaylar": [{{"slogan": "...", "puan": 0, "neden": "Türkçe kısa"}}]}}"""

TARZ_ISTEM = """These images are t-shirt designs by one designer. Describe their shared visual STYLE precisely so an
image model can reproduce it on new subjects: line work, shading, color palette (hex if possible), typography style,
composition, level of detail, humor/tone, recurring motifs. Do not describe the specific subjects.
Return JSON only: {"ozet_tr": "Türkçe 1-2 cümle", "stil_istemi": "English, one paragraph, for an image model"}"""


def sloganlar(fikir_metni, n=3):
    adaylar = _sor_json(SLOGAN_ISTEM.format(fikir=fikir_metni), "slogan")["adaylar"]
    temiz = [a for a in adaylar if not re.search(RISKLI, a.get("slogan", ""), flags=re.I)
             and len(a.get("slogan", "").split()) <= 6]
    return sorted(temiz, key=lambda a: -a.get("puan", 0))[:n]


def koyu_versiyon(orijinal: bytes, hedef: Path):
    """Aynı tasarımın koyu tişört için yeniden renklendirilmiş hali (siyah zeminde üretilir, siyah silinir)."""
    istem = ("Recolor this exact t-shirt print design for a BLACK t-shirt: keep the same drawing, composition and exactly "
             "the same text and spelling; turn dark outlines and dark fills into light cream/white, keep the other "
             "colors vivid. Place it on a solid pure black (#000000) background, no shirt, no extra elements.")
    return uret(istem, hedef, referanslar=[orijinal], zemin=SIYAH, etiket="koyu")


def mockup(orijinal: bytes, hedef: Path, tisort="heather grey crew-neck t-shirt"):
    """Ürün görseli taslağı. Etsy (22 Eki 2026 bildirimine göre) çoğu üründe en az bir düzenlenmemiş gerçek
    fotoğraf istiyor: mockup ek görsel olarak kullanılmalı."""
    istem = (f"Realistic product photo: a plain {tisort} laid flat on a light wooden table, soft natural daylight, "
             "with this exact design printed on the chest at realistic size. Do not change the design or its text.")
    ham, _ = gorsel_uret(istem, etiket="mockup", referanslar=[orijinal])
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.with_suffix(".mockup.webp").write_bytes(ham)
    return hedef.with_suffix(".mockup.webp").name


def tarz_cikar(gorseller: list[bytes]):
    """Tasarımcının örnek tasarımlarından tarz tarifi (Spark görsel okuma)."""
    icerik = [{"type": "text", "text": TARZ_ISTEM}] + [resim(g, "webp" if g[8:12] == b"WEBP" else "png") for g in gorseller[:6]]
    return _sor_json(icerik, "tarz")


def tarzla_uret(konu, tarz, ornekler: list[bytes], hedef: Path, slogan=""):
    """Yeni konuyu tasarımcının tarzında çizer: tarz tarifi + en fazla 2 örnek tasarım referans olarak."""
    istem = (f"Create a NEW t-shirt print design about: {konu}. Match the visual style of the reference designs exactly "
             f"(line work, palette, typography, tone) but do not copy their subjects. Style: {tarz['stil_istemi']} "
             + (f'Text in the design exactly: "{slogan}". ' if slogan else "No text. ")
             + "Isolated on plain pure white background, no t-shirt, no mockup.")
    return uret(istem, hedef, referanslar=ornekler[:2], etiket="tarz")


def evcil_portre(foto: bytes, hedef: Path, tarz_istemi="bold retro illustration, clean thick outlines, limited palette",
                 yazi=""):
    """Müşterinin evcil hayvan fotoğrafından kişiye özel tasarım.
    DİKKAT: ücretsiz kredide içerik Meta'nın ürün geliştirmesinde kullanılabilir; gerçek müşteri fotoğrafı göndermeden
    önce ücretli kullanıma geçin ya da müşteriden izin alın."""
    istem = ("Turn the pet in this photo into a t-shirt print illustration. Keep the pet recognizable: same breed, "
             f"fur colors, markings and face shape. Style: {tarz_istemi}. "
             + (f'Add the text exactly: "{yazi}". ' if yazi else "No text. ")
             + "Only the pet (head and shoulders), isolated on plain pure white background, no t-shirt.")
    return uret(istem, hedef, referanslar=[foto], etiket="evcil")


def aile_seti(konsept, hedef_klasor: Path, uyeler=("Dad", "Mom", "Kid", "Baby"), stil=""):
    """Aynı konseptin aile üyelerine göre tutarlı versiyonları: önce ilki çizilir, diğerleri onu referans alır."""
    ilk_istem = (f"T-shirt print design for a matching family set. Concept: {konsept}. This one is for: {uyeler[0]}. "
                 f"Include the word \"{uyeler[0].upper()}\" clearly in the design. {stil} "
                 "Isolated on plain pure white background, no t-shirt.")
    sonuc = {uyeler[0]: uret(ilk_istem, hedef_klasor / f"aile_{uyeler[0].lower()}", etiket="aile")}
    ilk = (hedef_klasor / f"aile_{uyeler[0].lower()}.orijinal.webp").read_bytes()

    def digeri(uye):
        istem = (f"Make the matching version of this exact design for: {uye}. Same style, palette, layout and typography; "
                 f"adapt the character to fit '{uye}' and replace the word \"{uyeler[0].upper()}\" with \"{uye.upper()}\". "
                 "Isolated on plain pure white background, no t-shirt.")
        return uye, uret(istem, hedef_klasor / f"aile_{uye.lower()}", referanslar=[ilk], etiket="aile")

    with ThreadPoolExecutor(3) as h:
        sonuc |= dict(h.map(digeri, uyeler[1:]))
    return sonuc


def seri(tema, ogeler, hedef_klasor: Path, stil=""):
    """Bir tema etrafında tutarlı seri (ör. 'meslek sahibi kediler': nurse, teacher, chef...)."""
    ilk_istem = (f"T-shirt print design, part of a collection '{tema}'. This design: {ogeler[0]}. {stil} "
                 "Isolated on plain pure white background, no t-shirt.")
    sonuc = {ogeler[0]: uret(ilk_istem, hedef_klasor / "seri_01", etiket="seri")}
    ilk = (hedef_klasor / "seri_01.orijinal.webp").read_bytes()

    def digeri(i_o):
        i, o = i_o
        istem = (f"Next design in the same collection '{tema}': {o}. Keep exactly the same art style, palette, framing "
                 "and typography as the reference so the set looks consistent. Isolated on plain pure white background.")
        return o, uret(istem, hedef_klasor / f"seri_{i + 2:02d}", referanslar=[ilk], etiket="seri")

    with ThreadPoolExecutor(3) as h:
        sonuc |= dict(h.map(digeri, enumerate(ogeler[1:])))
    return sonuc
