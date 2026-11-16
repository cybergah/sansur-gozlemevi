# Türkiye Sansür Gözlemevi

Türkiye'den hangi sitelerin engelli olduğunu, **nasıl** engellendiğini ve **ne zamandan beri** engelli olduğunu her gün ölçer. Sonuçlar herkese açık bir sayfada yayınlanır: **https://cybergah.github.io/sansur-gozlemevi/**

*English: a daily, open measurement of which websites are blocked in Turkey, by which method (DNS, IP or SNI) and since when.*

## Nasıl çalışır?

1. **Ölçüm (Türkiye'den):** `olc.py` yaklaşık 2.100 siteyi dört katmanda dener:
   - **DNS:** Operatörün verdiği adres ile şifreli DNS'in (DoH) verdiği adres karşılaştırılır.
   - **Bağlantı (IP):** Sitenin gerçek adresine bağlanılır.
   - **Site adı (SNI):** Site adıyla şifreli bağlantı kurulur. Bağlantının site adı görülünce kesilip kesilmediğine bakılır.
   - **Sayfa:** Sayfanın açılıp açılmadığına bakılır.
2. **İşleme:** `isle.py` günün sonucunu `veri/gunluk/` klasörüne yazar ve `veri/durum.json` dosyasındaki geçmişi günceller. Geçmiş, her sitenin ne zaman engellendiğini ve ne zaman açıldığını tutar.
3. **Karşı kontrol (Türkiye dışından):** Her gönderimde GitHub Actions, engelli görünen siteleri ABD'deki bir sunucudan yeniden dener (`kontrol.py`). Orada da açılmayan site engelli sayılmaz, çünkü sorun sitenin kendisindedir.
4. **Sayfa:** `site/index.html` dosyası GitHub Pages'te yayınlanır.

## Veri biçimi

Bütün veriler JSON'dur. Alanların tam tanımı [`sema/`](sema/) klasöründeki JSON Schema (2020-12) dosyalarındadır. Her gönderimde GitHub Actions verinin bu şemalara uyduğunu `dogrula.py` ile kontrol eder.

| Dosya | Şema | İçerik |
|---|---|---|
| `veri/durum.json` | [`durum.schema.json`](sema/durum.schema.json) | Her sitenin şu anki durumu ve engel geçmişi |
| `veri/gunluk/YYYY-MM-DD.json` | [`gunluk.schema.json`](sema/gunluk.schema.json) | Bir günün ölçüm özeti; dosya adı ölçüm günüdür (UTC) |
| [`kontrol.json`](https://cybergah.github.io/sansur-gozlemevi/kontrol.json) (yalnız sayfada) | [`kontrol.schema.json`](sema/kontrol.schema.json) | Türkiye dışından karşı kontrol sonucu |

`veri/durum.json` içinden kısaltılmış bir örnek:

```json
{
 "son_olcum": "2026-11-14T17:19:09+00:00",
 "site_sayisi": 2121,
 "siteler": {
  "anonymouse.org": {
   "kategori": "ANON",
   "son_olcum": "2026-11-14",
   "son": {"sonuc": "sni_engeli", "dns": "ayni", "tcp": "tamam", "tls": "zaman_asimi"},
   "gecmis": [{"tarih": "2026-11-14", "engelli": true, "sonuc": "sni_engeli"}]
  }
 }
}
```

- **`sonuc`:** Değerler `acik`, `dns`, `ip_engeli`, `sni_engeli`, `http_hatasi` ya da `bilinmiyor` olabilir. Engel sayılanlar `dns`, `ip_engeli` ve `sni_engeli`dir. `bilinmiyor`, sitenin adının şifreli DNS'te de çözülmediğini gösterir; site kapanmış olabilir.
- **`dns`, `tcp`, `tls`:** Yalnızca engelli sitelerde yazılır ve engelin hangi katmanda olduğunu gösterir. Örnekteki gibi DNS ve bağlantı `tamam`, şifreli bağlantı `zaman_asimi` ise engel site adına (SNI) göre konmuştur.
- **`gecmis`:** Her gün değil, yalnızca engel durumu değişince yeni satır eklenir. Son satırın tarihi, şu anki durumun ne zamandan beri sürdüğünü gösterir.
- **`kategori`:** Citizen Lab kategori kodudur, örneğin `NEWS`, `HUMR`, `POLR`, `LGBT`.

Verilerde ölçümü yapan bağlantıyı, operatörü ya da IP adresini tanıtan hiçbir alan yoktur, olmayacak da.

Kendi bilgisayarında doğrulamak için:

```bash
python -m pip install jsonschema
python dogrula.py
```

## Sınırlar

- Ölçüm tek bir bağlantıdan yapılır. Başka operatörlerde sonuç farklı olabilir. Ölçümü yapan bağlantı ve operatör, gizlilik için yayınlanmaz. Ölçüm bilgisayarı başka bir bağlantıdayken ölçüm yapılmaz. Bağlantının koptuğu, sitelerin çoğunun "bilinmiyor" çıktığı günler de yayınlanmaz.
- Yalnızca ana sayfaya bakılır. Tek bir haberin ya da sayfanın engellenmesi görünmez.
- Sayfa metnine bakılmaz. HTTPS'te sertifika doğrulandıysa gelen sayfa sitenin kendisidir. İlk denemede "5651" ya da "erişim engellenmiştir" geçen sayfaların hepsi, sitenin kendi içeriği ya da kendi yönlendirmesiydi.

## Kendin çalıştır

```bash
python -m pip install -r requirements.txt
python olc.py liste.txt sonuc.json   # her satırda bir site adı
python isle.py sonuc.json
```

## Lisans

- Kod: MIT.
- Site listesi (`liste.csv`) ve ölçüm verileri: [Citizen Lab test listelerinden](https://github.com/citizenlab/test-lists) türetilmiştir, [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) lisanslıdır.

Bir [Cybergah](https://github.com/cybergah) projesi.
