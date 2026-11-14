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

## Sınırlar

- Ölçüm tek bir bağlantıdan yapılır. Başka operatörlerde sonuç farklı olabilir. Ölçümü yapan bağlantı ve operatör, gizlilik için yayınlanmaz.
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
