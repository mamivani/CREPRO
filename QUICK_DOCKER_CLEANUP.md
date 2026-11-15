# Quick Docker Cleanup - Copy & Paste Guide

## 🚀 Quick Start (5 Minutes)

### Step 1: Check Current Status
```powershell
cd C:\Dev\CREPRO
.\cleanup-docker.ps1 -Action status
```

**Expected Output:**
```
TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE
Images          273       2         32.76GB   30.46GB (93%)
Containers      78        76        10.61MB   151.6kB (1%)
Local Volumes   108       78        4.769GB   262.6MB (5%)
Build Cache     378       0         27.97GB   19.49GB
```

---

### Step 2: Analyze What Will Be Removed
```powershell
.\cleanup-docker.ps1 -Action analyze
```

**Expected Output:**
```
CONTAINERS: 78 total (76 running, 2 stopped/unused)
IMAGES: 273 total (2 active, 271 unused)
VOLUMES: 108 total (78 active, 30 unused)
DISK: ~50GB can be reclaimed safely
```

---

### Step 3A: Test Cleanup WITHOUT Making Changes (Dry Run)
```powershell
.\cleanup-docker.ps1 -Action cleanup-all -DryRun
```

**What this does:**
- Shows what WOULD be removed
- Makes no actual changes
- Safe to run anytime

**Expected Output:**
```
Would remove 2 container(s)
Would remove multiple dangling image(s)
Would remove 30 unused volume(s)
```

---

### Step 3B: Actually Run Cleanup
```powershell
.\cleanup-docker.ps1 -Action cleanup-all -Force
```

**What this does:**
- Removes 2 stopped containers
- Removes orphaned image layers
- Removes unused volumes
- **Keeps** all running containers
- **Keeps** active images

**Expected Output:**
```
✓ Containers cleaned
  Deleted Containers: 2
  Total reclaimed space: ~500KB

✓ Dangling images cleaned
  Deleted images: 215
  Total reclaimed space: ~1-2GB

✓ Unused volumes cleaned
  Deleted Volumes: 30
  Total reclaimed space: ~262MB
```

---

### Step 4: Verify Results
```powershell
.\cleanup-docker.ps1 -Action status
```

Compare disk usage with Step 1. Should see significant reduction.

---

## 📋 Cleanup Options

### Option A: Conservative (Safe, Recommended) ⭐
```powershell
.\cleanup-docker.ps1 -Action cleanup-all -Force
```

**Removes:**
- Stopped containers only (2)
- Orphaned images layers (~215)
- Unused volumes (30)

**Space**: 500MB - 2GB  
**Risk**: VERY LOW  
**Time**: < 2 minutes

---

### Option B: Aggressive (More Space, Medium Risk)
```powershell
.\cleanup-docker.ps1 -Action aggressive-cleanup -Force
```

**Removes:**
- All unused images (even tagged ones)
- ALL build cache
- Stopped containers
- Unused volumes

**Space**: 20-50GB  
**Risk**: MEDIUM (slow first rebuild)  
**Time**: 10-30 minutes

---

### Option C: Interactive Menu
```powershell
.\cleanup-docker.ps1 -Action interactive
```

**Menu Options:**
1. Show status
2. Analyze system
3. Conservative cleanup
4. Aggressive cleanup
5. Exit

Follow prompts, options to test with dry-run first.

---

## 🛠️ Useful Commands Cheat Sheet

```powershell
# Show disk usage
.\cleanup-docker.ps1 -Action status

# Detailed analysis
.\cleanup-docker.ps1 -Action analyze

# Test cleanup without changes (dry-run)
.\cleanup-docker.ps1 -Action cleanup-all -DryRun

# Actually cleanup
.\cleanup-docker.ps1 -Action cleanup-all -Force

# Only remove containers
.\cleanup-docker.ps1 -Action cleanup-containers -Force

# Only remove images
.\cleanup-docker.ps1 -Action cleanup-images -Force

# Only remove volumes
.\cleanup-docker.ps1 -Action cleanup-volumes -Force

# Aggressive cleanup
.\cleanup-docker.ps1 -Action aggressive-cleanup -Force

# Interactive mode
.\cleanup-docker.ps1 -Action interactive

# Quiet mode (no output)
.\cleanup-docker.ps1 -Action cleanup-all -Force -Quiet
```

---

## ⚠️ Important Notes

### Running Containers
- The 76 running `buildx_buildkit_builder` containers are **part of Docker's system**
- They are **safe to leave running** - use minimal disk space
- They will **auto-cleanup** when Docker restarts
- **DO NOT manually remove** these running containers

### About the 2 Stopped Containers
- These are "Created" but never run
- **Safe to remove** - they're completely unused
- Cleanup removes these

### About 215 Dangling Images
- These are orphaned build layers
- **Safe to remove** - can be regenerated from registry
- Cleanup removes these

### About 30 Unused Volumes
- These are not mounted to any container
- **Safe to remove** (unless you have data in them)
- If volumes contain important data, back up first
- Cleanup removes these

---

## 🔄 Recovery if Something Goes Wrong

### If Important Image Was Deleted
```powershell
# Pull it again from registry
docker pull ubuntu:20.04

# Or rebuild from Dockerfile
cd C:\Dev\CREPRO
docker build -t myapp:latest .
```

### If Important Volume Was Deleted
```powershell
# Restore from backup if available
# Otherwise data is lost
```

### If Docker Won't Start
```powershell
# Restart Docker Desktop
#   Settings → General → Restart Docker

# Or from command line
Stop-Service com.docker.service
Start-Service com.docker.service
```

---

## 📊 Results You Can Expect

**Conservative Cleanup (Option A):**
- Space freed: 500 MB - 2 GB
- Build time impact: None
- Risk: Very Low
- Reversibility: High

**Aggressive Cleanup (Option B):**
- Space freed: 20-50 GB
- Build time impact: First build slower (images rebuild)
- Risk: Medium
- Reversibility: Medium

---

## ✅ Verification Checklist

After cleanup:

- [ ] Ran cleanup command successfully
- [ ] No error messages
- [ ] `docker ps` shows running containers still running
- [ ] `docker system df` shows reduced disk usage
- [ ] Docker Desktop still responsive
- [ ] Available disk space increased

---

## 🚀 Next Steps

**Option 1: Minimal (Just Run It)**
```powershell
.\cleanup-docker.ps1 -Action cleanup-all -Force
```

**Option 2: Safe (Test First)**
```powershell
# First: test with dry-run
.\cleanup-docker.ps1 -Action cleanup-all -DryRun

# Then: actually run
.\cleanup-docker.ps1 -Action cleanup-all -Force
```

**Option 3: Interactive**
```powershell
.\cleanup-docker.ps1 -Action interactive
# Follow menu options
```

---

## ❓ FAQ

**Q: Will cleanup affect running containers?**  
A: No. Only stopped/unused items are removed.

**Q: Can I undo cleanup?**  
A: Most items (images, volumes) can be restored from backups or registry. Cleanup is generally reversible.

**Q: Why so many buildx containers?**  
A: Docker's multi-platform build system creates many builder instances. They're part of normal operation.

**Q: Is it safe to cleanup regularly?**  
A: Yes. Running cleanup weekly is recommended maintenance.

**Q: Will builds be slower after cleanup?**  
A: Only the first build after cleanup (images rebuild). Subsequent builds use cache as normal.

---

## 📞 Getting Help

See full documentation:
- `DOCKER_CLEANUP_GUIDE.md` - Complete guide with all options
- `DOCKER_CLEANUP_ANALYSIS.md` - Technical analysis and scenarios

Need to understand what will be removed? Run:
```powershell
.\cleanup-docker.ps1 -Action analyze
```

---

**Recommended**: Start with Option A (Conservative) for best balance of safety and space recovery.

Time to cleanup: **< 5 minutes**  
Space to recover: **~1-2 GB immediately**  
Risk level: **VERY LOW**

Ready? 🚀
