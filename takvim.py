"""Etsy alıcıları için yaklaşan özel günler ve listeleme son tarihleri.

Etsy'nin en büyük pazarı ABD olduğu için ABD günleri ağırlıklı. Teslim süreleri varsayımdır:
alıcı genelde 2-4 hafta önceden alışveriş yapar, baskı + kargo ~1-2 hafta; Etsy aramasının yeni ürünü
öne çıkarması da zaman alır. Bu yüzden "ideal listeleme" = gün - 45, "en geç" = gün - 21 (sezgisel).
"""
from datetime import date, timedelta

IDEAL_ONCE, EN_GEC_ONCE = 45, 21


def _nth_haftagunu(yil, ay, haftagunu, n):
    """ayın n. haftagunu'su (0=Pzt); n=-1 son."""
    if n > 0:
        g = date(yil, ay, 1)
        g += timedelta((haftagunu - g.weekday()) % 7)
        return g + timedelta(weeks=n - 1)
    son = date(yil + (ay == 12), ay % 12 + 1, 1) - timedelta(1)
    return son - timedelta((son.weekday() - haftagunu) % 7)


def _paskalya(y):
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    return date(y, (h + l - 7 * m + 114) // 31, (h + l - 7 * m + 114) % 31 + 1)


def gunler(yil):
    """(tarih, ad, not) listesi. Not: tasarım açısından ipucu ve risk."""
    return [
        (date(yil, 1, 1), "New Year", "yılbaşı sonrası satış düşük; 'new year new me' esprileri"),
        (date(yil, 2, 14), "Valentine's Day", "çift tişörtleri, 'anti-valentine' esprileri"),
        (date(yil, 3, 17), "St. Patrick's Day", "yeşil, yonca; marka bira logolarından kaçın"),
        (_paskalya(yil), "Easter", "tavşan, yumurta; çocuk bedenleri"),
        (date(yil, 4, 22), "Earth Day", "doğa, geri dönüşüm"),
        (_nth_haftagunu(yil, 5, 6, 2), "Mother's Day (US)", "anne esprileri, kişiselleştirme talebi yüksek"),
        (_nth_haftagunu(yil, 6, 6, 3), "Father's Day (US)", "baba şakaları (dad jokes), mangal, balık"),
        (date(yil, 6, 1), "Pride Month", "topluluk dili hassas; özenle"),
        (date(yil, 7, 4), "Independence Day (US)", "bayrak, retro Amerikana"),
        (date(yil, 8, 15), "Back to School", "öğretmen tişörtleri çok satar (Ağustos başı)"),
        (date(yil, 10, 31), "Halloween", "en büyük sezonlardan; Eylül başında listelenmeli"),
        (_nth_haftagunu(yil, 11, 3, 4), "Thanksgiving", "aile yemeği esprileri, hindi"),
        (_nth_haftagunu(yil, 11, 3, 4) + timedelta(1), "Black Friday / Cyber Monday", "indirim dönemi; trafik zirvede"),
        (date(yil, 12, 25), "Christmas", "en büyük satış dönemi; 'ugly sweater' tarzı, aile pijama tişörtleri"),
    ]


def yaklasanlar(bugun=None, hafta=16):
    """Bugünden itibaren `hafta` hafta içindeki günler, listeleme durumu ile."""
    bugun = bugun or date.today()
    son = bugun + timedelta(weeks=hafta)
    sonuc = []
    for yil in (bugun.year, bugun.year + 1):
        for t, ad, ipucu in gunler(yil):
            if bugun <= t <= son:
                ideal, en_gec = t - timedelta(IDEAL_ONCE), t - timedelta(EN_GEC_ONCE)
                durum = ("geç kalındı" if bugun > en_gec else "acele" if bugun > ideal else "zamanında")
                sonuc.append({"tarih": t.isoformat(), "ad": ad, "ipucu": ipucu, "ideal_liste": ideal.isoformat(),
                              "en_gec_liste": en_gec.isoformat(), "durum": durum, "gun_kaldi": (t - bugun).days})
    return sorted(sonuc, key=lambda x: x["tarih"])


if __name__ == "__main__":
    for g in yaklasanlar():
        print(f"{g['tarih']} {g['ad']:<28} {g['durum']:<12} ideal {g['ideal_liste']}, en geç {g['en_gec_liste']}")
