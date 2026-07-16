<#
.SYNOPSIS
    setup-and-run.ps1 — One script to set up and launch the SSL Certificate
    Analytics Dashboard on Windows.

.DESCRIPTION
    Mirrors setup-and-run.sh phase-for-phase:
      1. Checks python, node, npm, mongod, mongorestore are installed
      2. Makes sure MongoDB is actually running
      3. Creates/activates a Python venv and installs backend requirements
      4. Checks whether the required MongoDB databases already exist
      5. If not, downloads the dataset from Hugging Face and restores it
      6. Installs frontend dependencies
      7. Starts backend (Django) and frontend (Next.js) together

.NOTES
    Run from PowerShell:  .\setup-and-run.ps1
    If you get an execution-policy error, run instead:
        powershell -ExecutionPolicy Bypass -File .\setup-and-run.ps1
    Press Ctrl+C at any time while both servers are running to stop them.
#>

# Allow this script to run even if the system's execution policy would
# otherwise block it — scoped to this process only, doesn't touch any
# system-wide setting.
if ((Get-ExecutionPolicy -Scope Process) -eq 'Restricted') {
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
}

$ErrorActionPreference = 'Stop'

# ----------------------------------------------------------------------
# Config — adjust these if your project layout / ports differ
# ----------------------------------------------------------------------
$ScriptDir    = $PSScriptRoot
$ProjectRoot  = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path   # dashboard\scripts -> dashboard -> project root
Set-Location $ProjectRoot

$BackendDir   = Join-Path $ProjectRoot "dashboard\backend"
$FrontendDir  = Join-Path $ProjectRoot "dashboard\frontend"
$ConfigFile   = Join-Path $ProjectRoot "project-config.json"
$DatasetDir   = Join-Path $ProjectRoot "dataset"
$VenvDir      = Join-Path $ProjectRoot "venv"

$BackendPort  = 8000
$FrontendPort = 3000

$MainArchive    = "hugging-face-700k.archive.gz"
$ResultsArchive = "hugging-face-700k-results.archive.gz"
$HfBaseUrl      = "https://huggingface.co/datasets/EbadJunaid/hugging-face-700k-ssl-certificates-data/resolve/main"

$DefaultMongoUri   = "mongodb://localhost:27017"
$DefaultMainDb     = "hugging-face-700k"
$DefaultResultsDb  = "hugging-face-700k-results"

# ----------------------------------------------------------------------
# Pretty printing helpers
# ----------------------------------------------------------------------
function Write-Info    { param($m) Write-Host "-> $m" -ForegroundColor Cyan }
function Write-Success { param($m) Write-Host "OK  $m" -ForegroundColor Green }
function Write-Warn    { param($m) Write-Host "!!  $m" -ForegroundColor Yellow }
function Write-ErrMsg  { param($m) Write-Host "XX  $m" -ForegroundColor Red }
function Write-Phase   { param($m) Write-Host "`n== $m ==" -ForegroundColor White }

function Test-CommandExists {
    param([string]$Command)
    return [bool](Get-Command $Command -ErrorAction SilentlyContinue)
}

function Test-PortOpen {
    param([string]$HostName, [int]$Port)
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $async  = $client.BeginConnect($HostName, $Port, $null, $null)
        $ok     = $async.AsyncWaitHandle.WaitOne(1000, $false) -and $client.Connected
        $client.Close()
        return $ok
    } catch {
        return $false
    }
}

$WingetAvailable = Test-CommandExists "winget"

function Get-InstallHint {
    param([string]$Tool)
    switch ($Tool) {
        "python" {
            if ($WingetAvailable) { return "winget install -e --id Python.Python.3.12" }
            return "https://www.python.org/downloads/"
        }
        "node" {
            if ($WingetAvailable) { return "winget install -e --id OpenJS.NodeJS.LTS" }
            return "https://nodejs.org/"
        }
        "mongodb" {
            if ($WingetAvailable) { return "winget install -e --id MongoDB.Server ; winget install -e --id MongoDB.DatabaseTools" }
            return "https://www.mongodb.com/try/download/community  and  https://www.mongodb.com/try/download/database-tools"
        }
    }
}

# ========================================================================
# PHASE 1 — Prerequisites
# ========================================================================
Write-Phase "Phase 1/7 -- Checking prerequisites"

$Missing = $false

if (Test-CommandExists "python") {
    $pyver = (python --version) 2>&1
    Write-Success "python found ($pyver)"
} else {
    Write-ErrMsg "python not found."
    Write-Host "   Install with: $(Get-InstallHint python)"
    $Missing = $true
}

if ((Test-CommandExists "node") -and (Test-CommandExists "npm")) {
    Write-Success "node + npm found (node $(node --version), npm $(npm --version))"
} else {
    Write-ErrMsg "node/npm not found."
    Write-Host "   Install with: $(Get-InstallHint node)"
    $Missing = $true
}

if (Test-CommandExists "mongod") {
    Write-Success "mongod found"
} else {
    Write-ErrMsg "mongod not found."
    Write-Host "   Install with: $(Get-InstallHint mongodb)"
    $Missing = $true
}

if (Test-CommandExists "mongorestore") {
    Write-Success "mongorestore found"
} else {
    Write-ErrMsg "mongorestore (MongoDB Database Tools) not found."
    Write-Host "   Install with: $(Get-InstallHint mongodb)"
    $Missing = $true
}

# Redis is optional — never block on it.
if (Test-CommandExists "redis-cli") {
    $pong = (redis-cli ping) 2>$null
    if ($pong -eq "PONG") {
        Write-Success "Redis is running (optional caching enabled)"
    } else {
        Write-Warn "Redis is installed but not running."
        Write-Host "   Windows doesn't have a single standard Redis service name; start it manually"
        Write-Host "   (e.g. via Memurai, the Redis Windows service, or WSL) if you want caching."
    }
} else {
    Write-Warn "Redis not installed -- dashboard will run fine without it (no caching)."
}

if ($Missing) {
    Write-Host ""
    Write-ErrMsg "One or more required tools are missing. Install them and re-run this script."
    exit 1
}

# Make sure MongoDB is actually running, not just installed.
if (Test-PortOpen "127.0.0.1" 27017) {
    Write-Success "MongoDB is running on localhost:27017"
} else {
    Write-Warn "MongoDB does not appear to be running. Attempting to start it..."
    try {
        Start-Service -Name "MongoDB" -ErrorAction Stop
    } catch {
        Write-Warn "Could not start the 'MongoDB' Windows service (it may be named differently, or not installed as a service)."
    }
    Start-Sleep -Seconds 3
    if (Test-PortOpen "127.0.0.1" 27017) {
        Write-Success "MongoDB started successfully."
    } else {
        Write-ErrMsg "Could not start MongoDB automatically."
        Write-Host "   Start it manually, then re-run this script. Examples:"
        Write-Host "     Start-Service MongoDB     (if installed as a Windows service)"
        Write-Host "     Or launch mongod.exe directly with your data path."
        exit 1
    }
}

# ========================================================================
# PHASE 2 — Python venv + backend dependencies
# ========================================================================
Write-Phase "Phase 2/7 -- Setting up Python environment"

if (-not (Test-Path $BackendDir)) {
    Write-ErrMsg "Backend directory not found at: $BackendDir"
    Write-Host "   Run this script from dashboard\scripts in the project."
    exit 1
}

if (-not (Test-Path $VenvDir)) {
    Write-Info "Creating virtual environment..."
    python -m venv $VenvDir
} else {
    Write-Info "Virtual environment already exists, reusing it."
}

$ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
. $ActivateScript

Write-Info "Installing backend Python dependencies (this can take a minute)..."
pip install --quiet --upgrade pip
pip install --quiet -r (Join-Path $BackendDir "requirements.txt")
Write-Success "Python dependencies installed."

# ========================================================================
# PHASE 3 — Check whether the MongoDB databases already exist
# ========================================================================
Write-Phase "Phase 3/7 -- Checking dataset status in MongoDB"

$PyCheckScript = @'
import json, sys
from pymongo import MongoClient
from pymongo.errors import PyMongoError

config_path, default_uri, default_main, default_results = sys.argv[1:5]

# Which "databases" entry to use — matches the dataset this script downloads.
DATASET_ID = "hugging-face-700k"

uri, main_db, results_db = default_uri, default_main, default_results
try:
    with open(config_path) as f:
        cfg = json.load(f)

    uri = cfg.get("mongo_uri", uri)

    entry = None
    for candidate in cfg.get("databases", []):
        if candidate.get("id") == DATASET_ID:
            entry = candidate
            break
    if entry is None and cfg.get("databases"):
        entry = cfg["databases"][0]

    if entry:
        main_db = entry.get("main", main_db)
        results_db = entry.get("results", results_db)
except FileNotFoundError:
    pass
except Exception:
    pass

missing = []
try:
    client = MongoClient(uri, serverSelectionTimeoutMS=3000)
    existing = client.list_database_names()
    if main_db not in existing:
        missing.append("main")
    if results_db not in existing:
        missing.append("results")
except PyMongoError:
    missing.append("main")
    missing.append("results")

if missing:
    print(",".join(missing))
else:
    print("READY")
'@

$DatasetCheck = ($PyCheckScript | python - $ConfigFile $DefaultMongoUri $DefaultMainDb $DefaultResultsDb).Trim()

$NeedMain = $false
$NeedResults = $false

if ($DatasetCheck -eq "READY") {
    Write-Success "Both required databases already exist -- skipping dataset download."
} else {
    Write-Warn "Some datasets not found in MongoDB."
    if ($DatasetCheck -match "main")    { $NeedMain = $true }
    if ($DatasetCheck -match "results") { $NeedResults = $true }
    if ($NeedMain)    { Write-Info "Main database ($DefaultMainDb) missing." }
    if ($NeedResults) { Write-Info "Analytics database ($DefaultResultsDb) missing." }

    # ====================================================================
    # PHASE 4 — Download dataset + mongorestore
    # ====================================================================
    Write-Phase "Phase 4/7 -- Downloading and restoring dataset"

    New-Item -ItemType Directory -Force -Path $DatasetDir | Out-Null
    Set-Location $DatasetDir

    function Get-FileWithProgress {
        param([string]$Url, [string]$OutFile)

        if (Test-Path $OutFile) {
            Write-Info "$OutFile already downloaded, skipping."
            return
        }
        Write-Info "Downloading $OutFile ..."

        $webClient = New-Object System.Net.WebClient
        $state = [hashtable]::Synchronized(@{ Done = $false; HadError = $false })

        $progressSub = Register-ObjectEvent -InputObject $webClient -EventName DownloadProgressChanged -Action {
            $recv  = [math]::Round($EventArgs.BytesReceived / 1MB, 1)
            $total = [math]::Round($EventArgs.TotalBytesToReceive / 1MB, 1)
            if ($EventArgs.TotalBytesToReceive -gt 0) {
                Write-Host -NoNewline ("`r    {0} MB / {1} MB  ({2}%)   " -f $recv, $total, $EventArgs.ProgressPercentage)
            } else {
                Write-Host -NoNewline ("`r    {0} MB downloaded...   " -f $recv)
            }
        }

        $completeSub = Register-ObjectEvent -InputObject $webClient -EventName DownloadFileCompleted -Action {
            $Event.MessageData.Done = $true
            if ($EventArgs.Error) { $Event.MessageData.HadError = $true }
        } -MessageData $state

        $webClient.DownloadFileAsync([Uri]$Url, $OutFile)

        while (-not $state.Done) {
            Start-Sleep -Milliseconds 300
        }
        Write-Host ""

        Unregister-Event -SourceIdentifier $progressSub.Name -ErrorAction SilentlyContinue
        Unregister-Event -SourceIdentifier $completeSub.Name -ErrorAction SilentlyContinue
        $webClient.Dispose()

        if ($state.HadError -or -not (Test-Path $OutFile)) {
            Write-ErrMsg "Download of $OutFile failed."
            exit 1
        }
        $sizeMB = [math]::Round((Get-Item $OutFile).Length / 1MB, 1)
        Write-Success "$OutFile downloaded ($sizeMB MB)."
    }

    if ($NeedMain) {
        Get-FileWithProgress -Url "$HfBaseUrl/$MainArchive" -OutFile $MainArchive
        Write-Info "Restoring main certificate database..."
        mongorestore --archive="$MainArchive" --gzip
        Write-Success "Main dataset restored."
    } else {
        Write-Info "Main database already exists -- skipping."
    }

    if ($NeedResults) {
        Get-FileWithProgress -Url "$HfBaseUrl/$ResultsArchive" -OutFile $ResultsArchive
        Write-Info "Restoring pre-computed analytics database..."
        mongorestore --archive="$ResultsArchive" --gzip
        Write-Success "Analytics dataset restored."
    } else {
        Write-Info "Analytics database already exists -- skipping."
    }

    if ($NeedMain -or $NeedResults) {
        $Reply = Read-Host "Delete downloaded archive files to save disk space? [Y/n]"
        if ("$Reply" -notmatch '^[Nn]') {
            if ($NeedMain)    { Remove-Item -Force $MainArchive -ErrorAction SilentlyContinue }
            if ($NeedResults) { Remove-Item -Force $ResultsArchive -ErrorAction SilentlyContinue }
            Write-Success "Archive files deleted."
        } else {
            Write-Info "Archive files kept in $DatasetDir"
        }
    }

    Set-Location $ProjectRoot
}

# ========================================================================
# PHASE 5 — Frontend dependencies
# ========================================================================
Write-Phase "Phase 5/7 -- Installing frontend dependencies"

if (-not (Test-Path $FrontendDir)) {
    Write-ErrMsg "Frontend directory not found at: $FrontendDir"
    exit 1
}

Set-Location $FrontendDir
if (Test-Path "node_modules") {
    Write-Info "node_modules already present, skipping npm install."
} else {
    npm install
}
Write-Success "Frontend dependencies ready."
Set-Location $ProjectRoot

# ========================================================================
# PHASE 6 — Start both servers
# ========================================================================
Write-Phase "Phase 6/7 -- Starting servers"

if (Test-PortOpen "127.0.0.1" $BackendPort) {
    Write-ErrMsg "Port $BackendPort is already in use -- backend can't start."
    Write-Host "   Either free the port, or run the backend on another port manually:"
    Write-Host "     1. cd dashboard\backend; python manage.py runserver 8001"
    Write-Host "     2. Set NEXT_PUBLIC_API_URL=http://localhost:8001/api in frontend\.env.local"
    Write-Host "     3. Add http://localhost:8001 to CORS_ALLOWED_ORIGINS in backend\ssl_dashboard\settings.py"
    exit 1
}

if (Test-PortOpen "127.0.0.1" $FrontendPort) {
    Write-ErrMsg "Port $FrontendPort is already in use -- frontend can't start."
    Write-Host "   Either free the port, or run the frontend on another port manually:"
    Write-Host "     1. cd dashboard\frontend; npm run dev -- -p 3001"
    Write-Host "     2. Add http://localhost:3001 to CORS_ALLOWED_ORIGINS in backend\ssl_dashboard\settings.py"
    exit 1
}

$BackendProcess  = $null
$FrontendProcess = $null

# Kills the entire process tree, not just the top-level process — needed
# because both `python manage.py runserver` (its auto-reloader) and
# `npm run dev` (npm -> node -> next) spawn child processes that a plain
# Stop-Process would leave orphaned and still holding the port.
function Stop-ProcessTree {
    param($Process)
    if ($Process -and -not $Process.HasExited) {
        try { taskkill /PID $Process.Id /T /F | Out-Null } catch {}
    }
}

try {
    Set-Location $BackendDir
    Write-Info "Applying Django migrations..."
    python manage.py migrate --noinput

    Write-Info "Starting backend on port $BackendPort..."
    $BackendProcess = Start-Process -FilePath "python" `
        -ArgumentList "manage.py runserver $BackendPort" `
        -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $ProjectRoot "backend.log") `
        -RedirectStandardError  (Join-Path $ProjectRoot "backend.err.log")

    Set-Location $FrontendDir
    Write-Info "Starting frontend on port $FrontendPort..."
    # Wrapped in cmd.exe /c so npm.cmd resolves correctly under Start-Process.
    $FrontendProcess = Start-Process -FilePath "cmd.exe" `
        -ArgumentList "/c npm run dev -- -p $FrontendPort" `
        -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $ProjectRoot "frontend.log") `
        -RedirectStandardError  (Join-Path $ProjectRoot "frontend.err.log")

    Set-Location $ProjectRoot

    # ====================================================================
    # PHASE 7 — Done
    # ====================================================================
    Start-Sleep -Seconds 2
    Write-Phase "Phase 7/7 -- Dashboard is running"
    Write-Host "  Backend:   http://localhost:$BackendPort" -ForegroundColor Green
    Write-Host "  Frontend:  http://localhost:$FrontendPort" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Press Ctrl+C to stop both servers."
    Write-Host ""

    while ($true) {
        Start-Sleep -Seconds 1
        if ($BackendProcess.HasExited -or $FrontendProcess.HasExited) {
            Write-ErrMsg "One of the servers exited unexpectedly. Check backend.log / frontend.log in the project root."
            break
        }
    }
}
finally {
    Write-Host ""
    Write-Info "Shutting down servers..."
    Stop-ProcessTree $BackendProcess
    Stop-ProcessTree $FrontendProcess
    Write-Success "Both servers stopped. Bye!"
}