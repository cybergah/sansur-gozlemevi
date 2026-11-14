# Günlük ölçüm: siteleri ölçer, sonucu işler ve GitHub'a gönderir.
# Windows Görev Zamanlayıcı her gün bu dosyayı çalıştırır.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$env:PYTHONIOENCODING = "utf-8"

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
