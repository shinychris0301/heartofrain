param(
    [string]$OutputName = 'HeartOfTheRain_Promo_28s_1080x1920.mp4'
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$ffmpeg = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe'
if (-not (Test-Path -LiteralPath $ffmpeg)) {
    $ffmpeg = (Get-Command ffmpeg -ErrorAction Stop).Source
}
$work = Join-Path $root '.verification-cache\Promo121\Segments'
New-Item -ItemType Directory -Force -Path $work | Out-Null

# Every moving shot is Heart of the Rain footage. The two art cards use the
# approved launch PNGs. Earlier Android effect captures are listed explicitly.
$shots = @(
    @{ Name='01_Opening'; Kind='art'; Source='Unity\Assets\HeartOfTheRain\App\Launch\Art\Opening_Key_Art_R1.png'; Start=0; Duration=2.5 },
    @{ Name='02_Home'; Kind='video'; Source='Verification\Evidence\Promo121\Raw\Gameplay01.mp4'; Start=20.2; Duration=2.5 },
    @{ Name='03_Journey'; Kind='video'; Source='Verification\Evidence\Promo121\Raw\JourneyStoryHome.mp4'; Start=20.3; Duration=2.5 },
    @{ Name='04_Story'; Kind='video'; Source='Verification\Evidence\Promo121\Raw\JourneyStoryHome.mp4'; Start=0.5; Duration=2.5 },
    @{ Name='05_LevelStart'; Kind='still'; Source='Verification\Evidence\Promo121\Raw\LevelStartPreview.png'; Start=0; Duration=2.0 },
    @{ Name='06_Rocket'; Kind='video'; Source='Verification\Evidence\Promo121\Raw\Gameplay01.mp4'; Start=1.0; Duration=3.0 },
    @{ Name='07_Hammer'; Kind='video'; Source='Verification\Evidence\ObstacleFall\Touch\Hammer.mp4'; Start=0.2; Duration=3.0 },
    @{ Name='08_Bomb'; Kind='video'; Source='Verification\Evidence\Gameplay79\Android\Touch\MixedBomb.mp4'; Start=0.2; Duration=2.7 },
    @{ Name='09_Orb'; Kind='video'; Source='Verification\Evidence\Gameplay79\Android\Touch\MixedOrb.mp4'; Start=0.2; Duration=2.7 },
    @{ Name='10_Chain'; Kind='video'; Source='Verification\Evidence\Gameplay79\Android\Touch\MixedChain.mp4'; Start=0.2; Duration=2.8 },
    @{ Name='11_EndCard'; Kind='art'; Source='Unity\Assets\HeartOfTheRain\App\Launch\Art\Opening_Key_Art_R1.png'; Start=0; Duration=2.3 }
)

$fit = '[0:v]split=2[bg][fg];[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:2[blur];[fg]scale=1080:1920:force_original_aspect_ratio=decrease[front];[blur][front]overlay=(W-w)/2:(H-h)/2,setsar=1,fps=30,format=yuv420p[v]'
$logo = Join-Path $root 'Unity\Assets\HeartOfTheRain\App\Launch\Art\Title_Logo_R1.png'
$outputFiles = @()
foreach ($shot in $shots) {
    $source = Join-Path $root $shot.Source
    if (-not (Test-Path -LiteralPath $source)) { throw "Missing shot source: $source" }
    $target = Join-Path $work ($shot.Name + '.mp4')
    $duration = $shot.Duration.ToString('0.0', [Globalization.CultureInfo]::InvariantCulture)
    $args = @('-hide_banner','-loglevel','error','-y')
    if ($shot.Kind -eq 'video') {
        $start = $shot.Start.ToString('0.0', [Globalization.CultureInfo]::InvariantCulture)
        $args += @('-ss',$start,'-t',$duration,'-i',$source,'-filter_complex',$fit,'-map','[v]')
    } elseif ($shot.Kind -eq 'still') {
        $args += @('-loop','1','-framerate','30','-t',$duration,'-i',$source,
            '-filter_complex',$fit,'-map','[v]')
    } else {
        $artFilter = "[0:v]scale=1080:1920,zoompan=z='min(zoom+0.0003,1.03)':d=1:s=1080x1920:fps=30[base];[1:v]scale=700:-1,format=rgba,fade=t=in:st=0.2:d=0.55:alpha=1[mark];[base][mark]overlay=(W-w)/2:70:shortest=1,format=yuv420p[v]"
        $args += @('-loop','1','-framerate','30','-t',$duration,'-i',$source,
            '-loop','1','-framerate','30','-t',$duration,'-i',$logo,
            '-filter_complex',$artFilter,'-map','[v]')
    }
    $args += @('-an','-t',$duration,'-r','30','-c:v','libx264','-preset','medium','-crf','19','-pix_fmt','yuv420p',$target)
    & $ffmpeg @args
    if ($LASTEXITCODE -ne 0) { throw "FFmpeg failed on $($shot.Name)" }
    $outputFiles += $target
}

$concat = Join-Path $work 'concat.txt'
$outputFiles | ForEach-Object { "file '$($_.Replace('\','/'))'" } | Set-Content -LiteralPath $concat -Encoding ASCII
$silent = Join-Path $work 'silent.mp4'
$concatArgs = @('-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',$concat,
    '-c:v','libx264','-preset','medium','-crf','19','-r','30','-pix_fmt','yuv420p','-an',$silent)
& $ffmpeg @concatArgs
if ($LASTEXITCODE -ne 0) { throw 'FFmpeg concat failed' }

$music = Join-Path $root 'Unity\Assets\HeartOfTheRain\App\Settings\Audio\Village_Settings_Review_Loop.wav'
$final = Join-Path $PSScriptRoot $OutputName
$audioDir = Join-Path $root 'Unity\Assets\HeartOfTheRain\M47\Audio'
$audioFilter = '[1:a]volume=0.30,atrim=0:28.5,afade=t=in:st=0:d=0.8,afade=t=out:st=27.5:d=1[bg];' +
    '[2:a]volume=0.85,adelay=14400:all=1[rocket];' +
    '[3:a]volume=0.85,adelay=16300:all=1[hammer];' +
    '[4:a]volume=0.75,adelay=19000:all=1[bomb];' +
    '[5:a]volume=0.65,adelay=21800:all=1[orb];' +
    '[6:a]volume=0.70,adelay=24500:all=1[chain];' +
    '[bg][rocket][hammer][bomb][orb][chain]amix=inputs=6:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.85,volume=2,alimiter=limit=0.9[a]'
$muxArgs = @('-hide_banner','-loglevel','error','-y','-i',$silent,
    '-stream_loop','-1','-i',$music,
    '-i',(Join-Path $audioDir 'rocket_launch.wav'),
    '-i',(Join-Path $audioDir 'hammer_hit.wav'),
    '-i',(Join-Path $audioDir 'bomb_blast.wav'),
    '-i',(Join-Path $audioDir 'combo_blast.wav'),
    '-i',(Join-Path $audioDir 'rocket_pass.wav'),
    '-filter_complex',$audioFilter,'-map','0:v:0','-map','[a]',
    '-c:v','copy','-c:a','aac','-b:a','192k',
    '-shortest','-movflags','+faststart',$final)
& $ffmpeg @muxArgs
if ($LASTEXITCODE -ne 0) { throw 'FFmpeg audio mux failed' }
Write-Host "Created $final"
