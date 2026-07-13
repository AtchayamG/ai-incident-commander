$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$assets = Join-Path $root "demo-video-assets"
$scenes = Get-Content (Join-Path $assets "narration.json") -Raw | ConvertFrom-Json

$voice = New-Object -ComObject SAPI.SpVoice
$preferred = @($voice.GetVoices()) | Where-Object { $_.GetDescription() -like "*Zira*" } | Select-Object -First 1
if ($null -ne $preferred) { $voice.Voice = $preferred }
$voice.Rate = 2
$voice.Volume = 100

foreach ($scene in $scenes) {
    $path = Join-Path $assets ($scene.slug + ".wav")
    $stream = New-Object -ComObject SAPI.SpFileStream
    $stream.Open($path, 3, $false)
    $voice.AudioOutputStream = $stream
    [void]$voice.Speak([string]$scene.narration)
    $stream.Close()
}
