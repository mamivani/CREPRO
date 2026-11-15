# Docker Self-Hosted Runner Cleanup - Complete Index

## 📌 Quick Links

| Need | Document | Location |
|------|----------|----------|
| **Quick Action** | [QUICK_RUNNER_REMOVAL.md](./QUICK_RUNNER_REMOVAL.md) | Repository |
| **Step-by-Step Guide** | [RUNNER_CLEANUP_GUIDE.md](./RUNNER_CLEANUP_GUIDE.md) | Repository |
| **Technical Analysis** | [RUNNER_CLEANUP_ANALYSIS.md](./RUNNER_CLEANUP_ANALYSIS.md) | Repository |
| **Management Tool** | [cleanup-runners.ps1](./cleanup-runners.ps1) | Repository |
| **Implementation** | [IMPLEMENTATION_CHECKLIST.md](../files/IMPLEMENTATION_CHECKLIST.md) | Session |
| **Summary** | [RUNNER_CLEANUP_SUMMARY.md](../files/RUNNER_CLEANUP_SUMMARY.md) | Session |

---

## 🎯 Current Situation

**Status**: ✅ Ready for cleanup  
**Total Runners**: 4 Windows runners (all online)  
**Recommendation**: Remove windows-runner-4 (ID: 30) - least utilized at 17.1%  
**Benefit**: ~25% cost savings with minimal performance impact  

---

## 📊 Quick Facts

| Metric | Value |
|--------|-------|
| Total Runners | 4 |
| Online Runners | 4 |
| Offline Runners | 0 |
| Jobs Analyzed | 35 (across 5 runs) |
| Recommended for Removal | windows-runner-4 (ID: 30) |
| Usage (runner-4) | 17.1% (6 of 35 jobs) |
| Cost Savings (Scenario 1) | ~25% |
| Performance Impact | Minimal |
| Risk Level | LOW |

---

## 🚀 Getting Started

### For First-Time Users
1. Start with: **QUICK_RUNNER_REMOVAL.md**
2. Review the quick commands section
3. Execute step-by-step with verification

### For Detailed Review
1. Read: **RUNNER_CLEANUP_ANALYSIS.md** (understand current state)
2. Study: **RUNNER_CLEANUP_GUIDE.md** (learn all options)
3. Plan: **IMPLEMENTATION_CHECKLIST.md** (prepare execution)

### For Automation/Scripting
1. Review: **cleanup-runners.ps1** (tool capabilities)
2. Test: Run `.\cleanup-runners.ps1 -Action list` (verify setup)
3. Execute: Follow script prompts

---

## 📚 Document Guide

### QUICK_RUNNER_REMOVAL.md
**Best for**: Getting it done quickly  
**Length**: ~4 KB | **Reading time**: 5 minutes  
**Contains**:
- Copy-paste ready commands
- Expected outputs
- Quick verification
- Next steps

**Use this if**: You're ready to act and want minimal reading

---

### RUNNER_CLEANUP_GUIDE.md
**Best for**: Step-by-step comprehensive guide  
**Length**: ~10 KB | **Reading time**: 15 minutes  
**Contains**:
- Prerequisites checklist
- Detailed removal procedures
- Troubleshooting guide
- Rollback procedures
- Commands cheat sheet

**Use this if**: You want to understand all options and be fully prepared

---

### RUNNER_CLEANUP_ANALYSIS.md
**Best for**: Technical understanding  
**Length**: ~6.5 KB | **Reading time**: 10 minutes  
**Contains**:
- Runner inventory with status
- Job distribution analysis
- Three cleanup scenarios
- Risk assessments
- Prerequisites and validation

**Use this if**: You need to justify decisions or understand trade-offs

---

### cleanup-runners.ps1
**Best for**: Automated runner management  
**Type**: PowerShell script | **Size**: ~9.2 KB  
**Features**:
- `list` - Show all runners
- `status` - Health summary
- `analyze` - Usage analytics
- `remove-single` - Remove one runner
- `remove-multiple` - Remove multiple runners

**Options**:
- `-DryRun` - Test without changes
- `-Force` - Skip confirmations
- `-RunnerIds` - Specify which runners

**Use this if**: You want automated, repeatable cleanup with safety checks

---

## 🔄 Three Cleanup Scenarios

### Scenario 1: MINIMAL CLEANUP ⭐ (RECOMMENDED)
```powershell
.\cleanup-runners.ps1 -Action remove-single -RunnerIds 30
```
- **Remove**: runner-4 (ID: 30)
- **Savings**: ~25%
- **Impact**: Minimal
- **Risk**: LOW

---

### Scenario 2: MODERATE CLEANUP
```powershell
.\cleanup-runners.ps1 -Action remove-multiple -RunnerIds 29, 30
```
- **Remove**: runner-3 & 4 (IDs: 29, 30)
- **Savings**: ~50%
- **Impact**: Noticeable slowdown
- **Risk**: MEDIUM

---

### Scenario 3: AGGRESSIVE CLEANUP
```powershell
.\cleanup-runners.ps1 -Action remove-multiple -RunnerIds 28, 29, 30
```
- **Remove**: runner-2, 3, 4 (IDs: 28, 29, 30)
- **Savings**: ~75%
- **Impact**: Significant slowdown
- **Risk**: HIGH

---

## ✅ Implementation Flowchart

```
START
  ↓
Read QUICK_RUNNER_REMOVAL.md
  ↓
Run: .\cleanup-runners.ps1 -Action status
  ↓
Run: .\cleanup-runners.ps1 -Action remove-single -RunnerIds 30 -DryRun
  ↓ (If dry-run looks good)
Run: .\cleanup-runners.ps1 -Action remove-single -RunnerIds 30
  ↓ (Type 'yes' when prompted)
Wait 30 seconds
  ↓
Run: .\cleanup-runners.ps1 -Action list
  ↓ (Verify 3 runners remain)
Stop local runner process
  ↓
Test with workflow run
  ↓
Monitor for 24 hours
  ↓
DONE ✅
```

---

## 🛠️ Tool Usage Quick Reference

### List All Runners
```powershell
.\cleanup-runners.ps1 -Action list
```

### Check Health Status
```powershell
.\cleanup-runners.ps1 -Action status
```

### Analyze Job Usage
```powershell
.\cleanup-runners.ps1 -Action analyze
```

### Test Removal (No Changes)
```powershell
.\cleanup-runners.ps1 -Action remove-single -RunnerIds 30 -DryRun
```

### Actually Remove Runner
```powershell
.\cleanup-runners.ps1 -Action remove-single -RunnerIds 30
```

### Remove Multiple Runners
```powershell
.\cleanup-runners.ps1 -Action remove-multiple -RunnerIds 29, 30
```

### Force Removal (Skip Prompts)
```powershell
.\cleanup-runners.ps1 -Action remove-single -RunnerIds 30 -Force
```

---

## 📋 Pre-Cleanup Checklist

- [ ] GitHub CLI installed: `gh --version`
- [ ] GitHub CLI authenticated: `gh auth status`
- [ ] Read QUICK_RUNNER_REMOVAL.md
- [ ] No critical workflows running
- [ ] Team notified (optional)
- [ ] Have rollback plan (optional)

---

## 🔄 Post-Cleanup Verification

- [ ] Ran removal command successfully
- [ ] Saw confirmation message
- [ ] Waited 30 seconds
- [ ] Verified 3 runners with `list` command
- [ ] Stopped local runner service
- [ ] Triggered test workflow
- [ ] All jobs executed successfully
- [ ] No performance issues observed

---

## 🚨 If Issues Occur

**Symptom**: Build failures after removal  
**Solution**: Re-register runner or restore from backup

```bash
cd actions-runner
./config.sh --url https://github.com/mamivani/CREPRO --token [TOKEN]
./run.sh
```

---

## 📞 Support Resources

| Issue | Solution |
|-------|----------|
| GitHub CLI not found | Install from github.com/cli/cli/releases |
| "Not authenticated" | Run `gh auth login` |
| "Runner is busy" | Wait a few minutes or use `-Force` option |
| "HTTP 404" | Runner might already be removed, verify with `list` |
| Workflow failures | Check runner distribution, may need to rollback |

---

## 📈 Success Metrics

✅ **Successful cleanup**:
- [ ] Runner removed from GitHub
- [ ] Remaining runners are online
- [ ] Recent workflows complete successfully
- [ ] Job distribution is healthy
- [ ] No timeouts or failures
- [ ] Cost reduced by ~25%

---

## 🎓 Learning Resources

**GitHub Actions Runners**:
- [GitHub Docs: Self-hosted runners](https://docs.github.com/en/actions/hosting-your-own-runners)
- [Runner Management API](https://docs.github.com/en/rest/actions/self-hosted-runners)

**PowerShell**:
- [GitHub CLI in PowerShell](https://cli.github.com/manual/gh_api)
- [GitHub CLI Reference](https://cli.github.com/manual/)

---

## 📝 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-11-09 | Initial release with complete cleanup toolkit |

---

## 🎯 Next Steps

1. **Choose your approach**:
   - Quick action? → Start with QUICK_RUNNER_REMOVAL.md
   - Full understanding? → Read RUNNER_CLEANUP_GUIDE.md
   - Just run it? → Use cleanup-runners.ps1

2. **Execute cleanup** when ready

3. **Verify** with test workflow

4. **Monitor** for 24 hours

5. **Document** completion

---

**Status**: ✅ Complete & Ready  
**All Resources**: ✅ Available  
**Recommendation**: Implement Scenario 1 (Remove runner-4)  
**Risk Level**: LOW  
**Expected Duration**: 15-30 minutes

---

**Need help?** Refer to the troubleshooting section in RUNNER_CLEANUP_GUIDE.md or review the IMPLEMENTATION_CHECKLIST.md for step-by-step guidance.
