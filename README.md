# Türkiye Sansür Gözlemevi

Türkiye'de hangi sitelerin engelli olduğunu, **hangi operatörde**, **nasıl** ve **ne zamandan beri** engellendiğini her gün gösterir. Sonuçlar herkese açık bir sayfada yayınlanır: **https://cybergah.github.io/sansur-gozlemevi/**

**[English below](#in-english)** · Sayfa İngilizce de okunabilir: **https://cybergah.github.io/sansur-gozlemevi/?lang=en**

## Nasıl çalışır?

Ölçümler [OONI](https://ooni.org) gönüllülerinindir. Türkiye'de pek çok kişi OONI Probe uygulamasıyla siteleri kendi internetinden dener; OONI bu ölçümleri her gün herkese açık yayınlar. Gözlemevi bu açık veriyi toplar ve sade bir tabloya çevirir.

1. **Toplama:** Her sabah GitHub Actions `ooni.py`'yi çalıştırır. Program OONI'den son 7 günün Türkiye web ölçümlerini alır: site ve operatör bazında ölçüm sayıları (tek sorgu) ve engel yöntemini görmek için son 3 günün anomali çıkan ölçümlerinden bir örnek.
2. **Karar:** [Citizen Lab listesindeki](https://github.com/citizenlab/test-lists) yaklaşık 2.100 sitenin her biri için, her operatörde ayrı karar verilir:
   - OONI ölçümde Türkiye'nin engel sayfasını gördüyse (parmak izi) tek ölçüm yeter. Bu **doğrulanmış** engeldir.
   - Değilse en az 5 başarılı ölçümün %60'ında sorun çıkması gerekir. Bu **olası** engeldir.
   - Yalnızca ev ve mobil internet operatörleri sayılır: Türk Telekom, Türk Telekom Mobil, Superonline, Turkcell, Vodafone, TurkNet, Türksat Kablo ve Netspeed. Şirket, okul ve veri merkezi ağları kendi filtrelerini uyguladığı için sonucu bozar.
   - Engel yöntemi OONI'nin her ölçüm için yaptığı tahminden gelir: DNS, IP adresi, bağlantının kesilmesi (çoğunlukla site adına, SNI'ye göre) ya da sayfanın değiştirilmesi.
3. **Geçmiş:** `isle.py` günün sonucunu `veri/gunluk/` klasörüne yazar ve `veri/durum.json` dosyasındaki geçmişi günceller. Geçmiş, her sitenin ne zaman engellendiğini ve ne zaman açıldığını tutar.
4. **Karşı kontrol (Türkiye dışından):** Olası engeller GitHub'ın ABD'deki sunucusundan ayrıca denenir (`kontrol.py`). Orada da açılmayan site engelli sayılmaz, çünkü sorun sitenin kendisindedir.
5. **Sayfa:** `site/index.html` GitHub Pages'te Türkçe ve İngilizce yayınlanır.

## Veri biçimi

Bütün veriler JSON'dur. Alanların tam tanımı [`sema/`](sema/) klasöründeki JSON Schema (2020-12) dosyalarındadır. Her çalışmada GitHub Actions verinin bu şemalara uyduğunu `dogrula.py` ile kontrol eder.

| Dosya | Şema | İçerik |
|---|---|---|
| `veri/durum.json` | [`durum.schema.json`](sema/durum.schema.json) | Her sitenin şu anki durumu, engel geçmişi ve operatör özeti |
| `veri/gunluk/YYYY-MM-DD.json` | [`gunluk.schema.json`](sema/gunluk.schema.json) | Bir günün sonucu; dosya adı 7 günlük pencerenin son günüdür (UTC) |
| [`kontrol.json`](https://cybergah.github.io/sansur-gozlemevi/kontrol.json) (yalnız sayfada) | [`kontrol.schema.json`](sema/kontrol.schema.json) | Olası engellerin Türkiye dışından karşı kontrolü |

`veri/durum.json` içinden kısaltılmış bir örnek:

```json
{
 "kaynak": "OONI",
 "pencere": {"baslangic": "2026-11-11", "bitis": "2026-11-17"},
 "operatorler": {"Türk Telekom": {"olcum": 58651, "site": 2071, "engelli": 232}},
 "siteler": {
  "t24.com.tr": {
   "kategori": "NEWS",
   "son_olcum": "2026-11-17",
   "son": {
    "sonuc": "dns", "kesin": true,
    "operatorler": {"Türk Telekom": {"sonuc": "dns", "olcum": 72, "kesin": true}}
   },
   "gecmis": [{"tarih": "2026-11-17", "engelli": true, "sonuc": "dns"}]
  }
 }
}
```

- **`sonuc`:** `acik`, `dns`, `ip_engeli`, `baglanti_kesildi`, `sayfa_degistirildi`, `engelli` (yöntem belirlenemedi) ya da `bilinmiyor` (yeterli ölçüm yok). `acik` ve `bilinmiyor` dışındakiler engel sayılır.
- **`kesin`:** OONI en az bir ölçümde Türkiye'nin engel sayfasını gördü. Yoksa alan yazılmaz ve engel "olası" sayılır.
- **`operatorler`:** Yalnızca engelli sitelerde, operatör operatör sonuç ve ölçüm sayısı.
- **`gecmis`:** Her gün değil, yalnızca engel durumu değişince yeni satır eklenir. Son satırın tarihi, şu anki durumun ne zamandan beri sürdüğünü gösterir.
- **`kategori`:** Citizen Lab kategori kodudur, örneğin `NEWS`, `HUMR`, `POLR`, `LGBT`.

Kendi bilgisayarında çalıştırmak ve doğrulamak için:

```bash
python -m pip install -r requirements.txt jsonschema
python ooni.py            # dünü bitiş günü alır; ya da: python ooni.py 2026-11-17
python dogrula.py
```

## Sınırlar

- Ölçümler gönüllülerden geldiği için her site her gün her operatörde ölçülmeyebilir. Küçük operatörlerde veri azdır; sayfadaki operatör tablosu kaç sitenin değerlendirilebildiğini gösterir.
- Sonuç 7 günlük ölçümlere dayanır. Yeni bir engel ya da kaldırılan bir engel birkaç gün gecikmeyle görünebilir.
- Yalnızca ana sayfaya bakılır. Tek bir haberin ya da sayfanın engellenmesi görünmez.
- Takip 17 Kasım 2026'da başladı. Bu tarihten önceki engeller "takip başlamadan önce" olarak görünür.

## In English

**Turkey Censorship Observatory** shows every day which websites are blocked in Turkey, **on which ISP**, **how** and **since when**. Results are published on an open page: **https://cybergah.github.io/sansur-gozlemevi/?lang=en**

**How it works**

The measurements come from [OONI](https://ooni.org) volunteers, who test websites from their own connections in Turkey with the OONI Probe app. OONI publishes the results openly every day; the observatory collects them and turns them into a simple table.

1. **Collect:** every morning GitHub Actions runs `ooni.py`. It fetches the last 7 days of Turkish web measurements from the OONI API: counts per site and ISP (one query), plus a sample of the anomalous measurements from the last 3 days to see the blocking method.
2. **Decide:** for each of about 2,100 sites from the [Citizen Lab test lists](https://github.com/citizenlab/test-lists), a separate decision is made for each ISP:
   - If OONI saw Turkey's block page (fingerprint) in a measurement, one measurement is enough. This is a **verified** block.
   - Otherwise at least 60% of at least 5 successful measurements must show a problem. This is a **possible** block.
   - Only home and mobile ISPs are counted: Türk Telekom, Türk Telekom Mobil, Superonline, Turkcell, Vodafone, TurkNet, Türksat Kablo and Netspeed. Corporate, school and data-centre networks apply their own filters and would skew the result.
   - The blocking method comes from OONI's per-measurement analysis: DNS, IP address, connection cut (usually by site name, SNI) or page replaced.
3. **History:** `isle.py` writes the day's result to `veri/gunluk/` and updates the history in `veri/durum.json`, which records when each site was blocked and unblocked.
4. **Cross-check, from outside Turkey:** possible blocks are re-tested from a GitHub server in the US (`kontrol.py`). A site that does not load there either is not counted as blocked.
5. **Page:** `site/index.html` is published on GitHub Pages, in Turkish and English.

**Data:** all files are JSON, described by JSON Schemas (2020-12) in [`sema/`](sema/) and validated on every run by `dogrula.py`. Field names are in Turkish:

| Field | Meaning |
|---|---|
| `sonuc` | Result: `acik` (open), `dns`, `ip_engeli` (IP block), `baglanti_kesildi` (connection cut), `sayfa_degistirildi` (page replaced), `engelli` (blocked, method unclear), `bilinmiyor` (not enough data) |
| `kesin` | Verified: OONI saw Turkey's block page |
| `operatorler` | Per-ISP results (ISP summary at the top level) |
| `gecmis` | History |
| `engelli` | Blocked |
| `tarih` | Date |
| `kategori` | Citizen Lab category code |

**Limits**

- Because measurements come from volunteers, not every site is measured on every ISP every day. Small ISPs have little data.
- Results are based on a 7-day window, so new blocks and unblocks may show up a few days late.
- Only the home page is checked, so blocks on single articles or pages are not visible.
- Tracking started on 17 November 2026.

## Lisans

- Kod: MIT.
- Ölçüm verisi: [OONI](https://ooni.org/data/), [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
- Site listesi (`liste.csv`): [Citizen Lab test listelerinden](https://github.com/citizenlab/test-lists) türetilmiştir, CC BY-NC-SA 4.0.
- Bu depodaki sonuç dosyaları bu iki kaynaktan türetilmiştir ve aynı lisansla (CC BY-NC-SA 4.0) paylaşılır.

Bir [Cybergah](https://github.com/cybergah) projesi. Ölçümler için OONI gönüllülerine teşekkürler.
