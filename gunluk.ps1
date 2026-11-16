# Günlük ölçüm: siteleri ölçer, sonucu işler ve GitHub'a gönderir.
# Windows Görev Zamanlayıcı her gün bu dosyayı çalıştırır.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$env:PYTHONIOENCODING = "utf-8"

# Yalnızca ev bağlantısından ölçülür: başka operatörün sonucu geçmişi bozar.
# Ev bağlantısı, modemin donanım adresi olarak ev-agi.txt dosyasında durur
# (bu dosya yalnızca bu bilgisayarda kalır, GitHub'a gönderilmez).
$agFile = Join-Path $PSScriptRoot "ev-agi.txt"
$gw = (Get-NetRoute -DestinationPrefix 0.0.0.0/0 -ErrorAction SilentlyContinue | Sort-Object RouteMetric | Select-Object -First 1).NextHop
$mac = if ($gw) { (Get-NetNeighbor -IPAddress $gw -ErrorAction SilentlyContinue | Select-Object -First 1).LinkLayerAddress } else { $null }
$ev = if (Test-Path $agFile) { (Get-Content $agFile -TotalCount 1).Trim() } else { $null }
if ($args -contains "-EvAgiKaydet") {
    if (-not $mac) { throw "modem bulunamadi" }
    Set-Content $agFile $mac -Encoding ascii
    Write-Output "ev agi kaydedildi"
    exit 0
}
if (-not $ev -or -not $mac -or $mac -ne $ev) {
    "$(Get-Date -Format s) ev aginda degil, olcum yapilmadi" | Add-Content (Join-Path $env:TEMP "sansur-olcum.log")
    exit 0
}

$liste = Join-Path $env:TEMP "sansur-liste.txt"
$ham = Join-Path $env:TEMP "sansur-ham.json"
Get-Content liste.csv -Encoding utf8 | Select-Object -Skip 1 | ForEach-Object { $_.Split(",")[0] } |
    Set-Content $liste -Encoding utf8

& $py olc.py $liste $ham | Out-File (Join-Path $env:TEMP "sansur-olcum.log") -Encoding utf8
if ($LASTEXITCODE -ne 0) { throw "olcum basarisiz" }
& $py isle.py $ham
if ($LASTEXITCODE -ne 0) { throw "isleme basarisiz" }

git pull --quiet --rebase
git add veri/durum.json veri/gunluk
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    # Windows PowerShell 5.1 BOM'suz dosyadaki Türkçe harfleri bozar, mesaj ASCII kalır.
    git commit --quiet -m "Olcum $(Get-Date -Format yyyy-MM-dd)"
    git push --quiet
}
