# GitHub Actions Self-Hosted Runner Cleanup Script
# Repository: mamivani/CREPRO
# Purpose: Safely remove unused Docker self-hosted runners

param(
    [ValidateSet("analyze", "remove-single", "remove-multiple", "list", "status")]
    [string]$Action = "list",
    
    [int[]]$RunnerIds = @(),
    
    [switch]$Force,
    
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

# Configuration
$REPO_OWNER = "mamivani"
$REPO_NAME = "CREPRO"
$API_BASE = "https://api.github.com"

# Color output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Error { Write-Host "ERROR: $args" -ForegroundColor Red }
function Write-Warning { Write-Host "WARNING: $args" -ForegroundColor Yellow }
function Write-Info { Write-Host "INFO: $args" -ForegroundColor Cyan }

# Verify GitHub CLI is available
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Error "GitHub CLI (gh) is not installed or not in PATH"
    exit 1
}

# Verify authentication
Write-Info "Verifying GitHub CLI authentication..."
$authStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "GitHub CLI not authenticated. Run: gh auth login"
    exit 1
}
Write-Success "GitHub CLI authenticated"

# Function: List all runners
function Show-Runners {
    Write-Info "Fetching runners from $REPO_OWNER/$REPO_NAME..."
    
    $runners = gh api -H "Accept: application/vnd.github+json" repos/$REPO_OWNER/$REPO_NAME/actions/runners | ConvertFrom-Json
    
    if ($runners.runners.Count -eq 0) {
        Write-Warning "No runners found"
        return
    }
    
    Write-Success "Found $($runners.runners.Count) runner(s)"
    Write-Host ""
    
    $runners.runners | ForEach-Object {
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        Write-Host "Runner ID: $($_.id)" -ForegroundColor Yellow
        Write-Host "Name:      $($_.name)"
        Write-Host "OS:        $($_.os)"
        $statusMsg = if ($_.status -eq 'online') { 'ONLINE' } else { '⚠️  OFFLINE' }
        Write-Host "Status:    $statusMsg"
        $busyMsg = if ($_.busy) { 'YES' } else { 'NO' }
        Write-Host "Busy:      $busyMsg"
        Write-Host "Version:   $($_.version)"
        Write-Host "Labels:    $($_.labels | ForEach-Object { $_.name } | Join-String -Separator ', ')"
    }
    
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    Write-Host ""
}

# Function: Check runner status
function Show-Status {
    Write-Info "Fetching runner status..."
    
    $runners = gh api -H "Accept: application/vnd.github+json" repos/$REPO_OWNER/$REPO_NAME/actions/runners | ConvertFrom-Json
    
    $stats = @{
        Total = $runners.runners.Count
        Online = ($runners.runners | Where-Object { $_.status -eq 'online' }).Count
        Offline = ($runners.runners | Where-Object { $_.status -eq 'offline' }).Count
        Busy = ($runners.runners | Where-Object { $_.busy }).Count
        Idle = ($runners.runners | Where-Object { -not $_.busy }).Count
    }
    
    Write-Host ""
    Write-Host "╔════════════════════════════════════╗"
    Write-Host "║  Runner Status Summary             ║"
    Write-Host "╠════════════════════════════════════╣"
    Write-Host "║ Total Runners:    $($stats.Total)                    ║"
    Write-Host "║ Online:           $($stats.Online)                    ║"
    Write-Host "║ Offline:          $($stats.Offline)                    ║"
    Write-Host "║ Currently Busy:   $($stats.Busy)                    ║"
    Write-Host "║ Idle:             $($stats.Idle)                    ║"
    Write-Host "╚════════════════════════════════════╝"
    Write-Host ""
    
    if ($stats.Offline -gt 0) {
        Write-Warning "$($stats.Offline) offline runner(s) detected - consider cleanup"
    }
}

# Function: Analyze runner usage
function Analyze-Usage {
    Write-Info "Analyzing runner usage from recent jobs..."
    
    $runners = gh api -H "Accept: application/vnd.github+json" repos/$REPO_OWNER/$REPO_NAME/actions/runners | ConvertFrom-Json
    $runnerMap = @{}
    $runners.runners | ForEach-Object { $runnerMap[$_.id] = $_.name }
    
    # Get recent jobs
    $jobs = gh api -H "Accept: application/vnd.github+json" repos/$REPO_OWNER/$REPO_NAME/actions/jobs?per_page=50 | ConvertFrom-Json
    
    $usage = @{}
    $jobs.jobs | Where-Object { $_.runner_name } | ForEach-Object {
        if (-not $usage[$_.runner_name]) {
            $usage[$_.runner_name] = 0
        }
        $usage[$_.runner_name] += 1
    }
    
    Write-Host ""
    Write-Host "╔═══════════════════════════════════════╗"
    Write-Host "║  Runner Usage Analysis (Last 50 Jobs) ║"
    Write-Host "╠═══════════════════════════════════════╣"
    
    $total = ($usage.Values | Measure-Object -Sum).Sum
    $usage.GetEnumerator() | Sort-Object Value -Descending | ForEach-Object {
        $percentage = [math]::Round(($_.Value / $total) * 100, 1)
        $runnerStatus = if ($runners.runners | Where-Object { $_.name -eq $_.Key -and $_.status -eq 'offline' }) { 
            " (⚠️  OFFLINE)" 
        } else { 
            "" 
        }
        Write-Host "║ $($_.Key): $($_.Value) jobs ($percentage%)$runnerStatus"
    }
    
    Write-Host "║ Total Jobs: $total"
    Write-Host "╚═══════════════════════════════════════╝"
    Write-Host ""
}

# Function: Remove single runner
function Remove-Runner {
    param([int]$RunnerId)
    
    Write-Warning "Preparing to remove runner ID $RunnerId"
    
    # Get runner details
    $runner = gh api -H "Accept: application/vnd.github+json" repos/$REPO_OWNER/$REPO_NAME/actions/runners/$RunnerId 2>&1 | ConvertFrom-Json
    
    if (-not $runner.id) {
        Write-Error "Runner $RunnerId not found"
        return $false
    }
    
    Write-Host ""
    Write-Host "Runner Details:"
    Write-Host "  Name:   $($runner.name)"
    Write-Host "  Status: $($runner.status)"
    Write-Host "  Busy:   $($runner.busy)"
    Write-Host ""
    
    if ($runner.busy -and -not $Force) {
        Write-Error "Runner is currently busy. Use -Force to remove anyway."
        return $false
    }
    
    if ($runner.busy) {
        Write-Warning "Runner is currently busy but -Force flag used, proceeding with removal"
    }
    
    # Confirmation
    if (-not $Force) {
        Write-Host ""
        $confirm = Read-Host "Remove runner '$($runner.name)' (ID: $RunnerId)? [yes/no]"
        if ($confirm -ne "yes") {
            Write-Info "Removal cancelled"
            return $false
        }
    }
    
    # Perform removal
    if ($DryRun) {
        Write-Info "DRY RUN: Would execute: gh api repos/$REPO_OWNER/$REPO_NAME/actions/runners/$RunnerId -X DELETE"
        return $true
    }
    
    Write-Info "Removing runner $RunnerId..."
    $result = gh api -H "Accept: application/vnd.github+json" repos/$REPO_OWNER/$REPO_NAME/actions/runners/$RunnerId -X DELETE 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Successfully removed runner $RunnerId"
        Write-Info "Wait 30 seconds for GitHub to update, then verify with: ./cleanup-runners.ps1 -Action list"
        return $true
    }
    else {
        Write-Error "Failed to remove runner $RunnerId"
        Write-Error "$result"
        return $false
    }
}

# Function: Remove multiple runners
function Remove-MultipleRunners {
    param([int[]]$Ids)
    
    if ($Ids.Count -eq 0) {
        Write-Error "No runner IDs specified"
        return
    }
    
    Write-Warning "Preparing to remove $($Ids.Count) runner(s)"
    Write-Host ""
    
    $Ids | ForEach-Object {
        $runner = gh api -H "Accept: application/vnd.github+json" repos/$REPO_OWNER/$REPO_NAME/actions/runners/$_ 2>&1 | ConvertFrom-Json
        if ($runner.id) {
            Write-Host "  - Runner $($_): $($runner.name) (Status: $($runner.status))"
        }
    }
    
    Write-Host ""
    
    if (-not $Force) {
        $confirm = Read-Host "Remove these $($Ids.Count) runner(s)? [yes/no]"
        if ($confirm -ne "yes") {
            Write-Info "Removal cancelled"
            return
        }
    }
    
    $successCount = 0
    $Ids | ForEach-Object {
        if (Remove-Runner -RunnerId $_) {
            $successCount++
        }
    }
    
    Write-Success "Removed $successCount / $($Ids.Count) runner(s)"
}

# Main execution
try {
    switch ($Action) {
        "list" {
            Show-Runners
        }
        "status" {
            Show-Status
        }
        "analyze" {
            Analyze-Usage
        }
        "remove-single" {
            if ($RunnerIds.Count -ne 1) {
                Write-Error "Specify exactly one runner ID with -RunnerIds parameter"
                exit 1
            }
            Remove-Runner -RunnerId $RunnerIds[0]
        }
        "remove-multiple" {
            Remove-MultipleRunners -Ids $RunnerIds
        }
        default {
            Write-Error "Unknown action: $Action"
            exit 1
        }
    }
}
catch {
    Write-Error $_
    exit 1
}
