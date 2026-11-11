# Docker Container & Image Cleanup Script
# Purpose: Safely manage Docker disk space and remove unused containers/images

param(
    [ValidateSet("status", "analyze", "cleanup-containers", "cleanup-images", "cleanup-volumes", "cleanup-cache", "cleanup-all", "aggressive-cleanup", "interactive")]
    [string]$Action = "status",
    
    [switch]$Force,
    [switch]$DryRun,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

# Color functions
function Write-Success { if (-not $Quiet) { Write-Host $args -ForegroundColor Green } }
function Write-Warning { if (-not $Quiet) { Write-Host "⚠️  WARNING: $args" -ForegroundColor Yellow } }
function Write-Error { Write-Host "❌ ERROR: $args" -ForegroundColor Red }
function Write-Info { if (-not $Quiet) { Write-Host "ℹ️  INFO: $args" -ForegroundColor Cyan } }
function Write-Header { if (-not $Quiet) { Write-Host "`n╔════════════════════════════════════════════╗" -ForegroundColor Cyan; Write-Host "║ $args" -ForegroundColor Cyan; Write-Host "╚════════════════════════════════════════════╝`n" -ForegroundColor Cyan } }

# Check Docker is available
function Test-Docker {
    try {
        $null = docker version 2>&1
        return $true
    }
    catch {
        Write-Error "Docker is not installed or not running"
        return $false
    }
}

# Show current status
function Show-Status {
    Write-Header "Docker Disk Usage Status"
    
    try {
        docker system df
        Write-Host ""
    }
    catch {
        Write-Error "Failed to retrieve Docker disk usage: $_"
    }
}

# Analyze system
function Analyze-System {
    Write-Header "Docker System Analysis"
    
    try {
        # Container analysis
        $containers = docker ps -a --format "{{.Status}}"
        $running = $containers | Where-Object { $_ -match "^Up" } | Measure-Object | Select-Object -ExpandProperty Count
        $stopped = $containers | Where-Object { $_ -match "^(Exited|Created|Removing)" } | Measure-Object | Select-Object -ExpandProperty Count
        $total = $containers | Measure-Object | Select-Object -ExpandProperty Count
        
        Write-Host "📦 CONTAINERS"
        Write-Host "  Total: $total"
        Write-Host "  Running: $running"
        Write-Host "  Stopped/Unused: $stopped"
        Write-Host ""
        
        # Image analysis
        $images = docker images --format "{{.ID}}"
        $imageCount = $images | Measure-Object | Select-Object -ExpandProperty Count
        $danglingImages = docker images -f dangling=true --format "{{.ID}}" | Measure-Object | Select-Object -ExpandProperty Count
        
        Write-Host "🖼️  IMAGES"
        Write-Host "  Total: $imageCount"
        Write-Host "  Dangling: $danglingImages"
        Write-Host ""
        
        # Volume analysis
        $volumes = docker volume ls --format "{{.Name}}"
        $volumeCount = $volumes | Measure-Object | Select-Object -ExpandProperty Count
        $danglingVolumes = docker volume ls -f dangling=true --format "{{.Name}}" | Measure-Object | Select-Object -ExpandProperty Count
        
        Write-Host "💾 VOLUMES"
        Write-Host "  Total: $volumeCount"
        Write-Host "  Unused: $danglingVolumes"
        Write-Host ""
        
        # Show detailed disk usage
        Write-Host "📊 DETAILED DISK USAGE"
        docker system df -v | Select-Object -First 20
        
    }
    catch {
        Write-Error "Analysis failed: $_"
    }
}

# Cleanup containers
function Cleanup-Containers {
    Write-Header "Container Cleanup"
    
    if ($DryRun) {
        Write-Info "DRY RUN MODE - No changes will be made"
    }
    
    try {
        Write-Info "Removing stopped containers..."
        
        if ($DryRun) {
            $count = docker ps -a --filter "status=created" --format "{{.ID}}" | Measure-Object | Select-Object -ExpandProperty Count
            $count += docker ps -a --filter "status=exited" --format "{{.ID}}" | Measure-Object | Select-Object -ExpandProperty Count
            Write-Info "Would remove $count container(s)"
        }
        else {
            $output = docker container prune -f 2>&1
            Write-Success "Containers cleaned"
            Write-Host $output
        }
    }
    catch {
        Write-Error "Container cleanup failed: $_"
    }
}

# Cleanup images
function Cleanup-Images {
    param(
        [ValidateSet("dangling", "all")]
        [string]$Type = "dangling"
    )
    
    Write-Header "Image Cleanup"
    
    if ($DryRun) {
        Write-Info "DRY RUN MODE - No changes will be made"
    }
    
    try {
        if ($Type -eq "dangling") {
            Write-Info "Removing dangling images (orphaned layers)..."
            
            if ($DryRun) {
                $count = docker images -f dangling=true --format "{{.ID}}" | Measure-Object | Select-Object -ExpandProperty Count
                Write-Info "Would remove $count dangling image(s)"
            }
            else {
                $output = docker image prune -f 2>&1
                Write-Success "Dangling images cleaned"
                Write-Host $output
            }
        }
        else {
            Write-Info "Removing ALL unused images..."
            Write-Warning "This will remove images not used by running containers"
            
            if (-not $Force) {
                $confirm = Read-Host "Continue? [yes/no]"
                if ($confirm -ne "yes") {
                    Write-Info "Cancelled"
                    return
                }
            }
            
            if ($DryRun) {
                $count = docker images --format "{{.ID}}" | Measure-Object | Select-Object -ExpandProperty Count
                Write-Info "System has $count total image(s), would analyze which to remove"
            }
            else {
                $output = docker image prune -a -f 2>&1
                Write-Success "Unused images cleaned"
                Write-Host $output
            }
        }
    }
    catch {
        Write-Error "Image cleanup failed: $_"
    }
}

# Cleanup volumes
function Cleanup-Volumes {
    Write-Header "Volume Cleanup"
    
    if ($DryRun) {
        Write-Info "DRY RUN MODE - No changes will be made"
    }
    
    try {
        Write-Info "Removing unused volumes..."
        
        if ($DryRun) {
            $count = docker volume ls -f dangling=true --format "{{.Name}}" | Measure-Object | Select-Object -ExpandProperty Count
            Write-Info "Would remove $count unused volume(s)"
        }
        else {
            $output = docker volume prune -f 2>&1
            Write-Success "Unused volumes cleaned"
            Write-Host $output
        }
    }
    catch {
        Write-Error "Volume cleanup failed: $_"
    }
}

# Cleanup build cache
function Cleanup-Cache {
    Write-Header "Build Cache Cleanup"
    
    if ($DryRun) {
        Write-Info "DRY RUN MODE - No changes will be made"
    }
    
    try {
        Write-Info "Removing build cache..."
        
        if ($DryRun) {
            $info = docker system df
            Write-Info "Would clear BuildKit cache (see 'Build Cache' row above)"
        }
        else {
            $output = docker builder prune -a -f 2>&1
            Write-Success "Build cache cleaned"
            Write-Host $output
        }
    }
    catch {
        Write-Error "Cache cleanup failed: $_"
    }
}

# Conservative cleanup
function Cleanup-Conservative {
    Write-Header "Conservative Cleanup (RECOMMENDED)"
    
    Write-Info "This will remove:"
    Write-Info "  ✓ Stopped containers"
    Write-Info "  ✓ Dangling images"
    Write-Info "  ✓ Unused volumes"
    Write-Host ""
    
    if ($DryRun) {
        Write-Info "DRY RUN - simulating cleanup"
    }
    else {
        Write-Info "Starting cleanup..."
    }
    
    Cleanup-Containers
    Cleanup-Images -Type dangling
    Cleanup-Volumes
    
    if (-not $DryRun) {
        Write-Success "Conservative cleanup complete"
        Show-Status
    }
}

# Aggressive cleanup
function Cleanup-Aggressive {
    Write-Header "Aggressive Cleanup"
    
    Write-Warning "This will remove:"
    Write-Warning "  ✓ ALL stopped containers"
    Write-Warning "  ✓ ALL unused images (even if might be needed)"
    Write-Warning "  ✓ ALL build cache"
    Write-Warning "  ✓ ALL unused volumes"
    Write-Host ""
    Write-Warning "Next Docker builds may be slow!"
    Write-Host ""
    
    if (-not $Force) {
        $confirm = Read-Host "Continue aggressive cleanup? [yes/no]"
        if ($confirm -ne "yes") {
            Write-Info "Cancelled"
            return
        }
    }
    
    if ($DryRun) {
        Write-Info "DRY RUN - simulating cleanup"
    }
    
    Cleanup-Containers
    Cleanup-Images -Type all
    Cleanup-Cache
    Cleanup-Volumes
    
    if (-not $DryRun) {
        Write-Success "Aggressive cleanup complete"
        Show-Status
    }
}

# Interactive mode
function Interactive-Menu {
    do {
        Write-Host "`n╔════════════════════════════════════════════╗" -ForegroundColor Cyan
        Write-Host "║        Docker Cleanup - Main Menu         ║" -ForegroundColor Cyan
        Write-Host "╠════════════════════════════════════════════╣" -ForegroundColor Cyan
        Write-Host "║ 1. Show status (disk usage)               ║" -ForegroundColor Cyan
        Write-Host "║ 2. Analyze system                         ║" -ForegroundColor Cyan
        Write-Host "║ 3. Conservative cleanup (RECOMMENDED)     ║" -ForegroundColor Cyan
        Write-Host "║ 4. Aggressive cleanup                     ║" -ForegroundColor Cyan
        Write-Host "║ 5. Exit                                   ║" -ForegroundColor Cyan
        Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Cyan
        Write-Host ""
        
        $choice = Read-Host "Select option (1-5)"
        
        switch ($choice) {
            "1" { Show-Status }
            "2" { Analyze-System }
            "3" {
                $dryrun = Read-Host "Run as DRY RUN first? [yes/no]"
                if ($dryrun -eq "yes") {
                    Write-Host ""
                    & $PSCommandPath -Action cleanup-all -DryRun
                    Read-Host "`nPress Enter to see actual cleanup prompt"
                }
                & $PSCommandPath -Action cleanup-all
            }
            "4" {
                $dryrun = Read-Host "Run as DRY RUN first? [yes/no]"
                if ($dryrun -eq "yes") {
                    Write-Host ""
                    & $PSCommandPath -Action aggressive-cleanup -DryRun
                    Read-Host "`nPress Enter to see actual cleanup prompt"
                }
                & $PSCommandPath -Action aggressive-cleanup
            }
            "5" {
                Write-Host "Goodbye!`n"
                exit 0
            }
            default {
                Write-Warning "Invalid option, please try again"
            }
        }
    } while ($true)
}

# Main execution
try {
    if (-not (Test-Docker)) {
        exit 1
    }
    
    switch ($Action) {
        "status" { Show-Status }
        "analyze" { Analyze-System }
        "cleanup-containers" { Cleanup-Containers }
        "cleanup-images" { Cleanup-Images -Type dangling }
        "cleanup-volumes" { Cleanup-Volumes }
        "cleanup-cache" { Cleanup-Cache }
        "cleanup-all" { Cleanup-Conservative }
        "aggressive-cleanup" { Cleanup-Aggressive }
        "interactive" { Interactive-Menu }
        default { Show-Status }
    }
}
catch {
    Write-Error $_
    exit 1
}
