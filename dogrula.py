"""Yayınlanan veri dosyalarını sema/ klasöründeki şemalarla doğrular.

Kullanım: python dogrula.py                      (veri/durum.json ve veri/gunluk/*.json)
          python dogrula.py --kontrol site/kontrol.json
Gerekli: python -m pip install jsonschema
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

KOK = Path(__file__).parent
from isle import ENGEL


def yukle(yol: Path):
    with open(yol, encoding="utf-8") as f:
        return json.load(f)


def dogrulayici(ad: str) -> Draft202012Validator:
    semalar = [yukle(p) for p in (KOK / "sema").glob("*.schema.json")]
    kayit = Registry().with_resources((s["$id"], Resource.from_contents(s)) for s in semalar)
    sema = next(s for s in semalar if s["$id"].endswith(f"/{ad}.schema.json"))
    return Draft202012Validator(sema, registry=kayit)


def hatalar(v: Draft202012Validator, veri, dosya: str) -> list[str]:
    return [f"{dosya}: {'/'.join(map(str, h.absolute_path)) or '(kök)'}: {h.message}" for h in v.iter_errors(veri)]


def tutarlilik(durum: dict) -> list[str]:
    """Şemanın söyleyemediği kurallar."""
    out = []
    for site, s in durum["siteler"].items():
        for g in s["gecmis"]:
            if g["engelli"] != (g["sonuc"] in ENGEL):
                out.append(f"durum.json: {site} {g['tarih']}: engelli={g['engelli']} ama sonuc={g['sonuc']}")
        if s["gecmis"][-1]["engelli"] != (s["son"]["sonuc"] in ENGEL):
            out.append(f"durum.json: {site}: geçmişin son satırı ile 'son' uyuşmuyor")
        tarihler = [g["tarih"] for g in s["gecmis"]]
        if tarihler != sorted(tarihler) or tarihler[-1] > s["son_olcum"]:
            out.append(f"durum.json: {site}: geçmiş tarihleri sırasız")
    return out


def main(arg: list[str]) -> int:
    for akis in (sys.stdout, sys.stderr):
        akis.reconfigure(encoding="utf-8")
    out: list[str] = []
    if arg[:1] == ["--kontrol"]:
        out += hatalar(dogrulayici("kontrol"), yukle(Path(arg[1])), arg[1])
    else:
        gunler = sorted((KOK / "veri" / "gunluk").glob("*.json"))
        v = dogrulayici("gunluk")
        for f in gunler:
            out += hatalar(v, yukle(f), f"gunluk/{f.name}")
        durum = yukle(KOK / "veri" / "durum.json")
        h = hatalar(dogrulayici("durum"), durum, "durum.json")
        out += h or tutarlilik(durum)
        if not out:
            print(f"tamam: durum.json ({len(durum['siteler'])} site) ve {len(gunler)} günlük dosya şemaya uyuyor")
    for h in out[:50]:
        print(h, file=sys.stderr)
    if len(out) > 50:
        print(f"... ve {len(out) - 50} hata daha", file=sys.stderr)
    return 1 if out else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
