"""Etsy ürün metni: başlık (<=140), 13 etiket (her biri <=20 karakter), açıklama.

Ürünün fiziksel özellikleri (kumaş, kesim, baskı yöntemi, bakım) YALNIZCA urun.json'dan gelir;
orada yoksa açıklamada yer tutucu kalır, uydurulmaz. Yapay zekâ beyanı açıklamaya kendiliğinden eklenir.
"""
import json
import re
from pathlib import Path

from fikir import RISKLI, _sor_json

URUN = Path(__file__).parent / "urun.json"
BEYAN = "Design note: this design was created with the help of AI image generation."
# urun.json'da "uretim_ortagi" doluysa (ör. "Printify") eklenir; Etsy üretim ortağının beyanını ister.
ORTAK_BEYAN = "Printed and shipped by our production partner ({})."
# Fiziksel iddia sözcükleri: urun.json'da geçmiyorsa açıklamada olmamalı.
IDDIALAR = r"\b(organic|eco|recycled|sustainable|vegan|handmade|hand-?printed|100% cotton|cotton|polyester|" \
           r"tri-?blend|unisex|oversized|pre-?shrunk|soft|heavyweight|lightweight|dtg|screen[- ]printed|embroider\w*)\b"

ISTEM = """Write an Etsy listing for this t-shirt design (US buyers). English.

DESIGN: {baslik}. Slogan: "{slogan}". Image: {prompt}
OCCASION / WHY NOW: {neden}
TARGET BUYER: {alici}
PRODUCT FACTS (the ONLY physical/product claims you may make; if a fact is missing, write {{{{FACT_NEEDED}}}} instead):
{olgular}

Rules: title max 140 characters, front-load the main search phrase, no ALL CAPS spam, no brand/character/celebrity
names, no "ugly sweater". Exactly 13 tags, each max 20 characters, lowercase, no duplicates, phrases buyers search.
Description: 2 short paragraphs about the design and gift occasion, then a bullet list of product facts
(only from PRODUCT FACTS). Do not mention AI (a disclosure line is added automatically).
Return JSON only: {{"baslik": "...", "etiketler": ["..."], "aciklama": "..."}}"""


def olgular():
    veri = json.loads(URUN.read_text(encoding="utf-8")) if URUN.exists() else {}
    return {k: v for k, v in veri.items() if not k.startswith("_")}


def denetle(l, olg):
    sorunlar = []
    if len(l.get("baslik", "")) > 140:
        sorunlar.append(f"başlık {len(l['baslik'])} karakter (sınır 140)")
    et = l.get("etiketler", [])
    if len(et) != 13:
        sorunlar.append(f"{len(et)} etiket (13 olmalı)")
    uzun = [e for e in et if len(e) > 20]
    if uzun:
        sorunlar.append(f"20 karakteri aşan etiket: {', '.join(uzun)}")
    if len(set(et)) != len(et):
        sorunlar.append("tekrarlanan etiket")
    hepsi = " ".join([l.get("baslik", ""), " ".join(et), l.get("aciklama", "")])
    m = re.search(RISKLI, hepsi, flags=re.I)
    if m:
        sorunlar.append(f"riskli kelime: {m.group(0)}")
    olg_metin = json.dumps(olg, ensure_ascii=False).lower()
    for s in {x.lower() for x in re.findall(IDDIALAR, l.get("aciklama", "") + " " + l.get("baslik", ""), flags=re.I)}:
        if s not in olg_metin:
            sorunlar.append(f"ürün bilgisinde olmayan iddia: {s}")
    return sorunlar


def yaz(fikir, deneme_ust=2):
    olg = olgular()
    olg_satir = "\n".join(f"- {k}: {v}" for k, v in olg.items() if v) or "(none provided)"
    duzelt = ""
    for _ in range(deneme_ust):
        l = _sor_json(ISTEM.format(baslik=fikir["baslik"], slogan=fikir.get("slogan", ""), prompt=fikir["prompt"],
                                   neden=fikir.get("neden_simdi", ""), alici=fikir.get("hedef_alici", ""),
                                   olgular=olg_satir) + duzelt, "liste")
        l["etiketler"] = [e.strip().lower() for e in l.get("etiketler", [])]
        sorunlar = denetle(l, olg)
        if not sorunlar:
            break
        duzelt = "\n\nYOUR PREVIOUS DRAFT HAD THESE PROBLEMS, FIX THEM:\n- " + "\n- ".join(sorunlar)
    l["aciklama"] = l.get("aciklama", "").rstrip() + "\n\n" + BEYAN
    if olg.get("uretim_ortagi"):
        l["aciklama"] += " " + ORTAK_BEYAN.format(olg["uretim_ortagi"])
    l["sorunlar"] = sorunlar
    l["eksik_bilgi"] = "{{FACT_NEEDED}}" in l["aciklama"]
    return l
