# Tişört Fikir Bülteni

Etsy'de tişört satan bağımsız bir tasarımcı için haftalık fikir bülteni. Her hafta şunları üretir:

1. **Takvim:** yaklaşan özel günler (ABD ağırlıklı) ve "ideal / en geç listeleme" tarihleri
2. **Yükselen temalar:** kalıcı tişört nişlerinin önümüzdeki iki aydaki mevsimsel ilgisi
   (geçen yılın Wikipedia görüntülenmesi; Etsy talebinin değil, genel ilginin vekili)
3. **Gündem + risk filtresi:** Google Trends günlük aramaları; kişi, takım, marka ve trajedi içerenler elenir
4. **Fikirler:** özgün tema + slogan; marka/karakter/ünlü/tanınmış slogan riski kod ve modelle taranır
5. **Taslak tasarım:** muse-image-1.0; şeffaf arka planlı, kırpılmış, baskıya hazır PNG
6. **Etsy metni:** başlık (≤140), 13 etiket (≤20 karakter), açıklama; yapay zekâ beyanı kendiliğinden eklenir

Hiçbir şey Etsy'ye yüklenmez. Seçim, düzenleme ve yayın tasarımcınındır.

## Çalıştırma

```bash
python -m venv .venv && .venv/Scripts/python -m pip install pillow
.venv/Scripts/python bulten.py 8 6     # 8 fikir, en fazla 6 görsel -> cikti/YYYYMMDD/bulten.html
.venv/Scripts/python takvim.py         # yalnızca takvim
.venv/Scripts/python sinyal.py         # yalnızca sinyaller
```

`urun.json`: tasarımcının gerçek ürün bilgileri (kumaş, kesim, baskı yöntemi, bedenler, üretim ortağı).
Boş bırakılan alan açıklamada `{{FACT_NEEDED}}` olarak kalır; uydurulmaz.

## İlk çalıştırma (2 Kasım 2026)

- 8 fikir üretildi, 8'i de risk taramasından geçti; 6'sı için tasarım üretildi.
- Gündem: 10 trend aramanın **10'u da elendi** (sporcu, oyuncu, takım, ölüm haberi). "Günün popülerini yakalama"
  fikrinin pratikteki karşılığı bu: günlük gündem tişört için neredeyse hiç kullanılabilir tema vermiyor.
- 6 tasarımın 6'sında yazı hatasız çıktı. Sloganlar orta karar; tasarımcının elden geçirmesi gerekir.
- Baskı dosyaları: 2400–3700 px genişlik (12 inç baskıda ~200–300 DPI), ama bu 2x **büyütme** ile elde edildi;
  modelin gerçek çıktısı ~1344×1792. Düz renkli çizimlerde sorun görmedim, ince dokuda bulanıklık olabilir.
- Maliyet: metin çağrıları ~0,01 $; görseller tahmini 0,02 $/adet (Meta görsel fiyatını yayımlamamış; panelden doğrulanmalı).

## Kurallar ve sınırlar

- **Meta şartları:** Üretilen görselin sahibi kullanıcıdır ve ticari kullanım amaçlanmıştır (Model API Şartları §4.1).
  Kabul Edilebilir Kullanım Politikası köken bilgisinin (metadata/filigran) silinmesini ve çıktının "insan yapımı"
  diye sunulmasını yasaklar: baskı PNG'sine XMP köken bilgisi aynen taşınır, Meta'nın orijinal dosyası ayrıca saklanır.
- **Etsy:** Yapay zekâ ile yapılmış tasarımın beyan edilmesi gerekir (listeleme formunda AI kutusu). Bu kural
  satıcı bloglarından derlendi; Etsy'nin güncel politikası ayrıca okunmalı.
- **Fikri mülkiyet taraması** bariz riskleri (marka listesi + model) yakalar; hukuki tarama değildir.
- Model aynı anda hem fikir üretip hem risk denetliyor; bağımsız değil.
- Wikipedia ilgisi Etsy satışının doğrudan ölçüsü değildir. Tasarımcının kendi satış verisi (Etsy API, kendi izniyle)
  eklenince öneriler ona göre ağırlıklandırılmalı.
- Tarz şimdilik varsayılan ("retro, kalın çizgi, esprili"); tasarımcının mağazası incelenince güncellenecek.

## Atölye (elle kullanılan arayüz)

```bash
.venv/Scripts/python sunucu.py     # http://127.0.0.1:8792 (yalnızca bu bilgisayardan)
```

| Sekme | Ne yapar | 2 Kasım denemesi |
|---|---|---|
| Yeni tasarım | konu + slogan → tasarım; "Slogan öner" 10 aday yazıp kendini puanlar, en iyi 3'ü gösterir | çalıştı; sloganlar orta (model kendine en fazla 7/10 veriyor) |
| Kart düğmeleri | **Koyu tişört** (siyah zeminde yeniden renklendirme), **Mockup** (gerçekçi tişört fotoğrafı), Baskı PNG | koyu versiyon 3/3 üretildi, 1'inde koyu yazı siyahta okunmuyordu → otomatik kontrast uyarısı eklendi; mockup tasarımı ve yazıyı bozmadı |
| Tarzım | 2-6 örnek tasarımdan tarz tarifi çıkarır; sonraki çizimler tarif + 2 örnek referansla yapılır | kendi ürettiğimiz 3 tasarımla denendi: yeni konu (kapibara) aynı tarzda çıktı. Tasarımcının gerçek işleriyle denenmedi |
| Evcil hayvan | fotoğraftan kişiye özel portre tasarımı | kamu malı bir golden retriever fotoğrafıyla: köpek tanınabilir (renk, tasma) |
| Aile seti | aynı konseptin Papa/Mama/Kid/Baby versiyonları (ilki diğerlerine referans) | 4/4 tutarlı |
| Seri | bir tema etrafında tutarlı koleksiyon | "Cats With Jobs" 4/4 tutarlı |
| Satış raporu | Etsy "Order Items" CSV'si → en çok satan, son 30 gün, tema/renk/beden; bülten fikirleri buna göre ağırlıklanır | **yalnızca sentetik CSV ile** denendi; Etsy'nin gerçek sütun adları farklı çıkarsa eşleştirme güncellenmeli |
| Haftalık bülten | bulten.py'yi arka planda çalıştırır | |

Ek sınırlar:
- **Kapalı boşluklar:** Şeffaflaştırma kenardan başlar; tasarımın içinde kalan zemin rengindeki boşluklar (ör. kolla gövde arası)
  dolu kalır. Açık versiyon beyaz, koyu versiyon siyah tişört içindir; başka renk tişörtte bu boşluklar leke gibi görünür.
- **Kontrast uyarısı** kaba bir ölçüdür (tişört rengine yakın piksel oranı > %20): gerçek beyaz alanları da sayar.
- **Evcil hayvan:** Ücretsiz Meta kredisinde içerik Meta'nın ürün geliştirmesinde kullanılabilir; gerçek müşteri
  fotoğrafı için ücretli kullanım ya da müşteri izni gerekir.
- **Etsy görsel kuralı (22 Eki 2026, satıcı kaynaklarından):** çoğu üründe en az bir düzenlenmemiş gerçek ürün fotoğrafı
  gerekiyor; mockup ek görsel olmalı. Baskı servisi/siparişe özel ürün istisnaları Etsy'nin kendi sayfasından kontrol edilmeli.

## Sonra

- Etsy Open API v3 ile ürünü **taslak** olarak yükleme (tasarımcının kendi geliştirici uygulaması ve izni gerekir).
- Gerçek super-resolution (şu an 2x LANCZOS).
