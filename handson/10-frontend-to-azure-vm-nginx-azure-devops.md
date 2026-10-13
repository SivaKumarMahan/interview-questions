# Hands-on 10: Deploy a Frontend App to an Azure VM with Nginx Using Azure DevOps

> Build a frontend app with lint, tests, SonarQube, and dependency scanning, then deploy it to an Nginx web server on an Azure VM in two ways: an Azure DevOps Environment with a VM resource, or an SSH service connection.

**Time:** about 2 hours. **Level:** Intermediate.

## What you practise

- A CI stage for a Node.js frontend: `npm ci`, lint, tests, and build
- SonarQube analysis with a quality gate that can fail the pipeline
- SCA (software composition analysis) with `npm audit` and Trivy
- Packaging the build output as one versioned pipeline artifact
- **Option A:** an Azure DevOps Environment with a Virtual machine resource (agent on the VM, no inbound SSH)
- **Option B:** an SSH service connection with `CopyFilesOverSSH@0` and `SSH@0`
- Nginx configuration for a single-page app (SPA)
- Release folders and a `current` symlink for fast rollback
- Approvals and checks before production

## Prerequisites

| Item | Purpose |
| --- | --- |
| Azure DevOps project with a repo containing a Node.js frontend | Source code and pipeline (for example React, Vue, or Angular with `build` and `lint` scripts) |
| Azure Linux VM (Ubuntu 22.04 or 24.04) | Web server that runs Nginx |
| SonarQube server and a SonarQube service connection | Code-quality stage |
| Option A: permission to create Environments, and a PAT or admin rights to run the registration script | Register the VM as an environment resource |
| Option B: SSH key pair and network path from the agent to the VM on port 22 | SSH service connection |
| Self-hosted agent inside the VNet (Option B only, recommended) | Reach the VM over a private IP |

## Flow

```text
Push / PR to main
      |
      v
CI stage (Microsoft-hosted or self-hosted agent)
  NodeTool -> npm ci -> npm run lint -> npm test
      |
      v
  SonarQube prepare -> analyze -> publish (wait for quality gate)
      |
      v
  SCA: npm audit --audit-level=high  +  trivy fs (HIGH, CRITICAL)
      |
      v
  npm run build -> ArchiveFiles (tar.gz) -> PublishPipelineArtifact
      |
      v
Approval on environment frontend-prod
      |
      +------------------------------+-------------------------------+
      |                                                              |
Option A: Environment VM resource                     Option B: SSH service connection
  agent on the VM pulls the job (outbound 443)          agent pushes files over SSH (port 22)
  download artifact on the VM                           CopyFilesOverSSH -> VM /tmp
  extract -> releases/<BuildId>                         SSH inline script:
  switch symlink current -> new release                   extract -> releases/<BuildId>
  nginx -t -> reload -> curl health check                 switch symlink -> nginx -t -> reload
      |                                                              |
      +------------------------------+-------------------------------+
                                     |
                                     v
                Nginx serves /var/www/frontend/current
```

## Steps

### 1. Prepare the VM

Install Nginx and create the folder layout:

```bash
sudo apt-get update
sudo apt-get install -y nginx
sudo systemctl enable --now nginx

sudo mkdir -p /var/www/frontend/releases
```

Create a deploy user. For Option B this is the SSH user. For Option A, use the user that the environment agent runs as (step 5), or run the agent as this user.

```bash
sudo adduser --disabled-password --gecos "" deploy
sudo chown -R deploy:deploy /var/www/frontend
```

Give the deploy user **only** the sudo rights it needs: test the Nginx config and reload Nginx. Nothing else.

```bash
sudo visudo -f /etc/sudoers.d/deploy-nginx
```

```text
deploy ALL=(root) NOPASSWD: /usr/sbin/nginx -t, /usr/bin/systemctl reload nginx
```

Check the paths with `which nginx` and `which systemctl`, and test the rule:

```bash
sudo -l -U deploy
```

Nginx (user `www-data`) only needs to **read** the files. The default permissions (folders `755`, files `644`) are enough.

### 2. Configure Nginx for the SPA

`/etc/nginx/sites-available/frontend`:

```nginx
server {
    listen 80;
    server_name app.example.com;

    root /var/www/frontend/current;
    index index.html;

    # SPA routing: unknown paths go to index.html so the client router handles them
    location / {
        try_files $uri $uri/ /index.html;
    }

    # index.html must not be cached, so users get the new release at once
    location = /index.html {
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }

    # Built assets have a hash in the file name, so they can be cached for a long time
    location ~* \.(js|css|png|jpg|jpeg|gif|svg|ico|woff2?)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
        try_files $uri =404;
    }

    location = /healthz {
        access_log off;
        return 200 "ok\n";
    }
}
```

Enable it:

```bash
sudo ln -s /etc/nginx/sites-available/frontend /etc/nginx/sites-enabled/frontend
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

`root` points at the `current` symlink. A deployment only changes where the symlink points; the Nginx config does not change.

In production, add HTTPS (a certificate from Key Vault or Let's Encrypt) and put the VM behind Application Gateway or a load balancer.

### 3. Create the CI stage

This stage is the same for both deployment options. `azure-pipelines.yml`:

```yaml
trigger:
  branches:
    include:
      - main

variables:
  nodeVersion: '20.x'
  artifactName: frontend
  archiveName: frontend-$(Build.BuildId).tar.gz

stages:
  - stage: CI
    pool:
      vmImage: ubuntu-latest
    jobs:
      - job: BuildAndScan
        steps:
          - task: NodeTool@0
            displayName: Install Node.js
            inputs:
              versionSpec: $(nodeVersion)

          - script: npm ci
            displayName: npm ci

          - script: npm run lint
            displayName: Lint

          - script: npm test --if-present
            displayName: Unit tests
            env:
              CI: 'true'

          - task: SonarQubePrepare@7
            inputs:
              SonarQube: sonarqube-connection
              scannerMode: cli
              configMode: manual
              cliProjectKey: frontend-app
              cliSources: src
              extraProperties: |
                sonar.qualitygate.wait=true
                sonar.qualitygate.timeout=300
                sonar.javascript.lcov.reportPaths=coverage/lcov.info
          - task: SonarQubeAnalyze@7
          - task: SonarQubePublish@7
            inputs:
              pollingTimeoutSec: '300'

          - script: npm audit --audit-level=high
            displayName: SCA - npm audit

          - script: |
              curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh \
                | sh -s -- -b /usr/local/bin v0.58.1
              trivy fs --scanners vuln --severity HIGH,CRITICAL --exit-code 1 .
            displayName: SCA - Trivy filesystem scan

          - script: npm run build
            displayName: Build

          - task: ArchiveFiles@2
            displayName: Archive build output
            inputs:
              rootFolderOrFile: dist          # use build/ for Create React App
              includeRootFolder: false
              archiveType: tar
              tarCompression: gz
              archiveFile: $(Build.ArtifactStagingDirectory)/$(archiveName)

          - task: PublishPipelineArtifact@1
            displayName: Publish artifact
            inputs:
              targetPath: $(Build.ArtifactStagingDirectory)/$(archiveName)
              artifact: $(artifactName)
```

Notes:

- `npm ci` installs exactly what is in `package-lock.json`, so the build is repeatable.
- `sonar.qualitygate.wait=true` makes the analyze step wait for the quality gate and fail the pipeline if the gate fails.
- `npm audit` and `trivy fs` both check dependencies for known CVEs. Trivy also reads other lock files in the repo. Pin the Trivy version you have checked, instead of installing the latest.
- **OWASP Dependency-Check** is another SCA option (`dependency-check.sh --scan . --failOnCVSS 7`). It needs the NVD database, so cache it between runs.
- The archive name includes the build ID, so every artifact is unique and traceable.

### 4. Choose a deployment option

Both options deploy the same artifact into the same folder layout:

```text
/var/www/frontend/
├── releases/
│   ├── 1041/          # previous release
│   └── 1042/          # new release
└── current -> releases/1042
```

| Topic | Option A: Environment VM resource | Option B: SSH service connection |
| --- | --- | --- |
| Network direction | Outbound from the VM to Azure DevOps on 443 | Inbound to the VM on port 22 from the agent |
| Open ports on the VM | None needed for deployment | Port 22 from the agent subnet only |
| Where steps run | On the VM itself (agent installed there) | On the pipeline agent; commands sent over SSH |
| Credentials | Agent registered once with a PAT; no SSH key in the pipeline | Private key stored in the service connection |
| Approvals and checks | On the environment (approvals, business hours, branch control) | On the service connection, or use a deployment job with an environment |
| Many VMs | Built in: tags plus `rolling` strategy with `maxParallel` | One service connection per VM, or a loop in a script |
| Deployment history | Per VM in the environment view | Only in pipeline runs |
| Extra software on the VM | Azure Pipelines agent | Nothing (SSH server only) |

### 5. Option A: create the environment and register the VM

1. Go to **Pipelines -> Environments -> New environment**.
2. Name: `frontend-prod`. Resource: **Virtual machines**. Select **Next**.
3. Provider: **Generic provider**. OS: **Linux**.
4. Copy the registration script. It contains a PAT (or asks for one).
5. Run the script on the VM over Bastion or the serial console:

```bash
# paste the copied script, for example:
mkdir azagent; cd azagent
# ... the generated script downloads the agent, configures it, and installs it as a service
```

6. When the script asks for tags, enter `web`. You can also add tags later in the environment view.

The script installs an Azure Pipelines agent as a systemd service. The agent connects **outbound** to Azure DevOps over HTTPS (443) and pulls jobs. Azure DevOps never connects in to the VM, so you do not need to open SSH for deployments.

Check the agent service and the user it runs as:

```bash
systemctl list-units 'vsts.agent.*'
systemctl status 'vsts.agent.*'
```

Give that user the same sudoers rule and folder ownership as `deploy` in step 1 (replace `deploy` with the agent user).

7. In the environment, open **Approvals and checks** and add an **Approvals** check with the release approvers. You can also add **Branch control** (only `refs/heads/main` can deploy) and **Business hours**.

### 6. Option A: add the deployment stage

Add this stage after the CI stage:

```yaml
  - stage: DeployVM
    displayName: Deploy to VM (environment resource)
    dependsOn: CI
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    jobs:
      - deployment: DeployWeb
        displayName: Deploy frontend to web VMs
        environment:
          name: frontend-prod
          resourceType: VirtualMachine
          tags: web
        strategy:
          runOnce:
            deploy:
              steps:
                - download: current
                  artifact: $(artifactName)

                - script: |
                    set -euo pipefail
                    RELEASE_DIR=/var/www/frontend/releases/$(Build.BuildId)
                    ARCHIVE=$(Pipeline.Workspace)/$(artifactName)/$(archiveName)

                    mkdir -p "$RELEASE_DIR"
                    tar -xzf "$ARCHIVE" -C "$RELEASE_DIR"

                    # switch the symlink to the new release
                    ln -sfn "$RELEASE_DIR" /var/www/frontend/current

                    sudo nginx -t
                    sudo systemctl reload nginx

                    # keep the last 5 releases
                    cd /var/www/frontend/releases
                    ls -1t | tail -n +6 | xargs -r rm -rf
                  displayName: Extract, switch symlink, reload Nginx

                - script: |
                    curl -fsS http://localhost/healthz
                    curl -fsS http://localhost/ | grep -qi "<html"
                  displayName: Health check
```

Notes:

- Every step in the deployment job runs **on the VM**, because the VM is the agent.
- `download: current` downloads the artifact of the current run to `$(Pipeline.Workspace)/<artifact name>`.
- `ln -sfn` replaces the symlink in one step. For a fully atomic switch, create a temporary link and rename it: `ln -s "$RELEASE_DIR" current.tmp && mv -T current.tmp current`.
- The approval on `frontend-prod` pauses the stage before any step runs on the VM.

For **many VMs**, tag them all `web` and use the `rolling` strategy, so only part of the fleet is updated at a time:

```yaml
        strategy:
          rolling:
            maxParallel: 1          # or a percentage, for example 25%
            deploy:
              steps:
                - download: current
                  artifact: $(artifactName)
                # same extract, symlink, reload, and health check steps
```

If a VM fails its health check, the rolling deployment stops, and the other VMs keep the old release.

### 7. Option B: create the SSH service connection

1. Create a key pair for the pipeline (on your machine, not the VM):

```bash
ssh-keygen -t ed25519 -f ./frontend-deploy -C "azure-devops-deploy" -N ""
```

2. Add the public key to the deploy user on the VM:

```bash
sudo mkdir -p /home/deploy/.ssh
sudo tee -a /home/deploy/.ssh/authorized_keys < frontend-deploy.pub
sudo chown -R deploy:deploy /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
sudo chmod 600 /home/deploy/.ssh/authorized_keys
```

3. In **Project settings -> Service connections -> New -> SSH**, enter:
   - Host name: the **private** IP of the VM, for example `10.10.1.4`
   - Port: `22`
   - User name: `deploy`
   - Private key: paste the content of `frontend-deploy`
   - Name: `vm-frontend-ssh`
4. Delete the local private key file. The key lives **only** in the service connection.
5. On the service connection, add **Approvals and checks** if you want, and do not grant access to all pipelines.

Network rule: the agent must reach the VM on port 22. Use a **self-hosted agent inside the same VNet** (or a peered VNet), or reach the VM through a VPN. Allow port 22 in the NSG **only** from the agent subnet. **Never** open port 22 to the internet. A Microsoft-hosted agent cannot reach a private IP.

### 8. Option B: add the deployment stage

```yaml
  - stage: DeploySSH
    displayName: Deploy to VM (SSH)
    dependsOn: CI
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    pool:
      name: vnet-linux-agents          # self-hosted agent pool inside the VNet
    jobs:
      - deployment: DeployWebSSH
        environment: frontend-prod-ssh  # environment with no resources, used for approvals
        strategy:
          runOnce:
            deploy:
              steps:
                - download: current
                  artifact: $(artifactName)

                - task: CopyFilesOverSSH@0
                  displayName: Copy artifact to VM
                  inputs:
                    sshEndpoint: vm-frontend-ssh
                    sourceFolder: $(Pipeline.Workspace)/$(artifactName)
                    contents: '*.tar.gz'
                    targetFolder: /tmp/frontend-deploy
                    cleanTargetFolder: true

                - task: SSH@0
                  displayName: Extract, switch symlink, reload Nginx
                  inputs:
                    sshEndpoint: vm-frontend-ssh
                    runOptions: inline
                    failOnStdErr: false        # nginx -t writes to stderr even on success
                    inline: |
                      set -euo pipefail
                      RELEASE_DIR=/var/www/frontend/releases/$(Build.BuildId)
                      mkdir -p "$RELEASE_DIR"
                      tar -xzf /tmp/frontend-deploy/$(archiveName) -C "$RELEASE_DIR"
                      ln -sfn "$RELEASE_DIR" /var/www/frontend/current
                      sudo nginx -t
                      sudo systemctl reload nginx
                      rm -rf /tmp/frontend-deploy
                      curl -fsS http://localhost/healthz
```

Notes:

- Here the steps run on the **agent**. Only the inline script runs on the VM, as the `deploy` user.
- `failOnStdErr: false` is needed because `nginx -t` prints its result to stderr. `set -e` still fails the step on a real error.
- `$(Build.BuildId)` and `$(archiveName)` are replaced by Azure DevOps before the script is sent to the VM.
- For several VMs, add one service connection per VM and repeat the two tasks, or deploy one VM at a time with a matrix or a loop.

### 9. Verify the deployment

On the VM:

```bash
readlink -f /var/www/frontend/current
ls -1 /var/www/frontend/releases
sudo nginx -t
curl -I http://localhost/
curl -I http://localhost/some/client/route
```

Expected results:

- `current` points to `/var/www/frontend/releases/<latest BuildId>`.
- `nginx -t` prints `syntax is ok` and `test is successful`.
- `/` returns `200` with `Cache-Control: no-cache, no-store, must-revalidate`.
- A client-side route such as `/some/client/route` also returns `200` (served by `index.html`).
- In Azure DevOps, **Environments -> frontend-prod** shows the run as the latest deployment on the VM (Option A).

### 10. Roll back

Point the symlink to the previous release and reload Nginx:

```bash
cd /var/www/frontend/releases
ls -1t                                   # newest first
PREVIOUS=$(ls -1t | sed -n 2p)
ln -sfn /var/www/frontend/releases/$PREVIOUS /var/www/frontend/current
sudo nginx -t && sudo systemctl reload nginx
```

Rollback takes seconds because the old files are still on disk. For a repeatable rollback, re-run the deployment stage of an older pipeline run: it deploys that run's artifact again.

## Important points

- Build once, deploy the same artifact everywhere. Never run `npm run build` on the VM.
- Option A needs no inbound port for deployment. This is the safer default for VMs.
- Option B needs port 22 from the agent. Keep it private: self-hosted agent in the VNet, NSG rule from the agent subnet only.
- Store SSH keys only in the service connection. Do not put them in variables, repos, or agent disks.
- Limit sudo to `nginx -t` and `systemctl reload nginx`. The deploy user does not need full root.
- Do not cache `index.html`. Cache hashed assets for a long time.
- SonarQube is SAST and code quality on **your** code. SCA checks **third-party** dependencies. You need both.
- Add approvals and branch control on the production environment.

## Common problems

| Problem | Likely cause | Fix |
| --- | --- | --- |
| Nginx returns 403 Forbidden | `www-data` cannot read the files, or the folder has no `index.html` | Set folders to `755` and files to `644`; check that the archive was created with `includeRootFolder: false` |
| Nginx returns 404 for `/` | `root` path is wrong or the symlink points to a missing folder | Run `readlink -f /var/www/frontend/current` and fix `root` |
| Refreshing a page like `/dashboard` returns 404 | Nginx looks for a real file at that path | Add `try_files $uri $uri/ /index.html;` |
| Users still see the old version | Browser cached `index.html` | Add `Cache-Control: no-cache` for `index.html` |
| `CopyFilesOverSSH` or `SSH` task times out | NSG blocks port 22, or a Microsoft-hosted agent cannot reach the private IP | Use a self-hosted agent in the VNet; allow port 22 from its subnet only |
| `Permission denied (publickey)` | Public key not in `authorized_keys`, or wrong permissions on `.ssh` | Check the key and set `700` on `.ssh`, `600` on `authorized_keys` |
| `sudo: a password is required` | Sudoers rule missing or the command path differs | Check `sudo -l -U deploy` and the full path from `which nginx` |
| Environment VM shows **Offline** | Agent service stopped, or outbound 443 blocked | `sudo systemctl start 'vsts.agent.*'`; allow outbound HTTPS to `dev.azure.com` |
| Deployment job waits for an agent forever | No VM in the environment has the tag `web` | Add the tag on the VM resource in the environment |
| SonarQube step fails with quality gate error | New code has bugs, low coverage, or duplications | Open the SonarQube project, fix the issues, or agree a change to the gate |
| `npm audit` or Trivy fails the build | A dependency has a HIGH or CRITICAL CVE | Upgrade the package (`npm audit fix` or a new version); document an exception only if there is no fix |

## Clean up

```bash
# on the VM: remove the agent (Option A)
cd ~/azagent
sudo ./svc.sh stop
sudo ./svc.sh uninstall
./config.sh remove

# remove the site and files
sudo rm -f /etc/nginx/sites-enabled/frontend /etc/nginx/sites-available/frontend
sudo rm -rf /var/www/frontend
sudo rm -f /etc/sudoers.d/deploy-nginx
sudo systemctl reload nginx
```

In Azure DevOps, delete the environment `frontend-prod` (and `frontend-prod-ssh`) and the SSH service connection. Delete the VM resource group if you created it only for this lab.

## Interview questions

<details><summary>Q1. What is the difference between deploying with an Environment VM resource and with an SSH service connection?</summary>

With an Environment VM resource, an Azure Pipelines agent is installed on the VM. It connects outbound to Azure DevOps over HTTPS and pulls the deployment job, so the steps run on the VM and no inbound port is needed. I also get tags, rolling deployments, per-VM history, and approvals on the environment.

With an SSH service connection, the pipeline agent connects in to the VM on port 22, copies files with `CopyFilesOverSSH`, and runs commands with the `SSH` task. Nothing is installed on the VM, but the agent must reach port 22, so I use a self-hosted agent inside the VNet. I prefer the environment option for production VMs.

</details>

<details><summary>Q2. How do you roll back a frontend deployment on a VM?</summary>

Each deployment extracts to its own folder, such as `releases/<BuildId>`, and Nginx serves a `current` symlink. To roll back, I point the symlink to the previous release folder and reload Nginx. It takes seconds and needs no rebuild. I keep the last few releases on disk. I can also re-run the deployment stage of an older pipeline run, which deploys that exact artifact again.

</details>

<details><summary>Q3. How is SCA different from SAST?</summary>

SAST (for example SonarQube) analyses the source code that my team writes. It finds bugs, code smells, and security issues such as injection in our own code. SCA (for example `npm audit`, Trivy, or OWASP Dependency-Check) checks the third-party packages we use against known vulnerability databases (CVEs) and can also check licenses. Most frontend code is dependencies, so SCA is very important, but both are needed.

</details>

<details><summary>Q4. How do you secure access to the VM during deployments?</summary>

I prefer the Environment VM resource, because the agent connects outbound and no inbound port is opened. If I must use SSH, the VM has only a private IP, port 22 is allowed only from the self-hosted agent subnet, and the private key is stored only in the service connection. The deploy user has no password and can run only `nginx -t` and `systemctl reload nginx` with sudo. Admins use Azure Bastion, not public SSH. The production environment has approvals and branch control, and the service connection is not open to all pipelines.

</details>

<details><summary>Q5. How do you deploy to many VMs without downtime?</summary>

I put the VMs behind a load balancer or Application Gateway with a health probe. In the environment, I tag all web VMs and use the `rolling` strategy with `maxParallel`, so only one VM (or a small percentage) is updated at a time. Each VM gets a health check after the symlink switch. If a check fails, the deployment stops and the other VMs keep serving the old release. Nginx `reload` also keeps existing connections alive while it loads the new files.

</details>
