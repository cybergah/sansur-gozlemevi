"""Türkiye'deki engelleri OONI'nin açık ölçümlerinden çıkarır.

OONI (ooni.org) gönüllülerinin Türkiye'den yaptığı web ölçümleri her gün yayınlanır.
Bu program son 7 günün ölçümlerini site ve operatör bazında toplar, liste.csv'deki
her site için bir sonuç çıkarır, günlük dosyayı yazar ve geçmişi günceller.

Yalnızca ev ve mobil internet operatörlerinin ölçümleri sayılır. Şirket, okul ve veri
merkezi ağları kendi filtrelerini uyguladığı için sonucu bozar.

Kullanım: python ooni.py              (dünü bitiş günü alır)
          python ooni.py 2026-11-17   (bu günü bitiş günü alır)
OONI verisi CC BY-NC-SA 4.0 lisanslıdır.
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

import httpx

import isle

API = "https://api.ooni.io/api/v1"
PENCERE = 7  # gün
ORNEK_GUN = 3  # engel yöntemi için bakılan son günler
ORNEK_SAYFA = 8  # en fazla 8 x 1000 ölçüm; OONI toplu veri çekilmesini istemiyor

# Ev ve mobil internet operatörleri (otonom sistem numarası -> ad).
OPERATOR = {
    9121: "Türk Telekom",
    47331: "Türk Telekom",
    20978: "Türk Telekom Mobil",
    34984: "Superonline",
    16135: "Turkcell",
    15897: "Vodafone",
    12735: "TurkNet",
    47524: "Türksat Kablo",
    206375: "Netspeed",
}

# Bir operatörde engel kararı için gereken en az başarılı ölçüm ve anomali oranı.
# OONI'nin engel sayfası parmak iziyle doğruladığı ("confirmed") tek ölçüm yeterlidir.
EN_AZ = 3
EN_AZ_ORANLI = 5
ORAN = 0.6

YONTEM = {
    "dns": "dns",
    "tcp_ip": "ip_engeli",
    "http-failure": "baglanti_kesildi",
    "http-diff": "sayfa_degistirildi",
}


def al(istemci: httpx.Client, yol: str, **params) -> dict:
    for deneme in range(4):
        try:
            r = istemci.get(yol if yol.startswith("http") else API + yol, params=params or None)
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, ValueError):
            if deneme == 3:
                raise
            time.sleep(5 * (deneme + 1))
    raise RuntimeError("ulaşılamadı")


def sayimlar(istemci: httpx.Client, bas: date, bit: date) -> list[dict]:
    """Site x operatör ölçüm sayıları (tek sorgu)."""
    return al(istemci, "/aggregation", probe_cc="TR", test_name="web_connectivity",
              since=bas.isoformat(), until=bit.isoformat(),
              axis_x="domain", axis_y="probe_asn")["result"]


def ornekler(istemci: httpx.Client, bas: date, bit: date) -> list[dict]:
    """Anomali çıkan ölçümlerden bir örnek; her birinde OONI'nin engel türü tahmini var."""
    out: list[dict] = []
    veri = al(istemci, "/measurements", probe_cc="TR", test_name="web_connectivity",
              since=bas.isoformat(), until=bit.isoformat(), anomaly="true", limit=1000)
    for _ in range(ORNEK_SAYFA):
        out += veri["results"]
        sonraki = veri["metadata"].get("next_url")
        if not sonraki or not veri["results"]:
            break
        time.sleep(1)
        veri = al(istemci, sonraki)
    return out


def alan_adi(girdi: str) -> str:
    a = girdi.split("://", 1)[-1].split("/", 1)[0].split(":", 1)[0].lower()
    return a


def sitenin_adlari(site: str) -> list[str]:
    s = site.lower()
    return [s, s[4:]] if s.startswith("www.") else [s, "www." + s]


def karar(siteler: list[str], sayim: list[dict], ornek: list[dict]) -> tuple[dict, dict]:
    # site -> operatör -> sayılar
    adi = {a: s for s in siteler for a in sitenin_adlari(s)}
    tablo: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    op_olcum: Counter = Counter()
    for r in sayim:
        op = OPERATOR.get(r["probe_asn"])
        s = adi.get(r["domain"].lower())
        if not op or not s:
            continue
        c = tablo[s][op]
        c["olcum"] += r["measurement_count"]
        c["basarili"] += r["measurement_count"] - r["failure_count"]
        c["anomali"] += r["anomaly_count"]
        c["kesin"] += r["confirmed_count"]
        op_olcum[op] += r["measurement_count"]

    # site -> operatör -> engel türleri
    tur: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    for m in ornek:
        op = OPERATOR.get(int(str(m.get("probe_asn", "AS0"))[2:] or 0))
        s = adi.get(alan_adi(m.get("input") or ""))
        bt = ((m.get("scores") or {}).get("analysis") or {}).get("blocking_type")
        if not op or not s or not bt or bt not in YONTEM:
            continue
        if bt == "http-diff" and not m.get("confirmed"):
            continue  # içerik farkı çoğu zaman sitenin kendi değişken içeriğidir
        tur[s][op][YONTEM[bt]] += 1

    bugun: dict[str, dict] = {}
    kapsam: Counter = Counter()  # operatör -> kararı verilebilen site sayısı
    for s in siteler:
        ops: dict[str, dict] = {}
        for op, c in tablo.get(s, {}).items():
            if c["basarili"] < EN_AZ and not c["kesin"]:
                continue
            engelli = c["kesin"] > 0 or (c["basarili"] >= EN_AZ_ORANLI and c["anomali"] >= ORAN * c["basarili"])
            if engelli:
                yontem = tur[s][op].most_common(1) or sum(tur[s].values(), Counter()).most_common(1)
                sonuc = yontem[0][0] if yontem else "engelli"
            else:
                sonuc = "acik"
            ops[op] = {"sonuc": sonuc, "olcum": c["olcum"], **({"kesin": True} if c["kesin"] else {})}
        kapsam.update(ops.keys())
        engelli_ops = {op: d for op, d in ops.items() if d["sonuc"] in isle.ENGEL}
        if engelli_ops:
            agirlik = Counter()
            for op, d in engelli_ops.items():
                agirlik[d["sonuc"]] += d["olcum"]
            d = {"sonuc": agirlik.most_common(1)[0][0], "operatorler": ops}
            if any(x.get("kesin") for x in engelli_ops.values()):
                d["kesin"] = True
        elif ops:
            d = {"sonuc": "acik"}
        else:
            d = {"sonuc": "bilinmiyor"}
        bugun[s] = d

    ozet = {
        op: {
            "olcum": n,
            "site": kapsam[op],
            "engelli": sum(1 for d in bugun.values() if d.get("operatorler", {}).get(op, {}).get("sonuc") in isle.ENGEL),
        }
        for op, n in op_olcum.items()
    }
    return bugun, ozet


def main(arg: list[str]) -> None:
    for akis in (sys.stdout, sys.stderr):
        akis.reconfigure(encoding="utf-8")
    bit = date.fromisoformat(arg[0]) if arg else datetime.now(timezone.utc).date() - timedelta(days=1)
    bas = bit - timedelta(days=PENCERE - 1)
    yol = isle.KOK / "veri" / "durum.json"
    durum = json.load(open(yol, encoding="utf-8")) if yol.exists() else {"siteler": {}}
    son_gun = durum.get("pencere", {}).get("bitis", "")
    if bit.isoformat() < son_gun:
        print(f"{bit}: yayındaki günden ({son_gun}) eski, işlenmedi", file=sys.stderr)
        sys.exit(3)
    kat = isle.kategoriler()
    siteler = list(kat)
    with httpx.Client(timeout=120, headers={"User-Agent": "sansur-gozlemevi (+https://github.com/cybergah/sansur-gozlemevi)"}) as ist:
        sayim = sayimlar(ist, bas, bit + timedelta(days=1))
        ornek = ornekler(ist, bit - timedelta(days=ORNEK_GUN - 1), bit + timedelta(days=1))
    bugun, ozet = karar(siteler, sayim, ornek)

    gun = bit.isoformat()
    if isle.bozuk(bugun):
        print(f"{gun}: sitelerin çoğu için veri yok, yayınlanmadı", file=sys.stderr)
        sys.exit(3)

    zaman = datetime.now(timezone.utc).isoformat(timespec="seconds")
    pencere = {"baslangic": bas.isoformat(), "bitis": gun}
    gunluk = isle.KOK / "veri" / "gunluk"
    gunluk.mkdir(parents=True, exist_ok=True)
    with open(gunluk / f"{gun}.json", "w", encoding="utf-8") as f:
        json.dump({"zaman": zaman, "kaynak": "OONI", "pencere": pencere, "operatorler": ozet, "siteler": bugun},
                  f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    isle.gecmise_isle(durum, gun, zaman, bugun, kat)
    durum.update(kaynak="OONI", pencere=pencere, operatorler=ozet)
    isle.yaz_durum(durum)
    eng = sum(d["sonuc"] in isle.ENGEL for d in bugun.values())
    print(f"{gun}: {eng} engelli / {sum(d['sonuc'] != 'bilinmiyor' for d in bugun.values())} veri olan site, "
          f"{len(sayim)} sayım satırı, {len(ornek)} örnek ölçüm")


if __name__ == "__main__":
    main(sys.argv[1:])
