"""Karşı kontrol: OONI'nin engel sayfasıyla doğrulamadığı olası engelleri dışarıdan dener.

Dışarıdan (GitHub sunucusu) da açılmayan site sansürlü sayılmaz: sorun sitenin kendisindedir.
Engel sayfasıyla doğrulanmış ("kesin") siteler zaten engellidir, onlar denenmez.

Kullanım: python kontrol.py veri/durum.json cikti.json
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone

import httpx

import olc
from isle import ENGEL


async def main(durum_yolu: str, cikti: str) -> None:
    durum = json.load(open(durum_yolu, encoding="utf-8"))
    siteler = [s for s, d in durum["siteler"].items() if d["son"]["sonuc"] in ENGEL and not d["son"].get("kesin")]
    sem = asyncio.Semaphore(olc.ESZAMANLI)
    async with httpx.AsyncClient(timeout=olc.ZAMAN, follow_redirects=True, headers={"User-Agent": olc.UA}) as istemci:
        sonuclar = await asyncio.gather(*(olc.olc(istemci, sem, s) for s in siteler))
    veri = {
        "zaman": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        # Dışarıdan sayfası açılan ya da en azından şifreli bağlantısı kurulan site, dünyada açık demektir.
        "disarida_acik": {
            o["site"]: bool((not o["http"].get("hata")) or (o["doh"] and o["tcp"] is None and o["tls"] is None))
            for o in sonuclar
        },
    }
    json.dump(veri, open(cikti, "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
    print(f"{sum(veri['disarida_acik'].values())}/{len(siteler)} site dışarıdan açık")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2]))
