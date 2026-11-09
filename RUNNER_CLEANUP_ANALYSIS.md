# Docker Self-Hosted Runner Cleanup Analysis

**Date**: 2026-11-09  
**Repository**: mamivani/CREPRO  
**Current Status**: 4 Windows self-hosted runners registered and online

---

## 📊 Current Runner Inventory

### Registered Runners

| Runner Name | ID | OS | Status | Version | Labels |
|---|---|---|---|---|---|
| windows-runner-1 | 27 | Windows | online | 2.338.2 | self-hosted, Windows, X64, docker |
| windows-runner-2 | 28 | Windows | online | 2.338.2 | self-hosted, Windows, X64, docker |
| windows-runner-3 | 29 | Windows | online | 2.338.2 | self-hosted, Windows, X64, docker |
| windows-runner-4 | 30 | Windows | online | 2.338.2 | self-hosted, Windows, X64, docker |

**Total**: 4 runners

---

## 📈 Runner Usage Analysis (Last 5 Workflow Runs)

### Job Distribution by Runner

| Runner | Jobs Executed | Percentage | Status |
|---|---|---|---|
| windows-runner-1 | 11 | 31.4% | **MOST USED** |
| windows-runner-2 | 7 | 20.0% | Active |
| windows-runner-3 | 7 | 20.0% | Active |
| windows-runner-4 | 6 | 17.1% | **LEAST USED** |

**Total Jobs**: 35 across 5 runs

---

## 🎯 Cleanup Recommendation

### Scenario 1: Minimal Cleanup (Reduce to 3 runners)
**Recommendation**: Remove **windows-runner-4**
- **Rationale**: Least utilized runner (17.1% usage)
- **Risk Level**: LOW
- **Impact**: Slight workload distribution adjustment to remaining 3 runners
- **Expected**: windows-runner-1, 2, 3 will distribute 35 jobs (vs. current 31)

**Removal Command**:
```powershell
gh api repos/mamivani/CREPRO/actions/runners/30 -X DELETE
```

**Validation**: 
- Verify runner is offline after removal
- Run one full workflow suite to ensure 3 runners handle load

---

### Scenario 2: Moderate Cleanup (Reduce to 2 runners)
**Recommendation**: Remove **windows-runner-3 and windows-runner-4**
- **Rationale**: Keep 2 most-utilized runners (runner-1 and runner-2)
- **Risk Level**: MEDIUM
- **Impact**: Increased workload concentration
- **Expected**: Potential queue time during parallel jobs

**Removal Commands**:
```powershell
gh api repos/mamivani/CREPRO/actions/runners/29 -X DELETE
gh api repos/mamivani/CREPRO/actions/runners/30 -X DELETE
```

**When to Use**: If infrastructure costs are critical concern

---

### Scenario 3: Aggressive Cleanup (Single Runner)
**Recommendation**: Keep **windows-runner-1**, Remove others
- **Rationale**: Maximum cost reduction
- **Risk Level**: HIGH
- **Impact**: Serial job execution, significant workflow slowdown
- **Expected**: 30-50% longer CI/CD cycles

**Removal Commands**:
```powershell
gh api repos/mamivani/CREPRO/actions/runners/28 -X DELETE
gh api repos/mamivani/CREPRO/actions/runners/29 -X DELETE
gh api repos/mamivani/CREPRO/actions/runners/30 -X DELETE
```

**When to Use**: Only if budgets are extremely constrained and speed is not a factor

---

## 📋 Prerequisites Before Cleanup

- [ ] Ensure no jobs are currently running on the runner(s) to be removed
- [ ] Have a backup removal command ready
- [ ] Plan maintenance window if critical
- [ ] Document which runner was removed and when
- [ ] Monitor workflow execution after removal

---

## 🔄 Pre-Cleanup Verification Steps

### 1. Check Current Job Queue
```powershell
gh api repos/mamivani/CREPRO/actions/runs?status=in_progress | ConvertFrom-Json | Select-Object -ExpandProperty workflow_runs | ForEach-Object { Write-Host "$($_.name) (#$($_.run_number))" }
```

### 2. Check for Scheduled Workflows
```powershell
gh api repos/mamivani/CREPRO/actions/workflows | ConvertFrom-Json | Select-Object -ExpandProperty workflows | Where-Object { $_.state -eq "active" }
```

### 3. Monitor Runner Status
```powershell
gh api repos/mamivani/CREPRO/actions/runners | ConvertFrom-Json | Select-Object -ExpandProperty runners | Format-Table name, status, busy
```

---

## 🗑️ Removal Procedure

### Step-by-Step Cleanup

1. **Identify Target Runner(s)**
   - From analysis above, choose which runner(s) to remove

2. **Verify No Active Jobs**
   ```powershell
   gh api repos/mamivani/CREPRO/actions/runners/[RUNNER_ID] | ConvertFrom-Json | Select-Object name, busy, status
   ```

3. **Remove Runner from GitHub**
   ```powershell
   gh api repos/mamivani/CREPRO/actions/runners/[RUNNER_ID] -X DELETE
   ```

4. **Verify Removal**
   ```powershell
   gh api repos/mamivani/CREPRO/actions/runners | ConvertFrom-Json | Select-Object -ExpandProperty runners | Format-Table name
   ```

5. **Stop/Uninstall Local Runner Service**
   - If Windows Service: `Remove-Service -Name GitHubRunner[N] -Force`
   - If Docker Container: `docker stop github-runner-[N] && docker rm github-runner-[N]`
   - If Manual: Stop process and remove installation directory

6. **Test Workflow Execution**
   - Trigger a workflow run
   - Monitor execution on remaining runner(s)
   - Confirm all jobs complete successfully

---

## ⏮️ Rollback Procedure

If removal causes issues:

1. **Re-register Runner** (from backup installation)
   ```powershell
   # On the machine/container where runner was installed
   ./config.sh --url https://github.com/mamivani/CREPRO --token [GITHUB_TOKEN]
   ./run.sh
   ```

2. **Verify Registration**
   ```powershell
   gh api repos/mamivani/CREPRO/actions/runners | ConvertFrom-Json | Select-Object -ExpandProperty runners | Format-Table name
   ```

---

## 📝 Cleanup Checklist

**Recommended Option**: Scenario 1 (Remove windows-runner-4 only)

- [ ] Verify no active jobs running
- [ ] Run removal command for runner ID 30
- [ ] Confirm removal in GitHub UI or via API
- [ ] Stop local runner service/container on removal target
- [ ] Trigger test workflow
- [ ] Monitor job distribution on remaining 3 runners
- [ ] Document removal in repository changelog

---

## 🔗 Related Documentation

- [README_SELF_HOSTED.md](./README_SELF_HOSTED.md) - Runner setup guide
- [SELF_HOSTED_RUNNER_SETUP.md](./SELF_HOSTED_RUNNER_SETUP.md) - Detailed installation
- [QUICK_START_RUNNER.md](./QUICK_START_RUNNER.md) - Quick setup

---

## 💡 Best Practices Going Forward

1. **Monitor Usage Regularly**: Check job distribution monthly
2. **Retire Unused Runners**: Remove runners with <10% usage for 30+ days
3. **Capacity Planning**: Add runners if queue times exceed 5 minutes
4. **Documentation**: Update this analysis after any changes
5. **Cost Tracking**: Monitor infrastructure costs vs. CI/CD performance gains

