"""Sansür gözlemevi: bir site listesini bu bağlantıdan ölçer.

Her site için dört katman denenir:
  dns  - sistemin (operatörün) verdiği adres ile şifreli DNS (DoH) adresi aynı mı
  tcp  - gerçek adrese (DoH) 443. kapıdan bağlanılabiliyor mu
  tls  - site adıyla (SNI) şifreli bağlantı kurulabiliyor mu
  http - sayfa açılıyor mu, engel sayfası mı geliyor

Kullanım: python olc.py liste.txt sonuc.json
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import socket
import ssl
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

import httpx

ZAMAN = 10  # saniye
ESZAMANLI = 25
DOH = [
    "https://cloudflare-dns.com/dns-query?name={}&type=A",
    "https://dns.google/resolve?name={}&type=A",
]
# Türkiye'de engellenen sitelerde görülen uyarı sayfası ifadeleri
ENGEL_METNI = [
    "5651 sayılı",
    "Bilgi Teknolojileri ve İletişim Kurumu",
    "idari tedbir",
    "erişim engellenmiştir",
    "Erişim Engellenmiştir",
    "koruma tedbiri",
]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0"


def hata_adi(e: BaseException) -> str:
    if isinstance(e, (asyncio.TimeoutError, TimeoutError)):
        return "zaman_asimi"
    if isinstance(e, ConnectionResetError):
        return "baglanti_sifirlandi"
    if isinstance(e, ConnectionRefusedError):
        return "reddedildi"
    if isinstance(e, ssl.SSLCertVerificationError):
        return "sertifika"
    if isinstance(e, ssl.SSLError):
        return "tls_hatasi"
    if isinstance(e, socket.gaierror):
        return "dns_yok"
    return type(e).__name__


async def sistem_dns(ad: str) -> tuple[list[str], str | None]:
    loop = asyncio.get_running_loop()
    try:
        bilgi = await asyncio.wait_for(loop.getaddrinfo(ad, 443, family=socket.AF_INET, type=socket.SOCK_STREAM), ZAMAN)
        return sorted({b[4][0] for b in bilgi}), None
    except BaseException as e:  # noqa: BLE001
        return [], hata_adi(e)


async def doh_dns(istemci: httpx.AsyncClient, ad: str) -> list[str]:
    for sablon in DOH:
        try:
            r = await istemci.get(sablon.format(ad), headers={"accept": "application/dns-json"})
            veri = r.json()
            return sorted({c["data"] for c in veri.get("Answer", []) if c.get("type") == 1})
        except Exception:  # noqa: BLE001
            continue
    return []


async def tcp_tls(ip: str, ad: str) -> tuple[str | None, str | None]:
    """(tcp hatası, tls hatası) döner; None başarılı demektir."""
    try:
        r, w = await asyncio.wait_for(asyncio.open_connection(ip, 443), ZAMAN)
        w.close()
    except BaseException as e:  # noqa: BLE001
        return hata_adi(e), None
    ctx = ssl.create_default_context()
    try:
        r, w = await asyncio.wait_for(asyncio.open_connection(ip, 443, ssl=ctx, server_hostname=ad), ZAMAN)
        w.close()
        return None, None
    except BaseException as e:  # noqa: BLE001
        return None, hata_adi(e)


async def http_dene(istemci: httpx.AsyncClient, url: str) -> dict:
    try:
        r = await istemci.get(url)
        govde = r.text[:300_000]
        engel = next((m for m in ENGEL_METNI if m in govde), None)
        return {"durum": r.status_code, "son_adres": str(r.url), "engel_metni": engel}
    except BaseException as e:  # noqa: BLE001
        return {"hata": hata_adi(e)}


def ozel_adres(ip: str) -> bool:
    try:
        a = ipaddress.ip_address(ip)
        return a.is_private or a.is_loopback or a.is_unspecified or a.is_reserved
    except ValueError:
        return False


def karar(o: dict) -> str:
    """Tek kelimelik sonuç."""
    h = o["http"]
    # Sayfa metnine bakılmaz: HTTPS'te sertifika doğrulandıysa gelen sayfa
    # sitenin kendisidir. Denemede "5651" ve "erişim engellenmiştir" geçen
    # sayfaların hepsi sitenin kendi içeriği ya da kendi yönlendirmesiydi.
    # Türkiye'deki engel sayfasına DNS üzerinden gidilir; o durum "dns" sayılır.
    if not o["doh"]:
        return "bilinmiyor"  # site adresi dünyada da çözülmüyor olabilir
    if o["sistem_hata"] or (o["sistem"] and not set(o["sistem"]) & set(o["doh"]) and any(ozel_adres(i) for i in o["sistem"])):
        if o["tcp"] is None and o["tls"] is None:
            return "dns"
    if o["tcp"]:
        return "ip_engeli" if "http" not in h or h.get("hata") else "acik"
    if o["tls"] in ("baglanti_sifirlandi", "zaman_asimi"):
        return "sni_engeli"
    if h.get("hata"):
        return "http_hatasi"
    return "acik"


async def olc(istemci, sem, url: str) -> dict:
    ad = urlsplit(url).hostname or url
    async with sem:
        bas = time.perf_counter()
        sistem, sistem_hata = await sistem_dns(ad)
        doh = await doh_dns(istemci, ad)
        tcp = tls = None
        if doh:
            tcp, tls = await tcp_tls(doh[0], ad)
        http = await http_dene(istemci, "https://" + ad + "/")
        o = {
            "site": ad,
            "sistem": sistem,
            "sistem_hata": sistem_hata,
            "doh": doh,
            "tcp": tcp,
            "tls": tls,
            "http": http,
            "sure_ms": int((time.perf_counter() - bas) * 1000),
        }
        o["sonuc"] = karar(o)
        print(f"{o['sonuc']:<14} {ad}", flush=True)
        return o


async def main(liste: str, cikti: str) -> None:
    # Kesilen bağlantıları kapatırken asyncio'nun bastığı uyarılar ölçümün parçası değil.
    asyncio.get_running_loop().set_exception_handler(lambda loop, ctx: None)
    urller = [s.strip().lstrip("﻿") for s in open(liste, encoding="utf-8") if s.strip() and not s.startswith("#")]
    sem = asyncio.Semaphore(ESZAMANLI)
    async with httpx.AsyncClient(timeout=ZAMAN, follow_redirects=True, headers={"User-Agent": UA}, verify=True) as istemci:
        sonuc = await asyncio.gather(*(olc(istemci, sem, u) for u in urller))
    veri = {"zaman": datetime.now(timezone.utc).isoformat(timespec="seconds"), "olcumler": sonuc}
    json.dump(veri, open(cikti, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2]))
