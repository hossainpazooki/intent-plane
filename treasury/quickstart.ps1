# Intent-plane quickstart: boots the real scorer + real gate with treasury
# facts, then runs a self-asserting probe ladder. ASCII output only.
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$scorerPort = 8000; $gatePort = 8080
$scorerUrl = "http://127.0.0.1:$scorerPort/ml/evaluate"
$gateUrl = "http://127.0.0.1:$gatePort"

# Fail fast on an occupied port: health-checking into someone else's process
# would score probes against a service this script does not own.
function Test-PortInUse($port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try { $client.Connect("127.0.0.1", $port); return $true }
    catch { return $false }
    finally { $client.Dispose() }
}
foreach ($p in @($scorerPort, $gatePort)) {
    if (Test-PortInUse $p) {
        Write-Host "[error] port $p is already in use - refusing to boot into another process"
        exit 1
    }
}

$dataDir = Join-Path ([System.IO.Path]::GetTempPath()) ("intent-plane-quickstart-" + [guid]::NewGuid().ToString("N").Substring(0,8))
New-Item -ItemType Directory -Path $dataDir | Out-Null

$scorer = $null; $gate = $null
$pass = 0; $fail = 0
try {
    $venvPy = Join-Path $repo "core\scorer\.venv\Scripts\python.exe"
    if (-not (Test-Path $venvPy)) {
        Write-Host "[setup] creating scorer venv (one-time)"
        python -m venv (Join-Path $repo "core\scorer\.venv")
        & $venvPy -m pip install -q -e ((Join-Path $repo "core\scorer") + "[dev]")
    }

    Write-Host "[boot] scorer with treasury facts (balance=250, fx_rate=1.30)"
    $env:SCORER_FACTS_JSON = Get-Content (Join-Path $PSScriptRoot "facts.json") -Raw
    $env:SCORER_PORT = "$scorerPort"
    $scorer = Start-Process -FilePath $venvPy -ArgumentList "-m", "scorer" -WorkingDirectory (Join-Path $repo "core\scorer") -PassThru -WindowStyle Hidden

    Write-Host "[boot] building and starting the gate"
    & go build -o (Join-Path $repo "bin\intent-gate.exe") "$repo\core\cmd\server"
    # A failing NATIVE command does not halt under -File even with
    # ErrorActionPreference=Stop, so a broken build would silently probe the
    # stale gitignored binary and report a false green. The sh twin gets this
    # from set -e.
    if ($LASTEXITCODE -ne 0) { throw "go build failed" }
    $env:INTENT_SCORER_URL = $scorerUrl
    $env:INTENT_DATA_DIR = $dataDir
    $env:INTENT_ADDR = ":$gatePort"
    $gate = Start-Process -FilePath (Join-Path $repo "bin\intent-gate.exe") -PassThru -WindowStyle Hidden

    function Wait-Healthy($url) {
        foreach ($i in 1..50) {
            try { if ((Invoke-WebRequest -Uri "$url/healthz" -UseBasicParsing -TimeoutSec 1).StatusCode -eq 200) { return } } catch { Start-Sleep -Milliseconds 200 }
        }
        throw "service at $url never became healthy"
    }
    Wait-Healthy "http://127.0.0.1:$scorerPort"
    Wait-Healthy $gateUrl

    # $wantReasonReject is the discriminating guard: a reason may be REQUIRED to
    # contain one substring and REFUSED for containing another, so that a
    # fail-closed "unevaluable:<name>" can never satisfy a "criterion bound" probe.
    function Probe($name, $file, $wantTerminal, $wantReasonPart, $why, $wantReasonReject = "") {
        $body = Get-Content (Join-Path $PSScriptRoot "probes\$file") -Raw
        $r = Invoke-RestMethod -Uri "$gateUrl/v2/intents" -Method Post -Body $body -ContentType "application/json"
        $ok = ($r.terminal -eq $wantTerminal) -and ($wantReasonPart -eq "" -or $r.reason -like "*$wantReasonPart*") -and ($wantReasonReject -eq "" -or $r.reason -notlike "*$wantReasonReject*")
        if ($ok) { $script:pass++; $tag = "PASS" } else { $script:fail++; $tag = "FAIL" }
        Write-Host ("[{0}] {1}: terminal={2} reason={3}" -f $tag, $name, $r.terminal, $r.reason)
        Write-Host ("       why it matters: {0}" -f $why)
    }

    Probe "declare within limits" "01-declare-pass.json" "ACHIEVED" "" "the full lifecycle runs against real scored facts; exactly one durable ACHIEVED record exists"
    Probe "near-duplicate, same key" "02-near-duplicate.json" "FAILED_AT_DISPATCH" "idempotency-collision" "at-most-once holds by construction: the declared key collides, value cannot move twice"
    Probe "over threshold" "03-over-threshold.json" "FAILED" "balance" "criteria actually bind - the refusal names the failing criterion, and NOT because it was unevaluable" "unevaluable"

    Write-Host "[chaos] killing the scorer to prove fail-closed on outage"
    Stop-Process -Id $scorer.Id -Force
    Start-Sleep -Milliseconds 500
    Probe "declare during scorer outage" "04-outage.json" "FAILED" "unevaluable" "an unreachable scorer denies - unevaluable NEVER collapses into a pass"
    Probe "empty criteria" "05-empty-criteria.json" "FAILED" "unevaluable:empty-criteria" "thin-spec defense - 'no criterion failed' is never satisfied by 'no criterion existed'"

    $events = Invoke-RestMethod -Uri "$gateUrl/v2/events?since=0"
    $achieved = @($events.events | Where-Object { $_.type -eq "ACHIEVED" })
    if ($achieved.Count -eq 1) { $pass++; Write-Host "[PASS] durable feed: exactly 1 ACHIEVED record among $($events.events.Count) events (cursor next_since=$($events.next_since))" }
    else { $fail++; Write-Host "[FAIL] durable feed: expected exactly 1 ACHIEVED, got $($achieved.Count)" }
    Write-Host "       why it matters: consumers settle only from this observable feed - emit-and-observe"

    Write-Host ("RESULT: {0}/6 probes passed" -f $pass)
}
finally {
    # Reclaim on EVERY exit path - a Wait-Healthy timeout or a transport throw
    # must not leak a gate holding :8080 and poison the next run.
    if ($scorer -and -not $scorer.HasExited) { Stop-Process -Id $scorer.Id -Force -ErrorAction SilentlyContinue }
    if ($gate) {
        Stop-Process -Id $gate.Id -Force -ErrorAction SilentlyContinue
        # Windows releases the gate's open file handles only once the process is
        # fully reaped, so wait before unlinking; a stray temp dir must never
        # mask the result.
        $gate.WaitForExit(5000) | Out-Null
    }
    Remove-Item -Recurse -Force $dataDir -ErrorAction SilentlyContinue
}
if ($fail -gt 0) { exit 1 }
