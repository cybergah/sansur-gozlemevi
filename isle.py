"""Günlük sonuçtan her sitenin şu anki durumunu ve engel geçmişini kurar.

  veri/gunluk/YYYY-MM-DD.json  her sitenin o günkü sonucu
  veri/durum.json              her sitenin şu anki durumu ve değişim geçmişi

Günlük sonucu ooni.py üretir. Bu dosya yalnızca geçmişi işler.

Kullanım: python isle.py --yeniden   (durum.json'u günlük dosyalardan baştan kurar)
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

KOK = Path(__file__).parent

# Engel sayılan sonuçlar. "engelli": engel var ama yöntemi belirlenemedi.
ENGEL = {"dns", "ip_engeli", "baglanti_kesildi", "sayfa_degistirildi", "engelli"}

# Sitelerin yarısından çoğu için veri yoksa o gün yayınlanmaz.
# Yayınlansaydı engelli bütün siteler "açıldı" görünürdü.
BOZUK_ORAN = 0.5


def kategoriler() -> dict[str, str]:
    with open(KOK / "liste.csv", encoding="utf-8") as f:
        return {r["site"]: r["kategori"] for r in csv.DictReader(f)}


def bozuk(siteler: dict) -> bool:
    return sum(d["sonuc"] == "bilinmiyor" for d in siteler.values()) > BOZUK_ORAN * len(siteler)


def gecmise_isle(durum: dict, gun: str, zaman: str, bugun: dict, kat: dict) -> None:
    for site, d in bugun.items():
        s = durum["siteler"].setdefault(site, {"gecmis": []})
        s["kategori"] = kat.get(site, "")
        if d["sonuc"] == "bilinmiyor" and s["gecmis"]:
            # Veri gelmeyen gün durumu değiştirmez; son bilinen durum geçerli kalır.
            continue
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
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(durum, f, ensure_ascii=False, indent=1, sort_keys=True)


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
        for k in ("kaynak", "pencere", "operatorler"):
            if k in g:
                durum[k] = g[k]
    yaz_durum(durum)


if __name__ == "__main__":
    if sys.argv[1:] == ["--yeniden"]:
        yeniden()
    else:
        print(__doc__)
        sys.exit(2)
