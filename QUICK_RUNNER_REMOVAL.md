# Quick Action: Remove Unused Runner (Option 1 - Recommended)

## 🎯 Goal
Remove **windows-runner-4** (ID: 30) - the least used runner
- Expected result: 75% job performance from 3 runners vs 4
- Cost savings: ~25% reduction in runner infrastructure
- Risk level: LOW
- Reversibility: HIGH (can re-register)

## ⚡ Quick Commands (Copy & Paste)

### Command 1: Verify Current Status
```powershell
cd C:\Dev\CREPRO
.\cleanup-runners.ps1 -Action status
```

**Expected Output:**
```
Total Runners:    4
Online:           4
Offline:          0
Currently Busy:   0
Idle:             4
```

### Command 2: Test Removal (Dry Run - NO CHANGES)
```powershell
.\cleanup-runners.ps1 -Action remove-single -RunnerIds 30 -DryRun
```

**Expected Output:**
```
INFO: DRY RUN: Would execute: gh api repos/mamivani/CREPRO/actions/runners/30 -X DELETE
```

✅ If you see "DRY RUN" message, the script is working correctly

### Command 3: Actually Remove Runner 30
```powershell
.\cleanup-runners.ps1 -Action remove-single -RunnerIds 30
```

When prompted:
```
Remove runner 'windows-runner-4' (ID: 30)? [yes/no]: yes
```

Type: `yes` and press Enter

**Expected Output:**
```
INFO: Removing runner 30...
Successfully removed runner 30
INFO: Wait 30 seconds for GitHub to update...
```

### Command 4: Verify Removal (Wait 30 seconds first)
```powershell
.\cleanup-runners.ps1 -Action list
```

**Expected Output:** Should show only 3 runners now

---

## 🔄 Then (Locally): Stop the Actual Runner Process

### If Docker Container:
```bash
docker ps -a | grep github-runner
# Find container ID for runner-4
docker stop <container-id>
docker rm <container-id>
```

### If Windows Service:
```powershell
Get-Service -Name "*github*" -ErrorAction SilentlyContinue
Remove-Service -Name "GitHubRunner4" -Force
```

### If Manual Installation:
1. Stop the `run.cmd` or `run.sh` process
2. Delete the runner directory (optional)

---

## ✅ Verification Checklist

- [ ] Ran `remove-single` command
- [ ] Typed `yes` when prompted
- [ ] Saw "Successfully removed runner 30" message
- [ ] Waited 30 seconds
- [ ] Ran `list` command and verified 3 runners remain
- [ ] Stopped/removed local runner service
- [ ] (Optional) Triggered a test workflow to verify remaining runners handle load

---

## ⚠️ If Something Goes Wrong

### Issue: "Not Found" Error
```
gh: Not Found (HTTP 404)
```
The runner might already be removed. Verify with:
```powershell
.\cleanup-runners.ps1 -Action list
```

### Issue: "Runner is currently busy" Error
Wait a few minutes for jobs to complete, then try again:
```powershell
.\cleanup-runners.ps1 -Action status
```

### Issue: Need to Undo
Re-register the runner on the machine where it was installed:
```bash
cd actions-runner
./config.sh --url https://github.com/mamivani/CREPRO --token [GITHUB_TOKEN]
./run.sh
```

---

## 📊 Impact Summary

**Before:**
- 4 runners available
- 35 jobs distributed: 11, 7, 7, 6
- Parallel capacity: High

**After:**
- 3 runners available
- Same jobs distributed: runner-1 handles 13, runner-2 handles 7, runner-3 handles 7
- Parallel capacity: Slightly reduced, still adequate

**Cost Savings:** ~25% (1 less runner instance)
**Performance Impact:** Minimal to none for current workload

---

## 🎬 Next Steps (Optional Advanced Scenarios)

Want to do more cleanup? After removing runner-4, you could:

**Scenario 2: Remove 2 runners**
```powershell
.\cleanup-runners.ps1 -Action remove-multiple -RunnerIds 29, 30
```

**Scenario 3: Keep only 1 runner (NOT RECOMMENDED)**
```powershell
.\cleanup-runners.ps1 -Action remove-multiple -RunnerIds 28, 29, 30
```

But Scenario 1 (remove-4 only) is the sweet spot.

---

## 📚 For More Information

- **Full Guide**: RUNNER_CLEANUP_GUIDE.md
- **Detailed Analysis**: RUNNER_CLEANUP_ANALYSIS.md
- **Script Help**: Run `.\cleanup-runners.ps1 -Action list` to see all options

---

**Ready to proceed?** Start with Command 1 above! 🚀
