# Practice Project 7: Provision and Configure an Azure VM with Ansible

> A hands-on guide to creating an Azure Linux VM with the `azure.azcollection` modules, finding it with the Azure dynamic inventory plugin, and configuring Nginx on it with a reusable Ansible role, Vault secrets and idempotent runs.

## Key Concepts

### What you will build

You will build one Ansible project that does two jobs:

1. **Provision**: a playbook (`provision.yml`) creates a resource group, VNet, subnet, public IP, network security group (NSG), network interface and an Ubuntu VM tagged `role: web`.
2. **Configure**: a second playbook (`site.yml`) finds the VM through the **Azure dynamic inventory** (no hard-coded IPs), then runs a `webserver` role that installs Nginx, deploys a Jinja2 site config and a small static app, and keeps the service running.

The final result: you open `http://<public-ip>/` in a browser and see a page that says which environment and host served it. Running `site.yml` a second time shows `changed=0`, which proves the playbook is idempotent.

### Architecture

```text
 Your laptop / CI runner
 +-----------------------------------------------+
 | ansible-core + azure.azcollection             |
 |                                               |
 |  provision.yml  --(Azure Resource Manager)--> |----+
 |  site.yml       --(SSH, port 22)----------->  |--+ |
 |  inventory/azure_rm.yml (dynamic inventory)   |  | |
 +-----------------------------------------------+  | |
                                                    | |
 Azure subscription                                 | |
 +--------------------------------------------------|-|-----------+
 | Resource group: rg-ansible-lab                   | |           |
 |                                                  | v           |
 |  VNet 10.10.0.0/16                         ARM creates:        |
 |   └─ Subnet snet-web 10.10.1.0/24          RG, VNet, subnet,   |
 |        └─ NIC nic-web01 ── NSG nsg-web     PIP, NSG, NIC, VM   |
 |             │            (allow 22 from your IP, 80 from any)  |
 |             └─ VM vm-web01 (Ubuntu 24.04, tag role=web)        |
 |                  └─ Public IP pip-web01  <── SSH + HTTP        |
 +----------------------------------------------------------------+
```

### Tools and why each one is used

| Tool | What it does here | Why this tool |
| --- | --- | --- |
| ansible-core | Runs playbooks and roles | Agentless, uses SSH, simple YAML |
| azure.azcollection | Modules and inventory plugin for Azure | Official collection maintained for Azure resources |
| Azure CLI (`az`) | Logs you in; Ansible reuses that login | No secrets to store for a lab |
| Dynamic inventory plugin `azure.azcollection.azure_rm` | Lists VMs and groups them by tags | IPs change; tags do not |
| Jinja2 templates | Render the Nginx site config per host | One template, many environments |
| ansible-vault | Encrypts secret variables in the repo | Secrets stay encrypted at rest in Git |
| ansible-lint | Checks playbooks for bad practice | Catches mistakes before they run |

### Prerequisites

- An Azure subscription where you can create resources (Contributor on a resource group or subscription).
- Linux, macOS or WSL2. Ansible control nodes do not run natively on Windows.
- Python 3.10 or later and `pip`.
- Azure CLI 2.60 or later: `az version`.
- An SSH key pair. Create one if needed:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/ansible_lab -C "ansible-lab"
```

- **Cost warning**: a `Standard_B1s` or `Standard_B2s` VM plus a Standard public IP costs a small amount per hour. Delete everything in the "Clean up" section when you finish.

### Folder structure

```text
ansible-azure-vm/
├── ansible.cfg
├── requirements.yml
├── provision.yml
├── site.yml
├── inventory/
│   └── azure_rm.yml
├── group_vars/
│   ├── all.yml
│   └── role_web/
│       ├── vars.yml
│       └── vault.yml          # encrypted with ansible-vault
└── roles/
    └── webserver/
        ├── defaults/main.yml
        ├── handlers/main.yml
        ├── tasks/main.yml
        ├── templates/site.conf.j2
        ├── templates/index.html.j2
        └── files/app/
            ├── app.css
            └── health.txt
```

### Step-by-step

#### Step 1: Create a Python virtual environment and install Ansible

A virtual environment keeps Ansible and the Azure SDK packages away from your system Python. This avoids version conflicts.

```bash
mkdir -p ~/ansible-azure-vm && cd ~/ansible-azure-vm
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install ansible-core ansible-lint
ansible --version
```

What this does:

- `python3 -m venv .venv` creates an isolated Python environment in the project folder.
- `ansible-core` is the engine only. Collections such as Azure are installed separately in the next step.
- `ansible --version` should show `ansible [core 2.17.x]` or later and the Python path inside `.venv`.

#### Step 2: Install the Azure collection and its Python requirements

The Azure modules call the Azure SDK for Python. The collection ships a `requirements.txt` with the exact SDK versions it was tested with.

```yaml
# requirements.yml
collections:
  - name: azure.azcollection
    version: ">=3.0.0"
```

```bash
ansible-galaxy collection install -r requirements.yml
pip install -r ~/.ansible/collections/ansible_collections/azure/azcollection/requirements.txt
ansible-galaxy collection list | grep azure
```

What this does:

- `ansible-galaxy collection install` downloads the collection into `~/.ansible/collections`.
- The `pip install -r .../requirements.txt` step installs packages such as `azure-mgmt-compute` and `azure-identity`. Skipping it is the most common cause of `ModuleNotFoundError` errors.
- If you installed the collection to a custom path, adjust the path to `requirements.txt`.

#### Step 3: Authenticate to Azure

The Azure modules support several auth methods. They check them in this order when `auth_source: auto` is used: environment variables, a credentials file, then the Azure CLI, then managed identity.

| Method | When to use | How |
| --- | --- | --- |
| Azure CLI (`az login`) | Labs and local work | `az login`, then `auth_source: cli` |
| Environment variables | CI pipelines | `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, plus a secret or OIDC token |
| Managed identity | Ansible runs on an Azure VM or self-hosted agent | `auth_source: msi` |

For this lab, use the CLI:

```bash
az login
az account set --subscription "<subscription-id>"
export AZURE_SUBSCRIPTION_ID=$(az account show --query id -o tsv)
```

What this does:

- `az login` opens a browser and stores a token in `~/.azure`. Ansible reuses it, so no password or client secret is stored in the project.
- Setting `AZURE_SUBSCRIPTION_ID` makes sure the modules target the right subscription.
- In a CI pipeline, prefer **workload identity federation (OIDC)** with a service principal or a self-hosted runner with a **managed identity**, instead of a long-lived client secret.

#### Step 4: Create ansible.cfg

`ansible.cfg` sets project defaults so every command does not need long flags.

```ini
[defaults]
inventory = inventory/azure_rm.yml
remote_user = azureuser
private_key_file = ~/.ssh/ansible_lab
host_key_checking = False
roles_path = roles
stdout_callback = yaml
retry_files_enabled = False
interpreter_python = auto_silent

[inventory]
enable_plugins = azure.azcollection.azure_rm, host_list, yaml, ini

[ssh_connection]
pipelining = True
```

What this does:

- `inventory` points to the dynamic inventory file, so `-i` is optional.
- `host_key_checking = False` is fine for a short-lived lab. In real environments, manage known hosts properly.
- `enable_plugins` must list `azure.azcollection.azure_rm`, or the inventory file is ignored.
- `pipelining = True` reduces SSH round trips and makes runs faster.
- Note: Ansible ignores `ansible.cfg` in a world-writable folder. Keep the folder permissions normal.

#### Step 5: Define shared variables

```yaml
# group_vars/all.yml
location: eastus
resource_group: rg-ansible-lab
vnet_name: vnet-ansible-lab
subnet_name: snet-web
nsg_name: nsg-web
admin_username: azureuser
ssh_public_key_path: ~/.ssh/ansible_lab.pub
my_ip_cidr: "<your-public-ip>/32"
env_name: lab

web_vms:
  - name: vm-web01
    size: Standard_B1s
```

What this does:

- One place holds names and sizes. Change `location` or add a second VM to `web_vms` without touching the playbook logic.
- `my_ip_cidr` restricts SSH to your own IP. Find it with `curl -s https://ifconfig.me`.

#### Step 6: Write the provisioning playbook

This playbook runs on `localhost` because it talks to the Azure API, not to a server.

```yaml
# provision.yml
- name: Provision Azure infrastructure for the web tier
  hosts: localhost
  connection: local
  gather_facts: false
  vars_files:
    - group_vars/all.yml

  tasks:
    - name: Create resource group
      azure.azcollection.azure_rm_resourcegroup:
        name: "{{ resource_group }}"
        location: "{{ location }}"
        tags:
          project: ansible-lab
          env: "{{ env_name }}"

    - name: Create virtual network
      azure.azcollection.azure_rm_virtualnetwork:
        resource_group: "{{ resource_group }}"
        name: "{{ vnet_name }}"
        address_prefixes: 10.10.0.0/16

    - name: Create subnet
      azure.azcollection.azure_rm_subnet:
        resource_group: "{{ resource_group }}"
        virtual_network_name: "{{ vnet_name }}"
        name: "{{ subnet_name }}"
        address_prefix: 10.10.1.0/24

    - name: Create network security group
      azure.azcollection.azure_rm_securitygroup:
        resource_group: "{{ resource_group }}"
        name: "{{ nsg_name }}"
        rules:
          - name: Allow-SSH-From-My-IP
            protocol: Tcp
            destination_port_range: 22
            source_address_prefix: "{{ my_ip_cidr }}"
            access: Allow
            priority: 100
            direction: Inbound
          - name: Allow-HTTP
            protocol: Tcp
            destination_port_range: 80
            source_address_prefix: Internet
            access: Allow
            priority: 110
            direction: Inbound

    - name: Create public IP for each VM
      azure.azcollection.azure_rm_publicipaddress:
        resource_group: "{{ resource_group }}"
        name: "pip-{{ item.name }}"
        allocation_method: Static
        sku: Standard
      loop: "{{ web_vms }}"

    - name: Create NIC for each VM
      azure.azcollection.azure_rm_networkinterface:
        resource_group: "{{ resource_group }}"
        name: "nic-{{ item.name }}"
        virtual_network: "{{ vnet_name }}"
        subnet_name: "{{ subnet_name }}"
        security_group: "{{ nsg_name }}"
        ip_configurations:
          - name: ipconfig1
            public_ip_address_name: "pip-{{ item.name }}"
            primary: true
      loop: "{{ web_vms }}"

    - name: Create the VMs
      azure.azcollection.azure_rm_virtualmachine:
        resource_group: "{{ resource_group }}"
        name: "{{ item.name }}"
        vm_size: "{{ item.size }}"
        admin_username: "{{ admin_username }}"
        ssh_password_enabled: false
        ssh_public_keys:
          - path: "/home/{{ admin_username }}/.ssh/authorized_keys"
            key_data: "{{ lookup('file', ssh_public_key_path) }}"
        network_interfaces: "nic-{{ item.name }}"
        os_disk_caching: ReadWrite
        managed_disk_type: StandardSSD_LRS
        image:
          publisher: Canonical
          offer: ubuntu-24_04-lts
          sku: server
          version: latest
        tags:
          role: web
          env: "{{ env_name }}"
          managed_by: ansible
      loop: "{{ web_vms }}"
```

What this does:

- `hosts: localhost` and `connection: local` mean the tasks run on your machine and call Azure Resource Manager (ARM).
- Each module is declarative: it describes the desired state. If the resource already exists with the same settings, the task reports `ok`, not `changed`.
- The NSG allows SSH only from your IP and HTTP from the internet. Never open port 22 to `*`.
- `ssh_password_enabled: false` plus `ssh_public_keys` gives key-only login.
- The `tags` block is important: the dynamic inventory uses `role: web` to put the VM in the right group.
- Image values: confirm current Ubuntu images with `az vm image list --publisher Canonical --offer ubuntu-24_04-lts --all -o table`.

Run it:

```bash
ansible-playbook provision.yml
```

The first run takes 3-5 minutes and ends with a recap similar to `localhost : ok=7 changed=7 failed=0`.

#### Step 7: Configure the dynamic inventory

The inventory plugin asks Azure for VMs and builds groups from tags. The file name **must** end in `azure_rm.yml` or `azure_rm.yaml`.

```yaml
# inventory/azure_rm.yml
plugin: azure.azcollection.azure_rm
auth_source: auto
include_vm_resource_groups:
  - rg-ansible-lab
plain_host_names: true

keyed_groups:
  # role=web  ->  group "role_web"
  - prefix: role
    key: tags.role | default('none')
  # env=lab   ->  group "env_lab"
  - prefix: env
    key: tags.env | default('none')
  # one group per Azure region, e.g. "location_eastus"
  - prefix: location
    key: location

conditional_groups:
  # VMs built from an Ubuntu image
  ubuntu: "'ubuntu' in image.offer"
  # VMs that are running right now
  running: powerstate == "running"

hostvar_expressions:
  # connect over the public IP; fall back to the private IP
  ansible_host: (public_ipv4_address + private_ipv4_addresses) | first
```

What this does:

- `include_vm_resource_groups` limits the query to one resource group. This is faster and avoids touching VMs you do not own.
- `keyed_groups` turns tag values into group names. A VM tagged `role: web` lands in `role_web`.
- `conditional_groups` creates groups from any Jinja2 expression on host variables.
- `hostvar_expressions` sets `ansible_host` so Ansible knows which IP to SSH into.
- Host variable names can differ slightly between collection versions (for example `public_ipv4_address` vs `public_ipv4_addresses`). Run `ansible-inventory --list` once and use the names you see.

Check the inventory:

```bash
ansible-inventory -i inventory/azure_rm.yml --graph
ansible-inventory -i inventory/azure_rm.yml --host vm-web01 | head -40
ansible role_web -m ping
```

Expected output of `--graph`:

```text
@all:
  |--@ungrouped:
  |--@role_web:
  |  |--vm-web01
  |--@env_lab:
  |  |--vm-web01
  |--@location_eastus:
  |  |--vm-web01
  |--@ubuntu:
  |  |--vm-web01
  |--@running:
  |  |--vm-web01
```

#### Step 8: Add group variables and a Vault secret

Group variables live in a folder named after the group. Secrets go in a separate file encrypted with ansible-vault.

```yaml
# group_vars/role_web/vars.yml
nginx_server_name: "_"
app_root: /var/www/demo-app
app_title: "Ansible on Azure demo"
# Points to the encrypted value; keeps the variable easy to find with grep
app_api_token: "{{ vault_app_api_token }}"
```

Create the encrypted file:

```bash
ansible-vault create group_vars/role_web/vault.yml
```

Inside the editor, add:

```yaml
vault_app_api_token: "<placeholder-token-value>"
```

Useful vault commands:

```bash
ansible-vault view group_vars/role_web/vault.yml
ansible-vault edit group_vars/role_web/vault.yml
ansible-vault rekey group_vars/role_web/vault.yml
echo '<vault-password>' > ~/.ansible_vault_pass && chmod 600 ~/.ansible_vault_pass
```

What this does:

- The `vault_` prefix pattern makes it clear which values are secret, while `vars.yml` stays readable.
- The encrypted file is safe to commit. The vault password is not. Keep it in a password manager, a protected file outside the repo, or a CI secret.
- For production, a better option is to read secrets at runtime from Azure Key Vault with the `azure.azcollection.azure_keyvaultsecret_info` module or the `azure.azcollection.azure_keyvault_secret` lookup, using a managed identity.

#### Step 9: Create the webserver role

Create the skeleton:

```bash
ansible-galaxy role init roles/webserver
```

Role defaults (lowest priority, easy to override):

```yaml
# roles/webserver/defaults/main.yml
nginx_listen_port: 80
nginx_server_name: "_"
app_root: /var/www/demo-app
app_title: "Demo app"
env_name: dev
```

Tasks:

```yaml
# roles/webserver/tasks/main.yml
- name: Install Nginx
  ansible.builtin.apt:
    name: nginx
    state: present
    update_cache: true
    cache_valid_time: 3600

- name: Create the app directory
  ansible.builtin.file:
    path: "{{ app_root }}"
    state: directory
    owner: www-data
    group: www-data
    mode: "0755"

- name: Copy static app files
  ansible.builtin.copy:
    src: app/
    dest: "{{ app_root }}/"
    owner: www-data
    group: www-data
    mode: "0644"

- name: Render the index page
  ansible.builtin.template:
    src: index.html.j2
    dest: "{{ app_root }}/index.html"
    owner: www-data
    group: www-data
    mode: "0644"

- name: Deploy Nginx site config
  ansible.builtin.template:
    src: site.conf.j2
    dest: /etc/nginx/sites-available/demo-app.conf
    owner: root
    group: root
    mode: "0644"
  notify: Reload nginx

- name: Enable the site
  ansible.builtin.file:
    src: /etc/nginx/sites-available/demo-app.conf
    dest: /etc/nginx/sites-enabled/demo-app.conf
    state: link
  notify: Reload nginx

- name: Remove the default site
  ansible.builtin.file:
    path: /etc/nginx/sites-enabled/default
    state: absent
  notify: Reload nginx

- name: Ensure Nginx is started and enabled at boot
  ansible.builtin.service:
    name: nginx
    state: started
    enabled: true
```

Handlers. The first handler tests the full Nginx config before the second one reloads the service:

```yaml
# roles/webserver/handlers/main.yml
# Both handlers listen to the same topic. Handlers run in the order
# they are defined here, so the config test always runs before the reload.
- name: Test nginx config
  ansible.builtin.command: nginx -t
  changed_when: false
  listen: Reload nginx

- name: Reload nginx service
  ansible.builtin.service:
    name: nginx
    state: reloaded
  listen: Reload nginx
```

Templates:

```jinja
{# roles/webserver/templates/site.conf.j2 #}
# Managed by Ansible. Manual changes will be overwritten.
server {
    listen {{ nginx_listen_port }} default_server;
    listen [::]:{{ nginx_listen_port }} default_server;
    server_name {{ nginx_server_name }};

    root {{ app_root }};
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }

    location = /health {
        access_log off;
        default_type text/plain;
        alias {{ app_root }}/health.txt;
    }

{% if env_name != 'prod' %}
    add_header X-Environment "{{ env_name }}" always;
{% endif %}
}
```

```jinja
{# roles/webserver/templates/index.html.j2 #}
<!doctype html>
<html>
  <head><title>{{ app_title }}</title><link rel="stylesheet" href="app.css"></head>
  <body>
    <h1>{{ app_title }}</h1>
    <p>Environment: {{ env_name }}</p>
    <p>Served by: {{ inventory_hostname }} ({{ ansible_facts['default_ipv4']['address'] }})</p>
  </body>
</html>
```

Static files:

```bash
mkdir -p roles/webserver/files/app
echo "OK" > roles/webserver/files/app/health.txt
echo "body { font-family: sans-serif; margin: 3rem; }" > roles/webserver/files/app/app.css
```

What this does:

- `apt` with `cache_valid_time` refreshes the package cache at most once per hour, which keeps re-runs fast.
- `template` renders Jinja2 with host and group variables. Any change to the rendered file triggers `notify`.
- Handlers run once at the end of the play, and only if a task notified them. Ten config changes cause one reload, not ten.
- `listen: Reload nginx` lets one `notify` trigger both handlers. A `changed_when: false` task cannot notify other handlers, so `listen` is the clean way to chain them.
- `nginx -t` in the first handler stops a broken config from being reloaded. A failed check fails the play and the old config keeps serving.
- `service: state=started enabled=true` makes sure Nginx survives a reboot.
- Do not template secrets into world-readable files. If the app needs `app_api_token`, write it to a file with `mode: "0600"` and add `no_log: true` to that task.

#### Step 10: Write the main playbook

```yaml
# site.yml
- name: Configure web servers
  hosts: role_web
  become: true
  gather_facts: true
  roles:
    - role: webserver
```

Run it:

```bash
ansible-playbook site.yml --vault-password-file ~/.ansible_vault_pass
```

What this does:

- `hosts: role_web` targets the group created by `keyed_groups`. A new VM with the tag joins automatically on the next run.
- `become: true` uses sudo, which the Azure Ubuntu image allows for the admin user.
- `--vault-password-file` decrypts `vault.yml` in memory only.

#### Step 11: Prove idempotency, dry runs and linting

Run the same playbook again. Nothing should change.

```bash
ansible-playbook site.yml --vault-password-file ~/.ansible_vault_pass
```

Expected recap:

```text
PLAY RECAP *********************************************************
vm-web01 : ok=9  changed=0  unreachable=0  failed=0  skipped=0  rescued=0  ignored=0
```

Preview a change without applying it. Edit `app_title` in `group_vars/role_web/vars.yml`, then:

```bash
ansible-playbook site.yml --check --diff --vault-password-file ~/.ansible_vault_pass
```

Expected output (shortened):

```text
TASK [webserver : Render the index page] ***************************
--- before: /var/www/demo-app/index.html
+++ after: /tmp/.../index.html.j2
@@ -1,6 +1,6 @@
-    <h1>Ansible on Azure demo</h1>
+    <h1>Ansible on Azure demo v2</h1>
changed: [vm-web01]
```

Lint the project:

```bash
ansible-lint site.yml provision.yml
```

What this does:

- A second run with `changed=0` shows every task checks state before acting. This is the main promise of Ansible modules.
- `--check` is a dry run. `--diff` shows file-level changes. Some tasks (for example `command`) cannot predict changes in check mode.
- `ansible-lint` flags issues such as missing `name`, short module names instead of FQCN, `command` used where a module exists, and missing `changed_when`.

### Verify it works

```bash
PIP=$(az network public-ip show -g rg-ansible-lab -n pip-vm-web01 --query ipAddress -o tsv)
curl -s http://$PIP/ | grep -E "h1|Environment"
curl -s http://$PIP/health
curl -sI http://$PIP/ | grep -i x-environment
ansible role_web -b -m ansible.builtin.command -a "systemctl is-enabled nginx"
```

Expected output:

```text
    <h1>Ansible on Azure demo</h1>
    <p>Environment: lab</p>
OK
X-Environment: lab
vm-web01 | CHANGED | rc=0 >>
enabled
```

### Common problems and fixes

| Problem | Likely cause | Fix |
| --- | --- | --- |
| `ModuleNotFoundError: No module named 'azure'` | Collection Python requirements not installed in the active Python | Activate `.venv`, rerun `pip install -r .../azcollection/requirements.txt` |
| `ansible-inventory --graph` shows only `@ungrouped` | Plugin not enabled, or file name does not end in `azure_rm.yml` | Add plugin to `enable_plugins`, rename the file |
| Inventory is empty | Wrong subscription or resource group filter | `az account show`, check `include_vm_resource_groups` |
| `UNREACHABLE! ... Permission denied (publickey)` | Wrong private key or user | Check `private_key_file` and `remote_user` in `ansible.cfg` |
| SSH timeout | NSG blocks your IP, or your IP changed | Update `my_ip_cidr` and rerun `provision.yml` |
| `ansible_host` is the private IP | Wrong hostvar name in `hostvar_expressions` | Check names with `ansible-inventory --host vm-web01` |
| `Could not get lock /var/lib/dpkg/lock-frontend` | cloud-init or unattended upgrades still running on first boot | Wait, or add a task that waits for `cloud-init status --wait` |
| `ERROR! Attempting to decrypt but no vault secrets found` | Vault password not supplied | Add `--ask-vault-pass` or `--vault-password-file` |
| Task always shows `changed` | `command`/`shell` with no `changed_when` | Use a proper module, or set `changed_when` |
| `AuthorizationFailed` on provisioning | Your identity lacks Contributor on the scope | Ask for the role or use a resource group where you have it |

### Clean up

```bash
az group delete --name rg-ansible-lab --yes --no-wait
```

Or with Ansible, which is useful to show that teardown can also be code:

```yaml
# destroy.yml
- name: Remove lab resources
  hosts: localhost
  connection: local
  gather_facts: false
  tasks:
    - name: Delete resource group and everything in it
      azure.azcollection.azure_rm_resourcegroup:
        name: rg-ansible-lab
        state: absent
        force_delete_nonempty: true
```

```bash
ansible-playbook destroy.yml
```

### Next improvements

- Move the infrastructure part to Terraform or Bicep, and keep Ansible for configuration only.
- Read secrets from Azure Key Vault at runtime with a managed identity instead of ansible-vault.
- Remove the public IP. Reach the VM through Azure Bastion or a self-hosted runner inside the VNet.
- Scale out with a VM Scale Set and a load balancer, and use the same tag-based inventory.
- Add Molecule tests for the role, and run `ansible-lint` and a `--check` run in a CI pipeline.
- Run Ansible from a pipeline that authenticates with OIDC (workload identity federation).
- Use cloud-init for first-boot bootstrap, and Ansible for ongoing configuration.

### How to explain this project in an interview

> "As a hands-on lab, I automated a small web tier on Azure with Ansible. One playbook uses the azure.azcollection modules to create the resource group, network, NSG, public IP and an Ubuntu VM tagged role equals web. I authenticated through the Azure CLI, so there were no secrets in the repo. A second playbook uses the Azure dynamic inventory plugin, which groups VMs by tag, so I never hard-code IP addresses. It applies a webserver role that installs Nginx, renders the site config from a Jinja2 template, copies the app files and reloads Nginx through a handler only when the config changes. Secrets live in an ansible-vault file. I proved idempotency by running it twice: the second run showed changed equals zero. I used check and diff mode to preview changes and ansible-lint to catch bad practice. If I did it again for production, I would use Terraform for the infrastructure and keep Ansible for configuration."

Points that impress interviewers:

- You can explain the split: provisioning (declarative infra) vs configuration management (inside the OS).
- You use tag-based dynamic inventory instead of static IP lists.
- You show idempotency with evidence (`changed=0`) and use handlers correctly.
- You keep secrets out of Git (CLI or managed identity auth, ansible-vault or Key Vault).

## Interview Questions

<details><summary>Q1. [Basic] What does "agentless" mean in Ansible, and why does it matter?</summary>

**Answer:**

Ansible does not need a software agent on the managed servers. It connects over SSH (or WinRM for Windows), copies a small Python module, runs it and removes it. This matters because:

- There is nothing to install, patch or monitor on each server.
- The only requirements on Linux targets are SSH and Python.
- Cloud API tasks (like creating Azure resources) run on the control node itself with `connection: local`.

</details>

<details><summary>Q2. [Basic] What is idempotency, and how do you prove a playbook is idempotent?</summary>

**Answer:**

Idempotency means running the same playbook many times gives the same end state, and it only changes things that are not already correct. Modules like `apt`, `template` and `service` check the current state first.

To prove it, run the playbook twice. The second run should show `changed=0` in the recap. Tasks that use `command` or `shell` break this unless you add `creates`, `removes` or `changed_when`.

</details>

<details><summary>Q3. [Basic] What is the difference between a handler and a normal task?</summary>

**Answer:**

A normal task runs every time. A handler runs only when another task notifies it **and** that task reported `changed`. Handlers run once at the end of the play, even if notified many times. This is used for actions like "reload Nginx after config changed". You can force them earlier with `ansible.builtin.meta: flush_handlers`.

</details>

<details><summary>Q4. [Intermediate] How does the Azure dynamic inventory plugin work, and why use it instead of a static inventory?</summary>

**Answer:**

The `azure.azcollection.azure_rm` plugin calls the Azure API at runtime and returns the VMs (and optionally scale set instances) it finds. You configure it in a YAML file whose name ends with `azure_rm.yml`.

- `include_vm_resource_groups` limits which resource groups to read.
- `keyed_groups` builds groups from values such as tags or location (for example `role_web`).
- `conditional_groups` builds groups from a Jinja2 condition.
- `hostvar_expressions` sets variables like `ansible_host`.

Static inventories break when IPs change or VMs are added. Tag-based groups stay correct automatically. Test with `ansible-inventory --graph`.

</details>

<details><summary>Q5. [Intermediate] How do you handle secrets in Ansible?</summary>

**Answer:**

- **ansible-vault**: encrypt variable files (`ansible-vault create/edit/encrypt`) and pass the vault password at runtime. Use a `vault_` prefix pattern so secret variables are easy to find.
- **External secret stores**: read from Azure Key Vault at runtime, ideally with a managed identity, so there is no secret in Git at all.
- Use `no_log: true` on tasks that handle secrets so they do not appear in logs.
- Never commit the vault password; keep it in a CI secret or a password manager.

</details>

<details><summary>Q6. [Intermediate] What do <code>--check</code> and <code>--diff</code> do, and what are their limits?</summary>

**Answer:**

`--check` runs the playbook in dry-run mode: modules report what they would change without changing it. `--diff` shows the before and after content of files and templates.

Limits:

- `command` and `shell` tasks are skipped in check mode unless they set `check_mode: false`.
- Tasks that depend on an earlier task's real result (for example a package that is not installed yet) can fail or give misleading results.
- It does not prove the app works; it only predicts state changes.

</details>

<details><summary>Q7. [Intermediate] Ansible or Terraform: when would you use each?</summary>

**Answer:**

| Area | Terraform | Ansible |
| --- | --- | --- |
| Main job | Provision cloud infrastructure | Configure servers and apps |
| Style | Declarative with a state file | Procedural task list with idempotent modules |
| State | Tracks state in a state file, plans drift | No state file; checks live state each run |
| Deletion | Removes resources dropped from code | Only deletes what you explicitly mark `state: absent` |
| Preview | `terraform plan` | `--check --diff` |

A common pattern is Terraform or Bicep for infrastructure, then Ansible (or cloud-init) for OS and app configuration. Ansible can provision Azure, as this lab shows, but it does not track drift or dependency graphs as well as Terraform.

</details>

<details><summary>Q8. [Advanced] Your playbook reports <code>changed</code> on every run for one task. How do you investigate? <em>(scenario)</em></summary>

**Answer:**

1. Run with `--diff` and `-v` to see what the task thinks changed.
2. If it is `command` or `shell`, it always reports changed. Replace it with a proper module, or add `changed_when` based on output, or `creates`/`removes`.
3. If it is a template, look for values that change on each run, such as timestamps, `ansible_date_time` or random ordering of a dict. Sort lists and remove dynamic values.
4. Check file ownership and mode: a mismatch between the task and what another process sets will flip every run.
5. For `apt`, `update_cache: true` without `cache_valid_time` can report changed.

The goal is a clean second run with `changed=0`.

</details>

<details><summary>Q9. [Advanced] How would you run this in a CI/CD pipeline securely? <em>(scenario)</em></summary>

**Answer:**

- Authenticate to Azure with **workload identity federation (OIDC)** from the pipeline, or run on a self-hosted agent inside the VNet with a **managed identity**. No client secrets.
- Store the vault password (if used) as a pipeline secret, or replace vault with Key Vault lookups.
- Stages: `ansible-lint` → `--check --diff` on pull requests → apply on merge with an approval gate for production.
- Keep the SSH private key in the pipeline's secure files, or avoid public SSH by running inside the VNet or through Bastion.
- Pin the collection and Python requirements versions to get repeatable runs.

</details>

<details><summary>Q10. [Advanced] A new VM was created but <code>site.yml</code> did not configure it. What do you check? <em>(scenario)</em></summary>

**Answer:**

1. `ansible-inventory --graph`: is the VM listed at all? If not, check the resource group filter and the subscription.
2. Is it in `role_web`? Check the tag spelling and case (`role: web`). Tags are case-sensitive in Jinja2 expressions.
3. Is it running? Stopped VMs may have no IP or fail to connect.
4. `ansible-inventory --host <vm>`: is `ansible_host` set to a reachable IP?
5. `ansible <vm> -m ping`: check the NSG, SSH key and user.
6. Make sure the inventory cache (if enabled) was refreshed.

</details>
