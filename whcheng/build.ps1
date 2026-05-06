param(
    [ValidateSet("Debug", "Release")]
    [string]$Config = "Debug",

    [switch]$Clean,

    [int]$Jobs = 0
)

$ErrorActionPreference = "Stop"

$RootDir = $PSScriptRoot
$ProjectDir = Join-Path $RootDir "Car-whc"
$BuildDir = Join-Path $ProjectDir "build\$Config"
$DefaultToolchainBin = "D:\CodeTools\Compiler\arm-none-eabi-gcc\bin"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Test-CommandAvailable {
    param(
        [string]$Name,
        [string]$InstallHint
    )

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Missing command '$Name'. $InstallHint"
    }
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

if (-not (Test-Path $ProjectDir)) {
    throw "Project directory not found: $ProjectDir"
}

if ((-not (Get-Command "arm-none-eabi-gcc" -ErrorAction SilentlyContinue)) -and
    (Test-Path (Join-Path $DefaultToolchainBin "arm-none-eabi-gcc.exe"))) {
    $env:Path = "$DefaultToolchainBin;$env:Path"
}

Write-Step "Checking build tools"
Test-CommandAvailable "cmake" "Please install CMake and add it to PATH."
Test-CommandAvailable "ninja" "Please install Ninja and add it to PATH."
Test-CommandAvailable "arm-none-eabi-gcc" "Please install GNU Arm Embedded Toolchain and add its bin directory to PATH."

if ($Clean) {
    Write-Step "Clean mode enabled"
}

Write-Step "Configuring CMake preset: $Config"
Push-Location $ProjectDir
try {
    Invoke-Checked "cmake" @("--preset", $Config)

    if ($Clean) {
        Write-Step "Cleaning build outputs"
        Invoke-Checked "cmake" @("--build", "--preset", $Config, "--target", "clean")
    }

    Write-Step "Building preset: $Config"
    $buildArgs = @("--build", "--preset", $Config)
    if ($Jobs -gt 0) {
        $buildArgs += @("--parallel", "$Jobs")
    }
    Invoke-Checked "cmake" $buildArgs
}
finally {
    Pop-Location
}

Write-Step "Build finished"
Write-Host "Output directory: $BuildDir"
