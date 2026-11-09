# Docker Self-Hosted Runner Cleanup Guide

## Quick Summary

This guide provides step-by-step instructions for cleaning up unused Docker self-hosted runners in the CREPRO repository.

**Current Status**: 4 Windows self-hosted runners registered
- ✅ All 4 runners are online and healthy
- ✅ All runners have the required Docker label
- ⚠️ Recommended: Reduce to 2-3 runners if cost optimization is needed

---

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Understanding Your Runners](#understanding-your-runners)
3. [Analysis Results](#analysis-results)
4. [Cleanup Options](#cleanup-options)
5. [Step-by-Step Removal](#step-by-step-removal)
6. [Verification & Testing](#verification--testing)
7. [Troubleshooting](#troubleshooting)

---

## 🚀 Quick Start

### Option A: Analyze Before Removing (Recommended)
```powershell
cd C:\Dev\CREPRO
.\cleanup-runners.ps1 -Action analyze
```

### Option B: List All Runners
```powershell
.\cleanup-runners.ps1 -Action list
```

### Option C: Check Status
```powershell
.\cleanup-runners.ps1 -Action status
```

### Option D: Remove a Single Runner (Example: Runner 30)
```powershell
.\cleanup-runners.ps1 -Action remove-single -RunnerIds 30
```

### Option E: Dry Run (No Changes)
```powershell
.\cleanup-runners.ps1 -Action remove-single -RunnerIds 30 -DryRun
```

---

## Understanding Your Runners

### Current Runners

| ID | Name | Status | Labels |
|----|------|--------|--------|
| 27 | windows-runner-1 | 🟢 Online | self-hosted, Windows, X64, docker |
| 28 | windows-runner-2 | 🟢 Online | self-hosted, Windows, X64, docker |
| 29 | windows-runner-3 | 🟢 Online | self-hosted, Windows, X64, docker |
| 30 | windows-runner-4 | 🟢 Online | self-hosted, Windows, X64, docker |

All runners:
- Are **Windows**-based
- Have the **docker** label required for container builds
- Are **online** and ready for jobs

---

## Analysis Results

### Job Distribution (Last 5 Runs)

| Runner | Jobs | % of Total | Recommendation |
|--------|------|-----------|-----------------|
| windows-runner-1 | 11 | 31.4% | ✅ Keep |
| windows-runner-2 | 7 | 20.0% | ✅ Keep |
| windows-runner-3 | 7 | 20.0% | ✅ Keep |
| windows-runner-4 | 6 | 17.1% | ⚠️ Could Remove |

**Interpretation:**
- **Runner-1** is most utilized (handles ~1/3 of jobs)
- **Runner-4** is least utilized (handles ~1/6 of jobs)
- **All runners are active** - none are completely idle
- **Removing any runner** will require remaining runners to handle more load

---

## Cleanup Options

### Scenario 1: Minimal Cleanup (Recommended) ⭐
**Remove: windows-runner-4 (ID: 30)**

**Pros:**
- Minimal performance impact
- Keeps capacity for parallel job execution
- Best balance between cost and performance
- Easy to rollback if needed

**Cons:**
- Smallest cost reduction
- Still requires 3 runner instances

**When to Choose:** Standard case, want to reduce costs without sacrificing speed

**Command:**
```powershell
.\cleanup-runners.ps1 -Action remove-single -RunnerIds 30
```

---

### Scenario 2: Moderate Cleanup
**Remove: windows-runner-3 & 4 (IDs: 29, 30)**

**Pros:**
- Significant cost reduction (50% runner count)
- Moderate performance impact
- Keeps redundancy with 2 runners

**Cons:**
- Noticeable slowdown during peak parallel jobs
- Reduced availability if one runner fails

**When to Choose:** Prioritize cost savings over build speed

**Command:**
```powershell
.\cleanup-runners.ps1 -Action remove-multiple -RunnerIds 29, 30
```

---

### Scenario 3: Aggressive Cleanup
**Remove: windows-runner-2, 3, & 4 (IDs: 28, 29, 30)**

**Pros:**
- Maximum cost reduction (75% runner count)
- Single source of truth for debugging

**Cons:**
- Significant performance hit (slower CI/CD)
- No redundancy - single runner failure = blocked pipeline
- Serial job execution instead of parallel

**When to Choose:** Extreme cost constraints, speed is not important

**Command:**
```powershell
.\cleanup-runners.ps1 -Action remove-multiple -RunnerIds 28, 29, 30
```

---

## Step-by-Step Removal

### Prerequisites

- [ ] GitHub CLI (gh) is installed: `gh --version`
- [ ] GitHub CLI is authenticated: `gh auth status`
- [ ] You have permission to manage runners in the repository
- [ ] No workflows are currently running (or use `-Force`)

### Step 1: Verify Runners Are Not Busy

```powershell
.\cleanup-runners.ps1 -Action status
```

**Look for:**
- "Currently Busy: 0" ✅ Safe to remove
- "Currently Busy: 1+" ⚠️ Wait for jobs to complete

### Step 2: Run Dry Run (Optional but Recommended)

```powershell
.\cleanup-runners.ps1 -Action remove-single -RunnerIds 30 -DryRun
```

**Expected Output:**
```
INFO: DRY RUN: Would execute: gh api repos/mamivani/CREPRO/actions/runners/30 -X DELETE
```

This shows what would happen without making changes.

### Step 3: Perform Actual Removal

```powershell
.\cleanup-runners.ps1 -Action remove-single -RunnerIds 30
```

**When prompted:**
```
Remove runner 'windows-runner-4' (ID: 30)? [yes/no]: yes
```

Type `yes` and press Enter.

**Expected Output:**
```
INFO: Removing runner 30...
Successfully removed runner 30
INFO: Wait 30 seconds for GitHub to update, then verify with: ./cleanup-runners.ps1 -Action list
```

### Step 4: Verify Removal

Wait 30 seconds, then verify:

```powershell
.\cleanup-runners.ps1 -Action list
```

Should now show 3 runners instead of 4.

### Step 5: Stop Local Runner Service/Process

On the machine where the runner was installed:

**If Windows Service:**
```powershell
Remove-Service -Name "GitHubRunner" -Force
```

**If Docker Container:**
```bash
docker stop github-runner-4
docker rm github-runner-4
```

**If Manual Installation:**
1. Stop the `run.cmd` or `run.sh` process
2. Remove the installation directory

---

## Verification & Testing

### Step 1: Verify GitHub Knows About Change
```powershell
.\cleanup-runners.ps1 -Action list
# Should show only 3 runners now
```

### Step 2: Trigger a Test Workflow

Push a commit or trigger manually:
```bash
git push origin develop
# Wait for build workflow to start
```

### Step 3: Monitor Job Execution

```powershell
gh run list --repo mamivani/CREPRO --limit 1
```

Watch the workflow run and confirm:
- ✅ All jobs execute successfully
- ✅ Jobs distribute across remaining runners
- ✅ No timeouts or failures

### Step 4: Check Performance

After first full workflow run, verify:
- [ ] All jobs completed successfully
- [ ] No queue backlog
- [ ] Reasonable execution times

---

## Troubleshooting

### Issue: Runner Still Shows in GitHub After Deletion

**Solution:**
- GitHub caches the runner list for ~30 seconds
- Wait 1 minute and refresh: `.\cleanup-runners.ps1 -Action list`
- If still there after 2 minutes, check GitHub Actions settings page

### Issue: "Runner is currently busy" Error

**Solution Option 1:** Wait for jobs to finish
```powershell
# Check status
.\cleanup-runners.ps1 -Action status

# Wait for Current Busy to become 0
```

**Solution Option 2:** Force removal
```powershell
.\cleanup-runners.ps1 -Action remove-single -RunnerIds 30 -Force
```

### Issue: Build Failures After Removal

**Cause:** Remaining runners overloaded with jobs

**Solution:**
1. Re-add removed runner:
   ```powershell
   # On the machine where runner was installed
   ./config.sh --url https://github.com/mamivani/CREPRO --token [TOKEN]
   ./run.sh
   ```

2. Verify runner shows up:
   ```powershell
   .\cleanup-runners.ps1 -Action list
   ```

### Issue: "HTTP 404" Error from GitHub API

**Cause:** Invalid runner ID or runner already removed

**Solution:**
1. List all runners to get valid IDs:
   ```powershell
   .\cleanup-runners.ps1 -Action list
   ```

2. Use valid ID from the list

### Issue: GitHub CLI Not Authenticated

**Solution:**
```powershell
gh auth login
# Follow the prompts to authenticate
```

---

## Recovery / Rollback

### If You Remove a Runner by Mistake

The runner can be re-registered on the same machine where it was installed.

**Steps:**

1. **On the machine with the runner:**
   ```bash
   cd actions-runner
   ./config.sh --url https://github.com/mamivani/CREPRO --token [GITHUB_TOKEN]
   ./run.sh
   ```

2. **Verify in GitHub:**
   ```powershell
   .\cleanup-runners.ps1 -Action list
   # Should see the runner re-appear
   ```

3. **Note:** The runner will be re-registered with a NEW ID and potentially a new name

---

## Documentation References

- **Full Analysis**: See [RUNNER_CLEANUP_ANALYSIS.md](./RUNNER_CLEANUP_ANALYSIS.md)
- **Setup Guide**: See [SELF_HOSTED_RUNNER_SETUP.md](./SELF_HOSTED_RUNNER_SETUP.md)
- **Quick Start**: See [QUICK_START_RUNNER.md](./QUICK_START_RUNNER.md)

---

## Common Commands Cheat Sheet

```powershell
# View all runners
.\cleanup-runners.ps1 -Action list

# Check status
.\cleanup-runners.ps1 -Action status

# Analyze usage
.\cleanup-runners.ps1 -Action analyze

# Dry run (no changes)
.\cleanup-runners.ps1 -Action remove-single -RunnerIds 30 -DryRun

# Remove runner 30
.\cleanup-runners.ps1 -Action remove-single -RunnerIds 30

# Remove multiple runners
.\cleanup-runners.ps1 -Action remove-multiple -RunnerIds 29, 30

# Force removal (no confirmation)
.\cleanup-runners.ps1 -Action remove-single -RunnerIds 30 -Force
```

---

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review related documentation files
3. Check GitHub Actions settings page: https://github.com/mamivani/CREPRO/settings/actions/runners

---

**Last Updated**: 2026-11-09
