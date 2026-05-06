param(
    [ValidateSet("Debug", "Release")]
    [string]$Config = "Debug",

    [string]$Device = "STM32F103ZE",

    [string]$Interface = "SWD",

    [int]$Speed = 4000
)

$ErrorActionPreference = "Stop"

$RootDir = $PSScriptRoot
$Firmware = Join-Path $RootDir "Car-whc\build\$Config\Car-whc.elf"
$JLinkExe = "C:\Program Files\SEGGER\JLink_V892\JLink.exe"
$CommandFile = Join-Path $RootDir "jlink_download.tmp"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Find-JLink {
    if (Test-Path $JLinkExe) {
        return $JLinkExe
    }

    $command = Get-Command "JLink.exe" -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    throw "JLink.exe not found. Please install SEGGER J-Link or add JLink.exe to PATH."
}

function Invoke-Checked {
    param(
        [string]$Command,
        [string[]]$Arguments
    )

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "'$Command $($Arguments -join ' ')' failed with exit code $LASTEXITCODE."
    }
}

if (-not (Test-Path $Firmware)) {
    throw "Firmware not found: $Firmware. Run .\build.ps1 $Config first."
}

$JLink = Find-JLink

Write-Step "Preparing J-Link command file"
$commands = @(
    "r",
    "loadfile `"$Firmware`"",
    "r",
    "g",
    "q"
)
Set-Content -Path $CommandFile -Value $commands -Encoding ASCII

try {
    Write-Step "Downloading $Config firmware with J-Link"
    Invoke-Checked $JLink @(
        "-device", $Device,
        "-if", $Interface,
        "-speed", "$Speed",
        "-autoconnect", "1",
        "-CommanderScript", $CommandFile
    )
}
finally {
    Remove-Item -LiteralPath $CommandFile -Force -ErrorAction SilentlyContinue
}

Write-Step "Download finished"
Write-Host "Firmware: $Firmware"
