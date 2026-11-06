# Self-Hosted Runner Setup Guide

## Overview
PR #40 has been created to update the CI workflows to use **self-hosted runners** for Docker builds, completely bypassing GitHub Actions billing limits. However, this requires you to set up at least one self-hosted runner on your infrastructure.

## Why Self-Hosted Runners?

The previous CI runs were blocked by GitHub Actions spending limits when building 13 Docker images in parallel. By using self-hosted runners:
- ✅ Docker builds run on your infrastructure (not GitHub-hosted)
- ✅ No consumption of GitHub Actions minutes
- ✅ Completely bypasses spending/billing limits
- ✅ All 15 pending PRs can merge without billing obstacles

## Current Status

- **PR #40** created with workflow updates
- **Status**: Waiting for self-hosted runner configuration
- **Blocker**: Container-scan jobs are PENDING because build-images (now requiring self-hosted) hasn't completed
- **Next Step**: Configure self-hosted runner on your infrastructure

## How to Set Up a Self-Hosted Runner

### Option 1: Docker Container (Recommended - Easiest)

Run a GitHub Actions runner in a Docker container on any machine:

```bash
# Create a runner directory
mkdir -p github-runner
cd github-runner

# Run the runner as a Docker container
docker run -d \
  -e RUNNER_ALLOW_RUNASROOT=true \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd):/home/runner \
  --name github-runner \
  myoung34/github-runner:latest \
  --url https://github.com/mamivani/CREPRO \
  --token YOUR_GITHUB_TOKEN \
  --unattended
```

### Option 2: Native Installation on Linux/macOS

```bash
# 1. Create a runner directory
mkdir actions-runner && cd actions-runner

# 2. Download the latest runner
curl -o actions-runner-linux-x64-latest.tar.gz -L https://github.com/actions/runner/releases/download/v2.317.0/actions-runner-linux-x64-2.317.0.tar.gz
tar xzf actions-runner-linux-x64-latest.tar.gz

# 3. Configure the runner
./config.sh --url https://github.com/mamivani/CREPRO --token YOUR_GITHUB_TOKEN

# 4. Run the runner
./run.sh
```

### Option 3: Native Installation on Windows

```powershell
# 1. Create runner directory
mkdir actions-runner
cd actions-runner

# 2. Download latest runner
Invoke-WebRequest -Uri "https://github.com/actions/runner/releases/download/v2.317.0/actions-runner-win-x64-2.317.0.zip" -OutFile "runner.zip"
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::ExtractToDirectory("$PWD\runner.zip", "$PWD")

# 3. Configure the runner
.\config.cmd --url https://github.com/mamivani/CREPRO --token YOUR_GITHUB_TOKEN

# 4. Run the runner
.\run.cmd
```

## Getting Your GitHub Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a name like "GitHub Actions Runner"
4. Check these scopes:
   - `repo` (Full control of private repositories)
   - `workflow` (Update GitHub Action workflows)
   - `admin:org_hook` (Full control of organization hooks)
5. Click "Generate token"
6. **Copy the token immediately** (you won't be able to see it again)
7. Use this token in the runner setup commands above

## Machine Requirements

Minimum specs for your self-hosted runner machine:
- **CPU**: 2+ cores (4+ recommended for Docker builds)
- **RAM**: 4 GB minimum (8+ GB recommended)
- **Disk**: 50+ GB free space (for Docker images and build artifacts)
- **Network**: Stable internet connection
- **Docker**: Required (must be installed on the machine)
- **Git**: Required
- **Python 3.13+**: Required (for test jobs)

## Verification Steps

1. **Verify runner is connected**:
   ```bash
   # Go to: https://github.com/mamivani/CREPRO/settings/actions/runners
   # You should see your runner listed with a green checkmark
   ```

2. **Check runner logs**:
   - If running in Docker: `docker logs github-runner`
   - If running natively: Look for logs in the runner directory

3. **Test by triggering a workflow**:
   - Go to: https://github.com/mamivani/CREPRO/actions
   - Click on any workflow
   - Click "Run workflow"
   - Select your branch
   - Click "Run workflow"
   - Watch the run to see if it uses your self-hosted runner

## Troubleshooting

### Runner shows offline/stale
- **Docker**: Restart the container: `docker restart github-runner`
- **Native**: Kill the process and run `./run.sh` or `./run.cmd` again
- **Check token**: Regenerate a new token if the old one expired

### Runner connects but doesn't run jobs
1. Verify the runner labels match the workflow `runs-on` value
2. Check that `docker` and `git` are available on the runner machine
3. Review runner logs for detailed error messages

### Docker images not building on self-hosted runner
1. Ensure Docker daemon is running on the runner machine
2. Verify the runner has permission to access Docker (user in `docker` group on Linux)
3. Check disk space: `docker system df`
4. Increase Docker memory limit if builds are timing out

### Can't generate GitHub token
- Make sure you're signed in to GitHub
- Check if you have permission to create tokens (usually available for personal accounts)
- Try creating a token with minimal scopes first, then add more as needed

## After Setup

Once your self-hosted runner is connected:

1. **Go to PR #40**: https://github.com/mamivani/CREPRO/pull/40
2. **Wait for CI to re-run** (or manually trigger it)
3. **All Docker builds should now complete** without billing errors
4. **PR #40 will auto-merge** once all checks pass
5. **Remaining 11 PRs will merge sequentially** without billing blocks

## Docker Runner Persistence

To keep the runner running permanently:

### Docker with systemd (Linux)
```bash
# Create a systemd service file
sudo tee /etc/systemd/system/github-runner.service > /dev/null <<'EOF'
[Unit]
Description=GitHub Actions Runner
After=docker.service
Requires=docker.service

[Service]
Type=simple
ExecStart=/usr/bin/docker run -d \
  -e RUNNER_ALLOW_RUNASROOT=true \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /opt/github-runner:/home/runner \
  myoung34/github-runner:latest
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable github-runner
sudo systemctl start github-runner
```

### Docker with restart policy
```bash
docker run -d --restart=always \
  -e RUNNER_ALLOW_RUNASROOT=true \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd):/home/runner \
  --name github-runner \
  myoung34/github-runner:latest
```

## Next Steps

1. ✅ PR #40 is ready (workflow changes)
2. ⏳ Set up self-hosted runner (you are here)
3. ⏳ Verify runner connection
4. ⏳ PR #40 will auto-merge once checks pass
5. ⏳ All 11 blocked PRs will merge sequentially
6. ⏳ Day 5 OAuth implementation (PR #39) will merge to main

## Questions?

- GitHub Actions Runner Docs: https://docs.github.com/en/actions/hosting-your-own-runners
- GitHub Actions Self-Hosted Runner Config: https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/adding-self-hosted-runners
- Docker Runner: https://github.com/myoung34/docker-github-actions-runner
