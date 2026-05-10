param(
    [ValidateSet("Debug", "Release")]
    [string]$Preset = "Debug"
)

$ErrorActionPreference = "Stop"

cmake --build --preset $Preset
