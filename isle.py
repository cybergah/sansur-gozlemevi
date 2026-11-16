"""Bir günlük ölçümü işler.

  veri/gunluk/YYYY-MM-DD.json  her sitenin o günkü sonucu (küçük biçim)
  veri/durum.json              her sitenin şu anki durumu ve değişim geçmişi

Kullanım: python isle.py ham-sonuc.json
          python isle.py --yeniden   (durum.json'u günlük dosyalardan baştan kurar)
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

KOK = Path(__file__).parent
ENGEL = {"dns", "sni_engeli", "ip_engeli"}


def kategoriler() -> dict[str, str]:
    with open(KOK / "liste.csv", encoding="utf-8") as f:
        return {r["site"]: r["kategori"] for r in csv.DictReader(f)}


def ozet(o: dict) -> dict:
    """Yayınlanacak alanlar. Ölçümü yapan bağlantıyı tanıtan bir şey içermez."""
    d = {"sonuc": o["sonuc"]}
    if o["sonuc"] in ENGEL:
        d["dns"] = o["sistem_hata"] or ("farkli_adres" if o["sistem"] and not set(o["sistem"]) & set(o["doh"]) else "ayni")
        d["tcp"] = o["tcp"] or "tamam"
        d["tls"] = o["tls"] or "tamam"
    return d


# Ölçümün yarısından çoğu "bilinmiyor" ise bağlantı o an kopuktu: o gün yayınlanmaz.
# Yayınlansaydı engelli bütün siteler "açıldı" görünürdü.
BOZUK_ORAN = 0.5


def bozuk(siteler: dict) -> bool:
    return sum(d["sonuc"] == "bilinmiyor" for d in siteler.values()) > BOZUK_ORAN * len(siteler)


def gecmise_isle(durum: dict, gun: str, zaman: str, bugun: dict, kat: dict) -> None:
    for site, d in bugun.items():
        s = durum["siteler"].setdefault(site, {"gecmis": []})
        s["kategori"] = kat.get(site, "")
        engelli = d["sonuc"] in ENGEL
        onceki = s["gecmis"][-1]["engelli"] if s["gecmis"] else None
        # Yalnızca engel durumu değişince geçmişe bir satır eklenir.
        if onceki is None or onceki != engelli:
            s["gecmis"].append({"tarih": gun, "engelli": engelli, "sonuc": d["sonuc"]})
        s["son"] = d
        s["son_olcum"] = gun
    durum["son_olcum"] = zaman
    durum["site_sayisi"] = len(bugun)


def yaz_durum(durum: dict) -> None:
    yol = KOK / "veri" / "durum.json"
    json.dump(durum, open(yol, "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)


def main(ham: str) -> None:
    veri = json.load(open(ham, encoding="utf-8"))
    gun = veri["zaman"][:10]
    bugun = {o["site"]: ozet(o) for o in veri["olcumler"]}
    if bozuk(bugun):
        print(f"{gun}: ölçüm bozuk (çoğu site bilinmiyor), yayınlanmadı", file=sys.stderr)
        sys.exit(3)

    gunluk = KOK / "veri" / "gunluk"
    gunluk.mkdir(parents=True, exist_ok=True)
    json.dump({"zaman": veri["zaman"], "siteler": bugun}, open(gunluk / f"{gun}.json", "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    yol = KOK / "veri" / "durum.json"
    durum = json.load(open(yol, encoding="utf-8")) if yol.exists() else {"siteler": {}}
    gecmise_isle(durum, gun, veri["zaman"], bugun, kategoriler())
    yaz_durum(durum)
    print(f"{gun}: {sum(d['sonuc'] in ENGEL for d in bugun.values())} engelli / {len(bugun)} site")


def yeniden() -> None:
    """durum.json'u veri/gunluk/ klasöründeki günlerden baştan kurar."""
    durum: dict = {"siteler": {}}
    kat = kategoriler()
    for f in sorted((KOK / "veri" / "gunluk").glob("*.json")):
        g = json.load(open(f, encoding="utf-8"))
        if bozuk(g["siteler"]):
            print(f"{f.stem}: bozuk, atlandı")
            continue
        gecmise_isle(durum, f.stem, g["zaman"], g["siteler"], kat)
    yaz_durum(durum)


if __name__ == "__main__":
    if sys.argv[1:] == ["--yeniden"]:
        yeniden()
    else:
        main(sys.argv[1])
