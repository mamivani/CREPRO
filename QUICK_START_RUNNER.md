# Quick Start: Self-Hosted Runner Setup

> **Fastest way to get your self-hosted runner up and running**

## Prerequisites
- Docker installed and running (or Python/Git if going native)
- GitHub Personal Access Token (see below)

## Generate GitHub Token (5 minutes)

1. Go to: https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Name: `github-actions-runner`
4. Scopes: Check ✅ `repo` and ✅ `workflow`
5. Click "Generate token"
6. **Copy the token** (appears once, can't retrieve later)

**Your token**: `ghp_XXXXXXXXXXXXXXX...`

## Option A: Docker (EASIEST - 2 minutes)

### If you have Docker:
```bash
# One command to run the runner
docker run -d --restart=always \
  -e RUNNER_ALLOW_RUNASROOT=true \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /tmp/github-runner:/home/runner \
  -e GITHUB_TOKEN=ghp_XXXXXXXXXXXXXXX \
  -e RUNNER_REPOSITORY=mamivani/CREPRO \
  --name github-runner \
  myoung34/github-runner:latest
```

**That's it!** Your runner is running. Go to step "Verify".

---

## Option B: Linux/macOS (Native - 5 minutes)

```bash
# Create directory
mkdir -p github-runner
cd github-runner

# Download runner
curl -o runner.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.317.0/actions-runner-linux-x64-2.317.0.tar.gz
tar xzf runner.tar.gz

# Configure
./config.sh --url https://github.com/mamivani/CREPRO \
  --token ghp_XXXXXXXXXXXXXXX \
  --unattended

# Run (keep this terminal open or run in tmux/screen)
./run.sh
```

---

## Option C: Windows (Native - 5 minutes)

```powershell
# Create directory
mkdir github-runner
cd github-runner

# Download
Invoke-WebRequest -Uri "https://github.com/actions/runner/releases/download/v2.317.0/actions-runner-win-x64-2.317.0.zip" -OutFile "runner.zip"
Expand-Archive -Path runner.zip -DestinationPath .

# Configure
.\config.cmd --url https://github.com/mamivani/CREPRO `
  --token ghp_XXXXXXXXXXXXXXX `
  --unattended

# Run (keep this terminal open)
.\run.cmd
```

---

## Verify (1 minute)

### Check runner is connected:
Go to: https://github.com/mamivani/CREPRO/settings/actions/runners

✅ You should see your runner listed with a **green checkmark** and status **"Idle"**

### Trigger CI to test:
1. Go to: https://github.com/mamivani/CREPRO/pull/40
2. Click "..." menu → "Re-run all jobs"
3. Watch the `build-images` job
4. Should see Docker builds running (no billing errors!)

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Runner doesn't appear online | Check token is correct; restart runner process |
| Docker builds still fail | Ensure Docker is running on runner machine; check `docker ps` |
| "Can't access /var/run/docker.sock" | Add user to docker group: `sudo usermod -aG docker $USER` |
| Runner keeps disconnecting | Check network connection; increase timeout in config |

---

## Success Signs

✅ Runner shows "Idle" in settings  
✅ PR #40 CI starts running  
✅ build-images job shows Docker build logs  
✅ No billing errors in build output  
✅ All checks pass → PR #40 merges  
✅ Remaining 11 PRs merge automatically  

---

## Next Steps

1. ✅ Generate GitHub token
2. ✅ Run one of the three setup options above
3. ✅ Verify runner appears online
4. ✅ CI automatically re-runs and passes
5. ✅ All PRs merge without billing issues
6. ✅ Day 5 OAuth live on main! 🎉

---

## Full Documentation

For more details, see:
- **SELF_HOSTED_RUNNER_SETUP.md** - Comprehensive setup guide
- **IMPLEMENTATION_STATUS.md** - Technical details and troubleshooting

---

**Ready? Start with Option A (Docker) or your preferred method above!**
