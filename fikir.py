"""Takvim + mevsimsellik + gündemden tişört fikirleri üretir ve risk filtresinden geçirir.

Risk: marka, film/dizi/oyun karakteri, ünlü/sporcu adı ya da tanınmış slogan içeren fikir
Etsy'de telif/marka şikayeti ve mağaza kapanması riski taşır; bunlar elenir.
"""
import json
import re
import statistics

from api import sor

# Bariz riskli kelimeler (kod katmanı). Tam bir marka veritabanı değildir; yalnızca sık görülenleri yakalar.
RISKLI = r"\b(disney|marvel|pixar|star wars|harry potter|hogwarts|pokemon|pokémon|nintendo|mario|zelda|minecraft|" \
         r"fortnite|barbie|hello kitty|sanrio|snoopy|peanuts|grinch|dr\.? seuss|looney|mickey|minnie|stitch|grogu|" \
         r"yoda|batman|superman|spider-?man|avengers|nfl|nba|mlb|nhl|fifa|olympic|super bowl|world series|" \
         r"taylor swift|swiftie|eras tour|nike|adidas|coca-?cola|starbucks|budweiser|jack daniel|harley|jeep|" \
         r"friends tv|stranger things|the office|game of thrones|lord of the rings|tolkien|simpsons|sesame|" \
         r"bluey|peppa|paw patrol|squishmallow|labubu|lego|hot wheels|nascar|ugly christmas sweater|" \
         r"just do it|keep calm|got milk)\b"

GUNDEM_ISTEM = """Below are today's trending US Google searches. For a small Etsy t-shirt seller, classify each one.
"kullanilabilir" ONLY if it points to a generic, non-proprietary theme a design could reference WITHOUT naming any
person, team, league, brand, show, game, film, company or event trademark, and it is not about a tragedy/crime/death.
Otherwise "kacin" with a short reason (e.g. "kişi adı", "takım/lig", "marka", "trajedi").
Return JSON only: {{"sonuc": [{{"baslik": "...", "karar": "kullanilabilir|kacin", "neden": "Türkçe kısa", "genel_tema": "if usable, the generic theme in English, else empty"}}]}}

{liste}"""

FIKIR_ISTEM = """You are helping a small independent t-shirt designer who sells on Etsy (mostly US buyers).
Today is {bugun}. Propose {n} original t-shirt design ideas for listings he can still publish in time.

SEASONAL CALENDAR (listing status: zamanında = on time, acele = hurry, geç kalındı = too late):
{takvim}

THEMES WITH RISING INTEREST in the coming buying window (Wikipedia interest last year for these months vs yearly
average = yukselis; recent momentum vs others = ivme_goreli):
{temalar}

USABLE GENERIC TRENDS TODAY (already filtered): {gundem}

THIS SHOP'S OWN SALES (strongest signal when present; build on what already sells, e.g. new seasonal twists on
best-selling themes): {satis}

DESIGNER STYLE: {stil}

Rules:
- Strictly original. No brands, franchises, characters, celebrities, sports teams/leagues, song lyrics, film quotes,
  or well-known existing slogans. No "ugly Christmas sweater" (trademark disputes). No real people.
- Prefer ideas that combine a seasonal moment with an evergreen niche (e.g. a hobby or an animal) so the shirt sells
  beyond one day.
- Skip events marked "geç kalındı".
- slogan: English, max 6 words, witty, or empty for image-only designs.
- prompt: an English image-generation prompt for a PRINT DESIGN (not a shirt photo): "isolated on plain pure white
  background, no t-shirt, no mockup, no text other than the slogan", screen-print friendly, limited palette, bold
  outlines, plus the designer style.
Return JSON only:
{{"fikirler": [{{"baslik": "short Turkish title", "kaynak": "takvim|mevsim|gundem", "neden_simdi": "Türkçe, 1 cümle, verilere dayan",
  "hedef_alici": "Türkçe", "slogan": "...", "prompt": "...", "son_liste_tarihi": "YYYY-MM-DD or empty"}}]}}"""

RISK_ISTEM = """You review t-shirt ideas for an Etsy seller for intellectual-property risk.
For each idea: does the slogan or the described image use or closely imitate a trademark, brand, franchise, character,
celebrity/real person, sports team/league, song lyric, film/TV quote, or a widely known existing slogan or meme phrase?
Be strict but do not flag generic words (cat, coffee, Christmas, turkey, reindeer are generic).
Return JSON only: {{"sonuc": [{{"risk": "dusuk|yuksek", "neden": "Türkçe kısa, yuksekse"}}]}}  (same order)

{liste}"""


def _json(s):
    s = re.sub(r"^```(json)?|```$", "", s.strip(), flags=re.M).strip()
    return json.loads(s[s.find("{"): s.rfind("}") + 1])


def _sor_json(istem, etiket, max_tokens=20000, deneme=3):
    """Akıl yürütme token'ları sınırı doldurup boş cevap dönebiliyor: geniş sınır + yeniden deneme."""
    for i in range(deneme):
        try:
            return _json(sor(istem, max_tokens=max_tokens, json_mod=True, etiket=etiket))
        except (json.JSONDecodeError, ValueError):
            if i == deneme - 1:
                raise


def gundem_suz(ogeler):
    if not ogeler:
        return []
    liste = "\n".join(f"- {o['baslik']} (news: {'; '.join(o['haberler'])})" for o in ogeler)
    sonuc = _sor_json(GUNDEM_ISTEM.format(liste=liste), "gundem")["sonuc"]
    for s in sonuc:  # kod katmanı: riskli kelime varsa model ne derse desin ele
        if re.search(RISKLI, s.get("baslik", "") + " " + s.get("genel_tema", ""), flags=re.I):
            s["karar"], s["neden"] = "kacin", "riskli kelime listesinde"
    return sonuc


def temalar_hazirla(mev, n=15):
    gecerli = [m for m in mev if "yukselis" in m]
    ortanca = statistics.median(m["ivme"] for m in gecerli)
    for m in gecerli:
        m["ivme_goreli"] = round(m["ivme"] / ortanca, 2)
    return gecerli[:n]


def fikirler(bugun, takvim, temalar, gundem_kullanilir, stil, n=8, satis=None):
    t = "\n".join(f"- {g['ad']} {g['tarih']}: {g['durum']} (ideal listing by {g['ideal_liste']}, "
                  f"latest {g['en_gec_liste']}); note: {g['ipucu']}" for g in takvim)
    tm = "\n".join(f"- {m['tema']}: yukselis {m['yukselis']}, ivme_goreli {m['ivme_goreli']}" for m in temalar)
    g = ", ".join(x["genel_tema"] for x in gundem_kullanilir) or "none"
    st = "none available"
    if satis:
        st = ("best sellers: " + "; ".join(f"{u['urun']} ({u['adet']} sold, last 30 days {u['son30']})" for u in satis["en_cok"][:6])
              + " | top themes: " + ", ".join(f"{k} {v}" for k, v in satis["tema"][:6])
              + " | shirt colors: " + ", ".join(f"{k} {v}" for k, v in satis["renk"][:4]))
    liste = _sor_json(FIKIR_ISTEM.format(bugun=bugun, n=n, takvim=t, temalar=tm, gundem=g, stil=stil, satis=st),
                      "fikir")["fikirler"]
    # risk: önce kod, sonra model
    metinler = "\n".join(f"{i + 1}. slogan: {f.get('slogan', '')} | image: {f.get('prompt', '')}" for i, f in enumerate(liste))
    try:
        model_risk = _sor_json(RISK_ISTEM.format(liste=metinler), "risk")["sonuc"]
    except Exception:
        model_risk = [{"risk": "yuksek", "neden": "risk denetimi yapılamadı"}] * len(liste)
    for f, r in zip(liste, model_risk + [{}] * len(liste)):
        kod = re.search(RISKLI, f.get("slogan", "") + " " + f.get("prompt", ""), flags=re.I)
        f["risk"] = "yuksek" if kod or r.get("risk") != "dusuk" else "dusuk"
        f["risk_nedeni"] = f"riskli kelime: {kod.group(0)}" if kod else r.get("neden", "")
    return liste
