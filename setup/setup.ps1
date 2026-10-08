# Asset Auto Generator launcher for Windows (called by Start.bat). Was "Tripo3D Auto Generation" before 2026-10-08.
# First run on a PC: downloads portable Blender 4.2 LTS (about 370 MB, checksum-verified) into
# %LOCALAPPDATA%\AssetAutoGenerator and adds Pillow from setup\wheels. Nothing is installed system-wide and no admin
# rights are needed. Later runs start straight away.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$Pkg = Split-Path -Parent $PSScriptRoot
$Local = Join-Path $env:LOCALAPPDATA 'AssetAutoGenerator'
$Old = Join-Path $env:LOCALAPPDATA 'Tripo3DAutoGen'          # the name before 2026-10-08: renamed once, nothing re-downloaded
if ((Test-Path $Old) -and -not (Test-Path $Local)) {
    try { Rename-Item -Path $Old -NewName 'AssetAutoGenerator'; Write-Host 'Renamed this PC''s local folder Tripo3DAutoGen -> AssetAutoGenerator.' }
    catch { $Local = $Old; Write-Host 'Note: could not rename the local folder (a file in it may be open); using the old one for now.' }
}
$Ver = '4.2.23'
$Name = "blender-$Ver-windows-x64"
$Sha = '82e791475779a7342424a480bdde9a20b43710da9264c60346125aa16cd910cb'
$BDir = Join-Path $Local $Name
$Py = Join-Path $BDir '4.2\python\bin\python.exe'
New-Item -ItemType Directory -Force -Path $Local | Out-Null

if (-not (Test-Path (Join-Path $BDir 'blender.exe'))) {
    Write-Host "First run on this PC: downloading Blender $Ver (about 370 MB). This happens once."
    $Zip = Join-Path $Local "$Name.zip"
    Invoke-WebRequest -UseBasicParsing -Uri "https://download.blender.org/release/Blender4.2/$Name.zip" -OutFile $Zip
    $h = (Get-FileHash -Algorithm SHA256 $Zip).Hash.ToLower()
    if ($h -ne $Sha) { Remove-Item $Zip -Force; throw "Blender download failed its checksum check. Run Start.bat again." }
    Write-Host 'Unpacking Blender (a few minutes)...'
    if (Get-Command tar.exe -ErrorAction SilentlyContinue) { tar.exe -xf $Zip -C $Local } else { Expand-Archive -Path $Zip -DestinationPath $Local -Force }
    Remove-Item $Zip -Force
}

# Pillow must sit inside Blender's own site-packages. (Asking python.exe to "import PIL" is not a valid check:
# a PYTHONPATH set on this PC can make it find another Python's Pillow, which Blender itself ignores.)
$Site = Join-Path $BDir '4.2\python\lib\site-packages'
$Whl = Get-ChildItem (Join-Path $Pkg 'setup\wheels') -Filter 'pillow-*-cp311-*win_amd64.whl' | Sort-Object Name -Descending | Select-Object -First 1
$WantVer = ($Whl.Name -split '-')[1]
# Installed when missing, and replaced when the package ships a newer Pillow (12.x reads AVIF photos; 11.0 can't).
if (-not (Test-Path (Join-Path $Site "pillow-$WantVer.dist-info"))) {
    Write-Host "Adding Pillow $WantVer to Blender's Python..."
    Get-ChildItem $Site -Directory -Filter 'pillow-*.dist-info' -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    if (Test-Path (Join-Path $Site 'PIL')) { Remove-Item (Join-Path $Site 'PIL') -Recurse -Force -ErrorAction SilentlyContinue }
    if (Test-Path (Join-Path $Site 'pillow.libs')) { Remove-Item (Join-Path $Site 'pillow.libs') -Recurse -Force -ErrorAction SilentlyContinue }
    $Tmp = Join-Path $env:TEMP 'autogen_pillow.zip'
    Copy-Item $Whl.FullName $Tmp -Force
    Expand-Archive -Path $Tmp -DestinationPath $Site -Force
    Remove-Item $Tmp -Force
}

Set-Location $Pkg
$env:PYTHONDONTWRITEBYTECODE = '1'      # keep the shared drive free of __pycache__ folders
$env:PYTHONUTF8 = '1'
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue   # this PC's other Python must not leak in
Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue
$ErrorActionPreference = 'Continue'
Write-Host 'Starting Asset Auto Generator. Keep this window open while you work; close it to stop.'
& $Py -m autogen serve
