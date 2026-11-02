"""Haftalık fikir bülteni: takvim + mevsimsellik + süzülmüş gündem -> fikirler -> taslak tasarım + Etsy metni.

Kullanım: python bulten.py [fikir_sayisi] [gorsel_sayisi]
Çıktı: cikti/YYYYMMDD/ (baskı PNG'leri, önizlemeler, veri.json) + cikti/YYYYMMDD/bulten.html
Hiçbir şey Etsy'ye yüklenmez; yayınlama kararı tasarımcınındır.
"""
import base64
import html
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import fikir
import metin
import sinyal
import takvim
import tasarim
from api import harcanan

KOK = Path(__file__).parent
STIL = ("bold retro illustration with clean thick outlines and a touch of humor, limited 3-4 color palette "
        "(VARSAYILAN: tasarımcının gerçek tarzı mağazası incelenince güncellenecek)")
e = html.escape


SATIS = KOK / "veri" / "satis_rapor.json"  # satis.py çıktısı buraya kopyalanırsa fikirler satışa göre ağırlıklanır


def calistir(n_fikir=8, n_gorsel=6):
    bugun = date.today()
    klasor = KOK / "cikti" / bugun.strftime("%Y%m%d")
    klasor.mkdir(parents=True, exist_ok=True)
    basla = harcanan()

    tk = takvim.yaklasanlar(bugun)
    temalar = fikir.temalar_hazirla(sinyal.mevsimsellik(bugun))
    gundem = sinyal.gundem()
    suzulmus = fikir.gundem_suz(gundem)
    kullanilir = [g for g in suzulmus if g.get("karar") == "kullanilabilir"]
    fk = fikir.fikirler(bugun.isoformat(), [t for t in tk if t["durum"] != "geç kalındı"], temalar, kullanilir,
                        STIL.split(" (VARSAYILAN")[0], n_fikir,
                        json.loads(SATIS.read_text(encoding="utf-8")) if SATIS.exists() else None)

    uygun = [f for f in fk if f["risk"] == "dusuk"][:n_gorsel]

    def isle(i_f):
        i, f = i_f
        istem = f["prompt"] + (f' Text in the design exactly: "{f["slogan"]}".' if f.get("slogan") else "") + \
            " Designed to print on a light-colored t-shirt."
        try:
            f["tasarim"] = tasarim.uret(istem, klasor / f"tasarim_{i + 1:02d}")
        except Exception as h:
            f["tasarim"] = {"hata": str(h)[:200]}
        try:
            f["liste"] = metin.yaz(f)
        except Exception as h:
            f["liste"] = {"hata": str(h)[:200]}
        return f

    with ThreadPoolExecutor(3) as h:
        list(h.map(isle, enumerate(uygun)))

    veri = {"tarih": bugun.isoformat(), "takvim": tk, "temalar": temalar, "gundem": suzulmus, "fikirler": fk,
            "maliyet_usd_tahmini": round(harcanan() - basla, 3)}
    (klasor / "veri.json").write_text(json.dumps(veri, ensure_ascii=False, indent=1), encoding="utf-8")
    (klasor / "bulten.html").write_text(sayfa(veri, klasor), encoding="utf-8")
    return klasor, veri


def _gorsel(klasor, ad):
    p = klasor / ad
    return f"data:image/webp;base64,{base64.b64encode(p.read_bytes()).decode()}" if p.exists() else ""


def sayfa(v, klasor):
    durum_renk = {"zamanında": "iyi", "acele": "uyari", "geç kalındı": "kotu"}
    tk = "".join(f"<tr><td>{e(t['ad'])}</td><td>{t['tarih']}</td><td>{t['gun_kaldi']} gün</td>"
                 f"<td><span class='rozet {durum_renk[t['durum']]}'>{t['durum']}</span></td>"
                 f"<td>{t['ideal_liste']} / {t['en_gec_liste']}</td><td class='soluk'>{e(t['ipucu'])}</td></tr>" for t in v["takvim"])
    tm = "".join(f"<tr><td>{e(m['tema'])}</td><td>{m['yukselis']}×</td><td>{m['ivme_goreli']}</td>"
                 f"<td class='soluk'>{m['aylik_ort']:,}</td></tr>" for m in v["temalar"][:12])
    gd = "".join(f"<li><b>{e(g['baslik'])}</b>: {'✓ ' + e(g.get('genel_tema', '')) if g['karar'] == 'kullanilabilir' else '✗ ' + e(g.get('neden', ''))}</li>"
                 for g in v["gundem"])
    kartlar = []
    for f in v["fikirler"]:
        if f["risk"] != "dusuk":
            kartlar.append(f"<article class='kart elendi'><h3>{e(f['baslik'])}</h3><p class='soluk'>Elendi (fikri mülkiyet riski): "
                           f"{e(f.get('risk_nedeni', ''))}</p><p class='soluk'>Slogan: “{e(f.get('slogan', ''))}”</p></article>")
            continue
        t, l = f.get("tasarim", {}), f.get("liste", {})
        if not t and not l:
            kartlar.append(f"<article class='kart'><h3>{e(f['baslik'])}</h3><p>{e(f['neden_simdi'])}</p>"
                           f"<p class='soluk'>Slogan: “{e(f.get('slogan', ''))}” · Bu hafta görsel sınırı nedeniyle taslak üretilmedi.</p></article>")
            continue
        gorsel = (f"<div class='gorseller'><figure class='acik'><img alt='' src='{_gorsel(klasor, t['onizleme'])}'><figcaption>açık tişört</figcaption></figure>"
                  f"<figure class='koyu'><img alt='' src='{_gorsel(klasor, t['onizleme'])}'><figcaption>koyu tişört</figcaption></figure></div>"
                  f"<p class='soluk'>Baskı dosyası: {e(t['baski'])} ({t['boyut']}, şeffaf, köken bilgisi {'korundu' if t['xmp_korundu'] else 'YOK'})</p>"
                  + (f"<p class='uyari-yazi'>Tasarımın %{round(t['kaybolan_oran'] * 100)}'i beyaza çok yakın: beyaz tişörtte kaybolabilir, kontrol edin.</p>"
                     if t.get("kaybolan_oran", 0) > 0.2 else "")
                  if "onizleme" in t else f"<p class='kotu'>Görsel üretilemedi: {e(t.get('hata', ''))}</p>")
        liste = ""
        if "baslik" in l:
            liste = (f"<details><summary>Etsy metni</summary><p><b>Başlık</b> ({len(l['baslik'])}/140): {e(l['baslik'])}</p>"
                     f"<p><b>Etiketler</b> ({len(l['etiketler'])}/13): {' · '.join(e(x) for x in l['etiketler'])}</p>"
                     f"<pre>{e(l['aciklama'])}</pre>"
                     + ("<p class='uyari-yazi'>Ürün bilgileri (kumaş, beden…) eksik: urun.json doldurulmalı.</p>" if l.get("eksik_bilgi") else "")
                     + "".join(f"<p class='uyari-yazi'>• {e(s)}</p>" for s in l.get("sorunlar", [])) + "</details>")
        kartlar.append(f"""<article class='kart'><div class='ust'><span class='rozet'>{e(f['kaynak'])}</span>
          {f"<span class='rozet uyari'>son liste: {e(f['son_liste_tarihi'])}</span>" if f.get('son_liste_tarihi') else ''}</div>
          <h3>{e(f['baslik'])}</h3><p>{e(f['neden_simdi'])}</p><p class='soluk'>Alıcı: {e(f['hedef_alici'])}
          {f" · Slogan: “{e(f['slogan'])}”" if f.get('slogan') else ''}</p>{gorsel}{liste}</article>""")
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tişört Fikir Bülteni</title><style>
:root{{--bg:#f7f5f0;--yuzey:#fff;--yazi:#1d1c1a;--soluk:#6a675f;--cizgi:#e4e0d6;--iyi:#1f6b4f;--uyari:#9a5b00;--kotu:#a3271c}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151513;--yuzey:#1f1e1b;--yazi:#edebe4;--soluk:#a3a097;--cizgi:#35332e;--iyi:#7fd0ac;--uyari:#f0b14a;--kotu:#f08a7e}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--yazi);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}}
.sar{{max-width:980px;margin:0 auto;padding:24px 16px 64px}}h1{{font:600 26px/1.2 Georgia,serif;margin:0}}h2{{font-size:17px;margin:28px 0 8px}}
.soluk{{color:var(--soluk)}}.uyari-yazi{{color:var(--uyari);font-size:13px;margin:4px 0}}.kotu{{color:var(--kotu)}}
.tablo{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{border-bottom:1px solid var(--cizgi);padding:6px 8px;text-align:left;vertical-align:top}}
.rozet{{font-size:12px;border-radius:4px;padding:1px 7px;background:var(--cizgi)}}.rozet.iyi{{color:var(--iyi)}}.rozet.uyari{{color:var(--uyari)}}.rozet.kotu{{color:var(--kotu)}}
.izgara{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}}
.kart{{background:var(--yuzey);border:1px solid var(--cizgi);border-radius:10px;padding:14px}}.kart.elendi{{opacity:.75}}
.kart h3{{margin:6px 0;font-size:16px}}.ust{{display:flex;gap:6px;flex-wrap:wrap}}
.gorseller{{display:grid;grid-template-columns:1fr 1fr;gap:6px}}figure{{margin:0;border-radius:8px;padding:8px;text-align:center}}
figure.acik{{background:#f1efe9}}figure.koyu{{background:#23252b}}figure img{{width:100%;height:auto;display:block}}
figcaption{{font-size:11px;color:#8a877f;margin-top:4px}}pre{{white-space:pre-wrap;font:13px/1.5 inherit;background:var(--bg);padding:8px;border-radius:6px}}
ul{{padding-left:18px}}li{{margin:3px 0;font-size:14px}}.not{{font-size:13px;color:var(--soluk);border-left:3px solid var(--cizgi);padding:4px 10px}}
</style></head><body><div class="sar">
<h1>Tişört Fikir Bülteni</h1><p class="soluk">{v['tarih']} · Etsy (ABD alıcıları) için · tahmini maliyet {v['maliyet_usd_tahmini']} $</p>
<p class="not">Taslaktır: hiçbir şey Etsy'ye yüklenmedi. Tasarımlar yapay zekâ ile üretildi; Etsy'de "yapay zekâ kullandım"
beyanı işaretlenmeli ve tasarımcı son dokunuşu yapmalı. Fikri mülkiyet taraması bariz riskleri yakalar, hukuki kontrol değildir.</p>
<h2>Takvim</h2><div class="tablo"><table><tr><th>Gün</th><th>Tarih</th><th>Kalan</th><th>Durum</th><th>İdeal / en geç listeleme</th><th>Not</th></tr>{tk}</table></div>
<h2>İlgisi yükselecek temalar</h2><p class="soluk">Geçen yıl önümüzdeki iki ayda Wikipedia ilgisinin yıllık ortalamaya oranı. Etsy talebi değil, genel ilginin vekili.</p>
<div class="tablo"><table><tr><th>Tema</th><th>Yükseliş</th><th>Göreli ivme</th><th>Aylık görüntülenme</th></tr>{tm}</table></div>
<h2>Bugünün gündemi (ABD) ve risk filtresi</h2><ul>{gd}</ul>
<h2>Fikirler</h2><div class="izgara">{''.join(kartlar)}</div>
</div></body></html>"""


if __name__ == "__main__":
    n_f = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    n_g = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    k, v = calistir(n_f, n_g)
    print(k / "bulten.html")
    print("maliyet (tahmini):", v["maliyet_usd_tahmini"], "$")
    for f in v["fikirler"]:
        print(f"- [{f['risk']}] {f['baslik']} | {f.get('slogan', '')} | {f.get('risk_nedeni', '')}"
              + (f" | liste sorunları: {f['liste'].get('sorunlar')}" if f.get('liste') else ""))
