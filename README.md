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
- Wikipedia ilgisi Etsy satışının doğrudan ölçüsü değildir. Tasarımcının kendi satış CSV'si atölyeden yüklenince
  (veri/satis_rapor.json) fikirler ona göre ağırlıklanır.
- Tarz şimdilik varsayılan ("retro, kalın çizgi, esprili"); tasarımcının mağazası incelenince güncellenecek.

## Herkese açık demo

**Dene:** https://51-20-66-93.sslip.io/tisort/

`canli.py` basit akışı (fikir → yazı → iki tasarım → renk önizleme → Etsy metni) AWS'de, Caddy arkasında açar (`tisort-demo.service`).
Demoda yalnız bu akışın uçları açık; uzman araçları, kullanım özeti, satış dosyası, aile/seri ve fotoğraf yükleme kapalı,
başkalarının tasarımları gösterilmez. Kişi başı günde 3 çizim (her biri 2 tasarım), toplam günde 40 çizim, harcama tavanı 5 $;
çizimler 24 saat sonra silinir. Bir tam akış yaklaşık 0,04 $.

## Atölye (elle kullanılan arayüz)

```bash
.venv/Scripts/python sunucu.py     # http://127.0.0.1:8792 (yalnızca bu bilgisayardan)
```

### Basit sayfa (ana sayfa, `kolay.html` + `kolay.py`)

Bilgisayarla arası iyi olmayan biri de ilk bakışta kullanabilsin diye her ekranda tek bir soru ve tek bir büyük düğme var:

1. **Ne çizelim?** Fikir Türkçe yazılır, sesle söylenir (tarayıcı destekliyorsa) ya da bir öneri kartına dokunulur.
   Öneriler yaklaşan özel günlerden gelir ("Noel · 53 gün kaldı") ve her zaman satan konulardan oluşur. Evcil hayvan
   fotoğrafı da eklenebilir.
2. **Tişörtün üstüne ne yazsın?** Model fikri İngilizce bir çizim tarifine çevirir ve 3 slogan önerir; her önerinin
   yanında Türkçe anlamı ve "şunu çizeceğim" cümlesi görünür. Fikirde marka, karakter ya da ünlü varsa uyarı çıkar.
   Bir seçeneğe dokununca çizim başlar.
3. **Bekleme:** Aynı anda iki tasarım çizilir. Bu sırada şunlar görünür:
   - gerçek aşamalar (hazırlanıyor → çiziyor → arka plan temizleniyor);
   - kalan süre (son 10 çizimin ortanca süresi);
   - tişört üstünde sloganın taslağı;
   - dönen Etsy ipuçları ve önceki tasarımlar.

   İlk tasarım biter bitmez gösterilir.
4. **Hangisini beğendiniz?** → **Tasarımınız hazır:**
   - 5 tişört renginde önizleme;
   - koyu renkte kaybolan çizgiler için uyarı ve tek düğmeyle koyu sürüm;
   - baskı dosyasını kaydetme;
   - kopyala düğmeli Etsy başlığı, 13 etiket ve açıklama;
   - beğenme ve benzerini çizme.

Ek olarak: "A+ Büyük yazı" düğmesi, tarayıcının geri düğmesiyle adım geri gitme ve yarım kalan fikrin saklanması var.
Hata mesajları sade Türkçe ve "Tekrar dene" düğmeli. Eski sekmeli sayfa `/uzman` adresinde duruyor (tarz, aile seti,
seri, satış raporu, bülten).

**Veriye göre değişen kısım ve sınırı:** Sayfa hangi adıma gelindiğini, hangi önerilere dokunulduğunu, rengi, indirmeyi
ve beklerken sayfadan ayrılmayı `kayitlar/kullanim.jsonl` dosyasına yazar. Kayıt yalnızca bu bilgisayarda kalır ve
`/kullanim` sayfasında özetlenir. Tek bir kullanıcıyla A/B testi anlamlı sonuç vermez, bu yüzden düğmeler kendi kendine
değişmez. Değişen yalnızca kişisel tercihlerdir: en çok seçilen tişört rengi varsayılan olur, en çok dokunulan öneriler
öne çıkar. Tasarım kararları (tek ana düğme, büyük dokunma alanları, yüksek kontrast, ikon + yazı) bilinen kullanılabilirlik
ilkelerine dayanıyor; kullanıcıyla test edilmedi.

2 Kasım denemesi:
- "sabah kahvesini içmeden konuşmayan huysuz bir baykuş" fikri yazıldı. Üç slogan önerildi; "No Coffee, No Hoot"
  seçildi ve iki tasarım yaklaşık 45 saniyede çıktı.
- Siyah tişörtte yazının kaybolduğu uyarısı çıktı (%32); koyu sürüm sorunu giderdi.
- Etsy yazısı 13 etiketle geldi. Ürün bilgileri boş olduğu için açıklamada `{{FACT_NEEDED}}` kaldı.
- Golden köpek resmiyle fotoğraf adımı: "Açık krem tüylü bir golden köpek…" doğru anlaşıldı.

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
