# Hands-on 9: Deploy a Java WAR to Tomcat with Azure DevOps on a Windows Self-Hosted Agent

> Build a Java web app with Maven in Azure DevOps and deploy the WAR to Apache Tomcat 9 on a Windows server, with an automatic restart and health check, using a self-hosted agent on that server.

**Time:** about 90 minutes. **Level:** Intermediate.

## What you practise

- Installing and registering a Windows self-hosted agent as a service
- Installing Tomcat 9 as a Windows service and setting `JAVA_HOME` and `CATALINA_HOME`
- Building a WAR with the `Maven@4` task and publishing JUnit results
- Deploying with PowerShell: stop Tomcat, replace the WAR, start Tomcat
- A health check that fails the pipeline if the app does not return HTTP 200
- Optional: deploying through the Tomcat Manager text API
- Rollback by keeping the previous WAR

## Prerequisites

| Item | Purpose |
| --- | --- |
| Windows Server (or Windows 10/11) VM | Runs the agent and Tomcat |
| JDK 17 (for example Eclipse Temurin 17) | Build and run the app |
| Apache Maven 3.9.x on the `PATH` | Maven build on the agent |
| Apache Tomcat 9 (Windows zip or installer) | Application server |
| Azure DevOps project with the app repository | Pipeline and source code |
| Personal access token (PAT) with **Agent Pools (read, manage)** scope | Registering the agent |
| Agent pool named `windows-selfhosted` | Pool the pipeline runs on |

## Flow

```text
git push (main)
     |
     v
Azure DevOps pipeline  -->  pool: windows-selfhosted (agent on the Tomcat server)
     |
     |-- Maven clean package  -->  target\login-showcase.war + JUnit results
     |-- Publish pipeline artifact
     |
     '-- Deploy (PowerShell)
            Stop-Service Tomcat9
            backup old WAR, remove old WAR + exploded folder
            Copy-Item WAR  -->  %CATALINA_HOME%\webapps\login-showcase.war
            Start-Service Tomcat9
            health check  -->  http://localhost:8080/login-showcase/  (200 or fail)
```

## Steps

### 1. Install the JDK and set the system variables

Install JDK 17, then open PowerShell **as Administrator**:

```powershell
# Adjust the paths to match your installation
[Environment]::SetEnvironmentVariable("JAVA_HOME", "C:\Program Files\Eclipse Adoptium\jdk-17.0.12.7-hotspot", "Machine")
[Environment]::SetEnvironmentVariable("CATALINA_HOME", "C:\tomcat9", "Machine")

# Add the JDK and Maven to the machine PATH
$path = [Environment]::GetEnvironmentVariable("Path", "Machine")
[Environment]::SetEnvironmentVariable("Path", "$path;C:\Program Files\Eclipse Adoptium\jdk-17.0.12.7-hotspot\bin;C:\tools\apache-maven-3.9.9\bin", "Machine")
```

Open a new PowerShell window and check:

```powershell
java -version      # should show 17
mvn -version       # should show Java version: 17
echo $env:JAVA_HOME
echo $env:CATALINA_HOME
```

`JAVA_HOME` must point to the **JDK** folder (the one that contains `bin\javac.exe`), not to a JRE and not to the `bin` folder.

### 2. Install Tomcat 9 as a Windows service

Extract the Tomcat 9 Windows zip to `C:\tomcat9`. Then, in an **Administrator** command prompt:

```bat
cd C:\tomcat9\bin
service.bat install Tomcat9
```

```powershell
Set-Service -Name Tomcat9 -StartupType Automatic
Start-Service Tomcat9
Get-Service Tomcat9
Invoke-WebRequest http://localhost:8080/ -UseBasicParsing | Select-Object StatusCode
```

Expected: the service is `Running` and the Tomcat home page returns `200`.

Note: the service stores the JVM path when it is installed. If you change `JAVA_HOME` later, update it in `C:\tomcat9\bin\Tomcat9w.exe` (the service configuration tool) or reinstall the service.

### 3. Create a service account and give it the rights it needs

The agent runs as a Windows service. That account must be able to write to the Tomcat `webapps` folder and to stop and start the `Tomcat9` service.

```powershell
# Local account for the agent (use a domain or managed service account in real environments)
$pw = Read-Host -AsSecureString "Password for svc-azagent"
New-LocalUser -Name "svc-azagent" -Password $pw -PasswordNeverExpires

# Modify rights on the webapps folder and a backup folder
New-Item -ItemType Directory -Path C:\deploy\backup -Force
icacls "C:\tomcat9\webapps" /grant "svc-azagent:(OI)(CI)M"
icacls "C:\deploy" /grant "svc-azagent:(OI)(CI)M"
```

To stop and start a service, a non-admin account needs rights on that service. For a lab, the quick way is to add the account to the local Administrators group:

```powershell
Add-LocalGroupMember -Group "Administrators" -Member "svc-azagent"
```

For production, give only the needed rights on the `Tomcat9` service (for example with `sc.exe sdset Tomcat9 ...` or Group Policy) instead of making the account an administrator.

### 4. Download and register the self-hosted agent

1. In Azure DevOps, go to **Project settings > Agent pools**, create a pool named `windows-selfhosted`.
2. Click **New agent > Windows**, and download the agent zip.
3. Extract it and register it from an **Administrator** PowerShell:

```powershell
mkdir C:\agent
cd C:\agent
Expand-Archive -Path "$env:USERPROFILE\Downloads\vsts-agent-win-x64-*.zip" -DestinationPath C:\agent

.\config.cmd --unattended `
  --url https://dev.azure.com/my-org `
  --auth pat --token <PAT> `
  --pool windows-selfhosted `
  --agent win-tomcat-01 `
  --runAsService `
  --windowsLogonAccount ".\svc-azagent" `
  --windowsLogonPassword "<password>"
```

Check that the agent is **Online** in the pool. The agent reads environment variables when it starts, so if you change `JAVA_HOME` or `PATH` later, restart the agent service (its name starts with `vstsagent.`).

### 5. Prepare the Maven project

In `pom.xml`, package the app as a WAR and target Java 17:

```xml
<packaging>war</packaging>

<properties>
  <maven.compiler.release>17</maven.compiler.release>
  <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
</properties>

<dependencies>
  <!-- Tomcat 9 = javax.servlet. Tomcat provides it, so scope is provided. -->
  <dependency>
    <groupId>javax.servlet</groupId>
    <artifactId>javax.servlet-api</artifactId>
    <version>4.0.1</version>
    <scope>provided</scope>
  </dependency>
  <dependency>
    <groupId>org.junit.jupiter</groupId>
    <artifactId>junit-jupiter</artifactId>
    <version>5.10.3</version>
    <scope>test</scope>
  </dependency>
</dependencies>

<build>
  <finalName>login-showcase</finalName>
  <plugins>
    <plugin>
      <groupId>org.apache.maven.plugins</groupId>
      <artifactId>maven-war-plugin</artifactId>
      <version>3.4.0</version>
    </plugin>
    <plugin>
      <groupId>org.apache.maven.plugins</groupId>
      <artifactId>maven-surefire-plugin</artifactId>
      <version>3.2.5</version>
    </plugin>
  </plugins>
</build>
```

**Servlet API must match Tomcat.** Tomcat 9 uses `javax.servlet.*`. Tomcat 10 and later use `jakarta.servlet.*`. An app compiled against `jakarta.servlet` fails on Tomcat 9, and a `javax.servlet` app fails on Tomcat 10+ (unless migrated).

`finalName` sets the WAR file name. Tomcat uses the WAR file name as the context path, so `login-showcase.war` is served at `/login-showcase/`.

Build locally once:

```powershell
mvn clean package
dir target\*.war
```

### 6. Create the pipeline

`azure-pipelines.yml`:

```yaml
trigger:
  branches:
    include:
      - main

pool:
  name: windows-selfhosted

variables:
  contextPath: login-showcase
  tomcatService: Tomcat9
  backupDir: C:\deploy\backup

steps:
  - task: Maven@4
    displayName: Maven clean package
    inputs:
      mavenPomFile: pom.xml
      goals: clean package
      javaHomeOption: Path
      jdkDirectory: $(JAVA_HOME)       # the machine JAVA_HOME on the agent
      mavenVersionOption: Default      # uses mvn from the PATH
      publishJUnitResults: true
      testResultsFiles: '**/surefire-reports/TEST-*.xml'

  - task: PublishPipelineArtifact@1
    displayName: Publish WAR
    inputs:
      targetPath: target/$(contextPath).war
      artifact: war

  - task: PowerShell@2
    displayName: Deploy WAR to Tomcat
    inputs:
      targetType: inline
      errorActionPreference: stop
      script: |
        $webapps = Join-Path $env:CATALINA_HOME "webapps"
        $war     = Join-Path $webapps "$(contextPath).war"
        $folder  = Join-Path $webapps "$(contextPath)"
        $newWar  = "$(Build.SourcesDirectory)\target\$(contextPath).war"

        Write-Host "Stopping $(tomcatService)"
        Stop-Service -Name "$(tomcatService)"
        (Get-Service "$(tomcatService)").WaitForStatus('Stopped', '00:01:00')

        # Keep the previous WAR for rollback
        if (Test-Path $war) {
          Copy-Item $war "$(backupDir)\$(contextPath)-previous.war" -Force
          Remove-Item $war -Force
        }
        if (Test-Path $folder) { Remove-Item $folder -Recurse -Force }

        Copy-Item $newWar $war -Force
        Write-Host "Copied $newWar to $war"

        Write-Host "Starting $(tomcatService)"
        Start-Service -Name "$(tomcatService)"

  - task: PowerShell@2
    displayName: Health check
    inputs:
      targetType: inline
      script: |
        $url = "http://localhost:8080/$(contextPath)/"
        $ok = $false
        for ($i = 1; $i -le 10; $i++) {
          try {
            $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 10
            if ($r.StatusCode -eq 200) { $ok = $true; break }
          } catch {
            $msg = $_.Exception.Message
            Write-Host "Attempt $i failed: $msg"
          }
          Start-Sleep -Seconds 10
        }
        if (-not $ok) {
          Write-Host "##vso[task.logissue type=error]Health check failed for $url"
          exit 1
        }
        Write-Host "App is up at $url"
```

Notes:

- `jdkDirectory: $(JAVA_HOME)` uses the machine variable, which the agent exposes as a pipeline variable. Another option is `javaHomeOption: JDKVersion` with `jdkVersionOption: '1.17'`, but on a self-hosted agent that needs a `JAVA_HOME_17_X64` environment variable to exist.
- `$env:CATALINA_HOME` is read from the agent's environment, so it must be a machine variable and the agent must have been restarted after it was set.
- The health check waits up to about 100 seconds, because Tomcat needs time to start and unpack the WAR.

### 7. Optional: deploy with the Tomcat Manager text API

Instead of stopping the service, Tomcat can hot-deploy through the Manager app. Add a user with the `manager-script` role in `C:\tomcat9\conf\tomcat-users.xml`:

```xml
<role rolename="manager-script"/>
<user username="deployer" password="CHANGE_ME" roles="manager-script"/>
```

Store the password in the pipeline as a **secret variable** named `tomcatPassword`. Secret variables are not passed to scripts automatically, so map them with `env`:

```yaml
  - task: PowerShell@2
    displayName: Deploy with Tomcat Manager
    inputs:
      targetType: inline
      script: |
        $user = "deployer"
        $pass = $env:TOMCAT_PASSWORD
        $war  = "$(Build.SourcesDirectory)\target\$(contextPath).war"
        curl.exe --fail -u "${user}:${pass}" -T $war `
          "http://localhost:8080/manager/text/deploy?path=/$(contextPath)&update=true"
        if ($LASTEXITCODE -ne 0) { exit 1 }
    env:
      TOMCAT_PASSWORD: $(tomcatPassword)
```

A successful response starts with `OK - Deployed application at context path`. Keep the Manager app reachable only from localhost (the default `RemoteAddrValve` in `webapps\manager\META-INF\context.xml` does this).

### 8. Run and verify

Push to `main` and watch the run.

```powershell
# On the server
Get-Service Tomcat9
dir $env:CATALINA_HOME\webapps
Get-Content "$env:CATALINA_HOME\logs\catalina.$(Get-Date -Format yyyy-MM-dd).log" -Tail 50
Invoke-WebRequest http://localhost:8080/login-showcase/ -UseBasicParsing | Select-Object StatusCode
```

Expected:

- The pipeline shows the Maven build, a **Tests** tab with JUnit results, a `war` artifact, and green deploy and health check steps.
- `webapps` contains `login-showcase.war` and the exploded `login-showcase` folder.
- The app login page opens at http://localhost:8080/login-showcase/.

### 9. Roll back

```powershell
Stop-Service Tomcat9
Remove-Item "$env:CATALINA_HOME\webapps\login-showcase" -Recurse -Force
Copy-Item C:\deploy\backup\login-showcase-previous.war "$env:CATALINA_HOME\webapps\login-showcase.war" -Force
Start-Service Tomcat9
```

A cleaner rollback is to re-run the deploy stage of an earlier successful run, which redeploys that run's artifact.

## Better practice: separate build and deploy stages

The single job above is easy to follow. In real projects, split it:

```yaml
stages:
  - stage: Build
    jobs:
      - job: Build
        pool:
          name: windows-selfhosted     # or a Microsoft-hosted agent
        steps:
          - task: Maven@4
            inputs:
              mavenPomFile: pom.xml
              goals: clean package
              javaHomeOption: Path
              jdkDirectory: $(JAVA_HOME)
              publishJUnitResults: true
              testResultsFiles: '**/surefire-reports/TEST-*.xml'
          - task: PublishPipelineArtifact@1
            inputs:
              targetPath: target/login-showcase.war
              artifact: war

  - stage: DeployDev
    dependsOn: Build
    jobs:
      - deployment: DeployTomcat
        pool:
          name: windows-selfhosted
        environment: tomcat-dev          # add an approval check here
        strategy:
          runOnce:
            deploy:
              steps:
                # The artifact is downloaded to $(Pipeline.Workspace)\war
                - task: PowerShell@2
                  inputs:
                    targetType: inline
                    script: |
                      Write-Host "Deploying $(Pipeline.Workspace)\war\login-showcase.war"
                      # same stop / backup / copy / start / health check as step 6
```

- The deploy stage uses the **same artifact** that was built and tested, not a new build.
- The **environment** records every deployment and can require an approval before Prod.
- Keep the previous WAR (or rely on old run artifacts) so rollback is quick.
- Add a `DeployProd` stage that targets a Prod agent or environment with its own approval.

## Important points

- The agent runs **on the Tomcat server**, so it can copy files and control the service locally. No WinRM or SSH is needed, but the agent account needs the right permissions and nothing more.
- Tomcat uses the WAR file name as the context path. `ROOT.war` is served at `/`.
- Delete the old exploded folder before copying a new WAR, or Tomcat may keep serving old files.
- `Stop-Service` / `Start-Service` causes a short outage. That is fine for Dev, but Prod needs more than one server behind a load balancer for zero downtime.
- Keep the Tomcat Manager app disabled or restricted to localhost, and never commit `tomcat-users.xml` passwords.
- Self-hosted agents keep files between runs. Use `clean package` and consider `workspace: clean: all` on the job.

## Common problems

| Problem | Likely cause | Fix |
| --- | --- | --- |
| 404 after deploy | Context path does not match the WAR name, or the WAR was not unpacked | Check `finalName` and the URL; check `catalina.*.log` for deploy errors |
| `ClassNotFoundException` / `NoClassDefFoundError` for `javax.servlet` or `jakarta.servlet` | Servlet API does not match the Tomcat version | Use `javax.servlet` for Tomcat 9, `jakarta.servlet` for Tomcat 10+ |
| `Stop-Service`: access denied / cannot open service | Agent service account has no rights on the `Tomcat9` service | Grant service rights to the agent account (or admin in a lab) |
| `Copy-Item`: access denied | Agent account cannot write to `webapps`, or a file is locked | Grant Modify with `icacls`; make sure Tomcat is fully stopped |
| Tomcat does not start: address already in use | Another process uses port 8080 | `netstat -ano \| findstr :8080`, stop that process or change the port in `server.xml` |
| Maven: "No compiler is provided in this environment" | `JAVA_HOME` points to a JRE | Point `JAVA_HOME` to the JDK folder and restart the agent |
| Build uses the wrong Java version | Old `JAVA_HOME`, or the agent was not restarted after the change | Check `mvn -version` on the agent; restart the agent service |
| `$env:CATALINA_HOME` is empty in the pipeline | Set as a user variable, or the agent started before it was set | Set it as a machine variable and restart the agent service |
| Health check fails but the app works later | Tomcat starts slowly | Increase the number of retries or the wait between them |

## Clean up

```powershell
# Remove the app
Stop-Service Tomcat9
Remove-Item "$env:CATALINA_HOME\webapps\login-showcase*" -Recurse -Force
Start-Service Tomcat9

# Remove the agent (from C:\agent, as Administrator)
.\config.cmd remove --auth pat --token <PAT>

# Remove the Tomcat service
cd C:\tomcat9\bin
.\service.bat remove Tomcat9
```

## Interview questions

<details><summary>Q1. Why use a self-hosted agent here instead of a Microsoft-hosted agent?</summary>

The app runs on a Windows server with Tomcat, often inside a private network. A self-hosted agent installed on that server can reach it directly, copy the WAR into `webapps`, and restart the service without opening WinRM, SSH, or firewall ports from the internet. It also keeps the JDK, Maven, and the Maven cache between runs, so builds are faster. The trade-off is that I must patch and secure the agent machine myself.

</details>

<details><summary>Q2. How do you roll back a bad deployment?</summary>

Before deploying, the pipeline copies the current WAR to a backup folder. To roll back, I stop Tomcat, remove the exploded folder, copy the backup WAR back as `<context>.war`, and start Tomcat. With separate build and deploy stages, I can also re-run the deploy stage of the last good run, which redeploys its exact artifact. The health check makes sure a bad deploy is noticed straight away.

</details>

<details><summary>Q3. What is the difference between hot deploy and restarting Tomcat?</summary>

Hot deploy (dropping a new WAR while Tomcat runs, or using the Manager `deploy?update=true` API) reloads only that application, so other apps on the same Tomcat keep running. But repeated hot deploys can leak memory (classloader leaks) and old files can stay locked on Windows. Stopping and starting the service gives a clean JVM every time, but all apps on that Tomcat are down for the restart. I use a restart for a single-app server and add more servers behind a load balancer to avoid downtime.

</details>

<details><summary>Q4. How do you secure the Tomcat Manager app?</summary>

Disable or remove it if it is not needed. If it is used for deployments, give the deploy user only the `manager-script` role, use a strong password stored as a secret pipeline variable (or in Key Vault), keep the `RemoteAddrValve` so only localhost or the agent can reach it, and use HTTPS if it is accessed over the network. Never commit `tomcat-users.xml` with real passwords.

</details>

<details><summary>Q5. How would you achieve zero-downtime deployments?</summary>

Run at least two Tomcat servers behind a load balancer. Deploy to one server at a time: take it out of the load balancer (or let the health probe fail), deploy and restart, run the health check, then put it back and move to the next server (a rolling deployment). Tomcat parallel deployment (`app##002.war`) is another option on a single server. A longer-term option is to containerise the app and let Kubernetes or Azure App Service handle rolling updates and slots.

</details>
