# Docker Container & Image Cleanup Guide

## 📋 Table of Contents

1. [Quick Summary](#quick-summary)
2. [Current Status](#current-status)
3. [Safety First](#safety-first)
4. [Cleanup Options](#cleanup-options)
5. [Step-by-Step Instructions](#step-by-step-instructions)
6. [Verification](#verification)
7. [Troubleshooting](#troubleshooting)

---

## Quick Summary

Your Docker system has:
- **78 containers** (76 running, 2 unused)
- **273 images** (mostly unused layers)
- **~50 GB available** to reclaim through cleanup
- **Low risk** cleanup available now

**Recommendation**: Run conservative cleanup (Scenario 1) to free ~500MB-1GB with zero risk.

---

## Current Status

```
Docker Disk Usage Summary:
┌─────────────────┬──────────┬────────────┬──────────────────┐
│ Resource        │ Total    │ Reclaimable│ Recommendation   │
├─────────────────┼──────────┼────────────┼──────────────────┤
│ Images          │ 32.76 GB │ 30.46 GB   │ ⚠️ High cleanup  │
│ Containers      │ 10.61 MB │ 151.6 kB   │ ✅ 2 unused      │
│ Volumes         │ 4.769 GB │ 262.6 MB   │ ✅ Some orphaned │
│ Build Cache     │ 27.97 GB │ 19.49 GB   │ ⚠️ Large cache   │
├─────────────────┼──────────┼────────────┼──────────────────┤
│ TOTAL           │ 75.1 GB  │ ~50 GB     │ Can reclaim 60%  │
└─────────────────┴──────────┴────────────┴──────────────────┘
```

---

## Safety First

### What's Safe to Remove? ✅

**Very Safe (No Risk):**
- Stopped containers (Status: Exited, Created)
- Dangling images (orphaned layers)
- Unused volumes (not mounted anywhere)
- Old build cache (can be regenerated)

**Safe (Low Risk):**
- Unused images (not used by any container)
- Old image versions
- Build cache from old builds

### What Should NOT Be Removed? ❌

**Never Remove:**
- Running containers (Status: Up)
- Active images (used by running containers)
- Actively mounted volumes
- Recent build cache (might be in use)

### About Running Buildx Containers

The 76 running `buildx_buildkit_builder` containers are **part of Docker's system** and should NOT be manually removed. They:
- Are used by Docker Desktop's build system
- Auto-cleanup when Docker restarts
- Take minimal disk space (10.61 MB total)
- Are safe to leave running

---

## Cleanup Options

### ✅ Option 1: Conservative Cleanup (RECOMMENDED)

**What it does:**
```powershell
docker container prune -f           # Remove stopped containers
docker image prune -f               # Remove dangling images
docker volume prune -f              # Remove unused volumes
```

**Removes:**
- Stopped containers only
- Orphaned image layers
- Unmounted volumes

**Keeps:**
- All running containers
- Active images
- Everything else

**Space saved:** ~500 MB - 1 GB  
**Risk:** VERY LOW ✅  
**Time:** < 1 minute  
**Reversibility:** HIGH (images cache from registry)

**When to use:** Always safe, recommended for regular maintenance

---

### ⚠️ Option 2: Moderate Cleanup

**What it does:**
```powershell
docker container prune -f           # Remove stopped containers
docker image prune -a -f            # Remove ALL unused images
docker builder prune -a -f          # Remove all build cache
docker volume prune -f              # Remove unused volumes
```

**Removes:**
- All unused images (even if might be useful)
- Old build cache
- Orphaned containers & volumes

**Keeps:**
- Running containers
- Currently active data

**Space saved:** ~20-25 GB  
**Risk:** LOW ⚠️  
**Time:** 5-10 minutes (images rebuild on first use)  
**Reversibility:** MEDIUM (most images available from registry)

**When to use:** When you want more space and can accept rebuild time

---

### 🔴 Option 3: Aggressive Cleanup

**What it does:**
```powershell
docker system prune -a -f           # Remove everything unused
docker builder prune -a -f          # Clear all build cache
```

**Removes:**
- ALL unused images
- ALL build cache
- ALL unused volumes
- ALL stopped containers

**Keeps:**
- Running containers only

**Space saved:** ~50 GB  
**Risk:** MEDIUM ⚠️⚠️  
**Time:** 30-60 minutes (full rebuild)  
**Reversibility:** LOW (major rebuild needed)

**When to use:** Only when you need maximum space and can handle rebuild time

---

## Step-by-Step Instructions

### Before Starting - Verification

Run these commands to see what will be removed:

```powershell
# See stopped containers
docker ps -a --filter "status=exited"
docker ps -a --filter "status=created"

# See dangling images
docker images -f dangling=true

# See unused volumes
docker volume ls -f dangling=true

# See current disk usage
docker system df
```

### Option 1: Conservative Cleanup (Recommended)

#### Step 1: Remove Stopped Containers
```powershell
docker container prune -f
```

**Expected output:**
```
Deleted Containers:
cf014807449a
80711600bd95

Total reclaimed space: 151.6kB
```

#### Step 2: Remove Dangling Images
```powershell
docker image prune -f
```

**Expected output:**
```
Deleted images:
deleted sha256:abc123...

Total reclaimed space: 100MB - 500MB
```

#### Step 3: Remove Unused Volumes
```powershell
docker volume prune -f
```

**Expected output:**
```
Deleted Volumes:
volume_name_1
volume_name_2

Total reclaimed space: 262.6MB
```

#### Step 4: Verify Results
```powershell
docker system df
```

Compare with previous output. Should see reduced numbers.

---

### Option 2: Moderate Cleanup

**Warning**: This removes images that might be needed. First backup important data.

#### Step 1: Remove Stopped Containers
```powershell
docker container prune -f
```

#### Step 2: Remove All Unused Images
```powershell
docker image prune -a -f
```

This removes images not used by running containers. **First build will be slower.**

#### Step 3: Remove Build Cache
```powershell
docker builder prune -a -f
```

#### Step 4: Remove Unused Volumes
```powershell
docker volume prune -f
```

#### Step 5: Verify
```powershell
docker system df
docker images                   # Should show very few images
```

**Note**: Next build will download/rebuild images.

---

### Option 3: Aggressive Cleanup

**WARNING**: This clears almost everything except running containers.

#### Step 1: Full System Prune
```powershell
docker system prune -a -f
```

This removes:
- All stopped containers
- All images not used by running containers
- All build cache
- All unused volumes
- All unused networks

#### Step 2: Clear Build Cache
```powershell
docker builder prune -a -f
```

#### Step 3: Verify
```powershell
docker system df
docker images                   # Only images for running containers
```

**Note**: Prepare for slow builds until cache regenerates.

---

## Verification

### After Cleanup Checklist

- [ ] Ran `docker system df` and confirmed disk usage decreased
- [ ] Confirmed running containers are still running: `docker ps`
- [ ] No error messages from cleanup commands
- [ ] Docker Desktop still responsive
- [ ] Disk space available as expected

### Ongoing Monitoring

Monitor disk usage regularly:

```powershell
# View disk usage
docker system df

# View with details
docker system df -v

# See largest images
docker images --format "{{.Size}}\t{{.Repository}}" | Sort-Object
```

### Health Check

```powershell
# Test that Docker still works
docker run --rm hello-world

# Build something simple
docker build -t test:latest .

# View recent activity
docker ps
docker images
```

---

## Troubleshooting

### Issue: "Permission Denied" Error

**Cause**: Docker daemon requires elevated privileges  
**Solution**:
```powershell
# Run PowerShell as Administrator
# Then retry cleanup commands
```

Or use WSL:
```bash
# In WSL terminal
docker system prune -f
```

---

### Issue: "Cannot remove container" Error

**Cause**: Container is still running  
**Solution**:
```powershell
# Stop the container first
docker stop <container_id>

# Then run prune
docker container prune -f
```

---

### Issue: "Device or resource busy"

**Cause**: Docker is in middle of operation  
**Solution**:
```powershell
# Wait a moment, then try again
Start-Sleep -Seconds 5
docker container prune -f

# Or restart Docker Desktop
# Settings → Troubleshoot → Restart Docker
```

---

### Issue: "Disk space not freed"

**Cause**: Docker system cache hasn't updated  
**Solution**:
```powershell
# Restart Docker Desktop
#   Settings → General → Restart Docker

# Or clear system cache
docker system prune --all --force --volumes
```

---

### Issue: Images Missing After Cleanup

**Cause**: Aggressive cleanup removed images  
**Solution**: Pull images from registry:
```powershell
# For example:
docker pull ubuntu:latest
docker pull node:latest

# Or rebuild from Dockerfile
cd path/to/project
docker build -t myapp:latest .
```

---

## Best Practices

### Automatic Cleanup

Run cleanup regularly (e.g., weekly):

```powershell
# In scheduled task or script
docker container prune -f --filter "until=72h"
docker image prune -f --filter "until=720h"
docker builder prune -f --filter "until=720h"
```

### Manual Cleanup Schedule

- **Daily**: Check with `docker system df`
- **Weekly**: Run `docker container prune -f`
- **Monthly**: Run `docker image prune -f`
- **Quarterly**: Run full cleanup if needed

### Preservation Strategy

For important images, tag them with a preservation label:

```powershell
# Mark image as important
docker tag myimage:old myimage:keep

# When using prune, it won't remove tagged versions
docker image prune -a
# myimage:keep is preserved
```

---

## Recovery from Mistakes

### If Too Much Was Deleted

**Scenario 1: Deleted image you need**
```powershell
# Pull it again from registry
docker pull ubuntu:20.04

# Or rebuild from Dockerfile
docker build -t myapp:latest .
```

**Scenario 2: Deleted volume with data**
- If backed up elsewhere: restore from backup
- If not backed up: data is lost

**Prevention**: Always backup important volumes before aggressive cleanup.

---

## Commands Quick Reference

```powershell
# View what will be removed (dry run)
docker container prune --dry-run
docker image prune -a --dry-run
docker volume prune --dry-run

# Remove unused items (safe)
docker container prune -f
docker image prune -f
docker volume prune -f

# Remove more items
docker image prune -a -f           # Remove all unused images
docker builder prune -a -f         # Remove build cache

# Full cleanup (aggressive)
docker system prune -a -f          # Everything except running

# View current status
docker system df                   # Summary
docker system df -v                # Detailed
docker ps -a                       # All containers
docker images                      # All images
docker volume ls                   # All volumes
```

---

## Summary

| Action | Command | Space | Risk | Time |
|--------|---------|-------|------|------|
| **Conservative** | `docker container prune -f` | 500MB | VERY LOW | < 1min |
| **Conservative+** | + `docker image prune -f` | 1GB | VERY LOW | < 2min |
| **Moderate** | + `docker image prune -a -f` | 20GB | LOW | 5-10min |
| **Aggressive** | + `docker builder prune -a -f` | 50GB | MEDIUM | 30min |

---

**Recommendation**: Start with Conservative cleanup, monitor results, and escalate only if more space is needed.

For immediate cleanup: `docker container prune -f && docker image prune -f`
