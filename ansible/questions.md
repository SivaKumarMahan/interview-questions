# Ansible Interview Questions

---

### 1. How have you used Ansible? Give a real example.

**Answer:**

I use Ansible for repeatable server setup, patching, user management, application deployment, and configuring services. Ansible has no agent to install — the control node connects to Linux machines over SSH and runs modules remotely.

A practical example is setting up Nginx on several application servers. My flow is:

1. Keep server addresses and groups in an inventory.
2. Test access with `ansible all -m ping`.
3. Install Nginx with the package module.
4. Build the configuration from a Jinja2 template.
5. Check that the Nginx configuration is valid before reloading it.
6. Use a handler so Nginx only reloads when its configuration actually changes.

```yaml
---
- name: Configure web servers
  hosts: web
  become: true
  serial: 2

  tasks:
    - name: Install Nginx
      ansible.builtin.package:
        name: nginx
        state: present

    - name: Install Nginx configuration
      ansible.builtin.template:
        src: nginx.conf.j2
        dest: /etc/nginx/nginx.conf
        owner: root
        group: root
        mode: "0644"
        validate: "nginx -t -c %s"
      notify: Reload Nginx

    - name: Ensure Nginx is running
      ansible.builtin.service:
        name: nginx
        state: started
        enabled: true

  handlers:
    - name: Reload Nginx
      ansible.builtin.service:
        name: nginx
        state: reloaded
```

I run `ansible-playbook --check --diff` in a lower environment first, then deploy in small batches using `serial`. Afterward I check the play recap, service status, configuration test, health endpoint, and monitoring.

Running the same playbook again should report no unnecessary changes. That's what "idempotent" means, and it's a property I design every playbook around.

---

### 2. How do you configure an Ansible agent?

**Answer:**

Ansible normally doesn't need an agent on managed Linux servers. It connects over SSH, and most modules just need Python on the target. The machine where Ansible itself runs is called the control node.

My setup steps:

1. Install Ansible on the control node.
2. Create a dedicated automation user on managed hosts.
3. Set up SSH key authentication and verify host keys.
4. Give that user only the `sudo` privileges it actually needs.
5. Add hosts and variables to inventory.
6. Test connectivity and facts before running a real playbook.

```ini
[web]
web01 ansible_host=10.0.1.10
web02 ansible_host=10.0.1.11

[web:vars]
ansible_user=automation
ansible_ssh_private_key_file=/secure/path/automation_key
ansible_become=true
```

```bash
ansible-inventory --graph
ansible web -m ping
ansible web -m setup -a 'filter=ansible_distribution*'
```

If `ping` fails, I add `-vvvv` and check DNS/IP reachability, port 22, SSH keys, host-key verification, the username, whether Python is available, and sudo permissions. On Windows, Ansible usually connects over WinRM or SSH instead, so the setup looks different, but there's still no permanently installed Ansible agent.
---

### 3. How do you manage secrets securely in Ansible?

**Answer:**

I never store plaintext passwords, private keys, or API tokens in playbooks, inventory, or Git. For smaller setups I encrypt variables with Ansible Vault.

In enterprise environments I prefer pulling secrets at runtime from Vault, Azure Key Vault, AWS Secrets Manager, or another approved secret store.

```bash
ansible-vault create group_vars/prod/vault.yml
ansible-vault encrypt_string 'StrongPassword' --name 'db_password'
ansible-playbook site.yml --vault-id prod@prompt
```

```yaml
- name: Configure database password without exposing it in output
  ansible.builtin.template:
    src: app.conf.j2
    dest: /etc/myapp/app.conf
    owner: root
    group: myapp
    mode: "0640"
  no_log: true
```

My other security habits: a separate vault identity per environment, giving accounts only the access they need, protecting CI credentials, encrypting traffic, rotating secrets, and locking down permissions on the destination file.

`no_log: true` cuts down accidental output, but I don't apply it everywhere by default — it can also hide information I need when troubleshooting.
After a deployment I check that the application can authenticate, that unauthorized users can't read the secret file, that CI logs contain no secret values, and that rotation works without hand-editing the playbook.

If a secret does leak, I revoke or rotate it first, then remove it from Git history and logs, and find out who accessed it.
---

### 4. How does Ansible communicate with remote Linux servers, and how do you establish connectivity?

**Answer:**

Ansible has no agent. The control node connects to managed Linux hosts over SSH, sends a small module payload, runs it with the selected Python interpreter, and gets back a structured result.

Inventory defines host addresses and variables. `remote_user`, SSH settings, and `become` control login and privilege escalation.
I create or use an approved automation account, check DNS, routes, the firewall, and SSH host keys, install its public key, grant only the sudo commands it needs, and test with:

```bash
ansible-inventory --graph
ansible all -m ping
ansible all -m setup -a 'filter=ansible_distribution*'
```

Ansible's `ping` doesn't use ICMP — it checks login, Python/module execution, and the response. I troubleshoot with `ssh -vvv` and `ansible -vvv`, then check inventory precedence, proxy or bastion settings, the interpreter, sudo, and file permissions.

Credentials stay in an approved vault or CI identity, never in plaintext inventory.

---

### 5. How do you configure passwordless SSH for Ansible, and where should the key be generated?

**Answer:**

I generate the key pair on whatever starts the automation — an engineer's approved workstation for personal admin work, or, better, a dedicated CI/control-node identity for shared automation.

The private key stays there or in a credential manager. Only the public key goes into the target user's `~/.ssh/authorized_keys`.
```bash
ssh-keygen -t ed25519 -f ~/.ssh/ansible_prod
ssh-copy-id -i ~/.ssh/ansible_prod.pub automation@server
ssh -i ~/.ssh/ansible_prod automation@server
```

I use restrictive file permissions, verify host keys, protect the private key with a passphrase or managed agent, scope down accounts and sudo, rotate keys, and keep environments separate. "Passwordless" just means public-key authentication — it isn't the same as no authentication at all.

In cloud environments I prefer short-lived certificates, SSM, or a managed identity mechanism when the platform supports it.
---

### 6. What if the target Ansible user does not exist or you do not yet have access to the server?

**Answer:**

Ansible can't create its own first login path — it needs an already-authorized bootstrap mechanism. I don't bypass access controls or guess at another account.

Instead, I ask the server owner, the cloud-init/image process, the identity-management team, or an approved break-glass administrator to create the automation user, install the public key, register host keys, and grant narrowly scoped sudo.

For repeatability, the base image or provisioning workflow should bootstrap that account. After that, Ansible can manage it going forward.

If access unexpectedly fails, I check ownership, approval, the inventory address, DNS, routing, the firewall, the bastion, the SSH service, whether the account is locked or expired, `authorized_keys` permissions, and any host-key changes, using console or provider access where I'm authorized to.
I record who approved the bootstrap access, and I test both what should work and what should be denied. Missing access is a process gap to escalate, not a reason to loosen SSH policy.

---

### 7. How would you automate Machine B from Machine A with Ansible?

**Answer:**

Machine A needs to be an approved control node: Ansible installed, inventory in place, code checked out, and a valid identity for reaching Machine B. After confirming connectivity, I write an idempotent playbook — one that's safe to run more than once — using modules instead of a chain of shell commands:

```yaml
- hosts: machine_b
  become: true
  tasks:
    - name: Install Nginx
      ansible.builtin.package:
        name: nginx
        state: present
    - name: Ensure Nginx is enabled and running
      ansible.builtin.service:
        name: nginx
        enabled: true
        state: started
```

I run `ansible-playbook --syntax-check`, then `--check --diff` where the modules support it, limit the first production run to a single canary host, and check service health afterward. Code, inventory structure, Vault references, reviews, and CI logs give me repeatability and an audit trail.

---

### 8. Is Ansible inventory static or dynamic?

**Answer:**

It can be either. A static inventory lists hosts and groups in INI or YAML, and works well for small, stable environments.

A dynamic inventory plugin queries a source such as AWS, Azure, VMware, or Kubernetes at run time, and can group hosts by tags, region, or other metadata. I use dynamic inventory for cloud fleets that scale up and down, cache it appropriately, and check it with `ansible-inventory --graph` before making a change.

Inventory should describe targets only — it should never contain secrets.

---

### 9. What is the difference between the `command` and `shell` modules?

**Answer:**

`ansible.builtin.command` runs a program directly, without a shell interpreting it. That means pipes, redirects, glob expansion, and variables don't work. It's the safer default because it avoids shell injection.

`ansible.builtin.shell` runs through a shell, so use it only when you genuinely need shell features.

Given the choice, I prefer a dedicated Ansible module over either one. Where I can, I use `creates`/`removes` or a module that's already idempotent, and I quote any variables carefully when `shell` really is unavoidable.

---

### 10. What is an Ansible module?

**Answer:**

A module is a reusable unit that Ansible runs to perform one action, for example `package`, `service`, `copy`, `user`, `template`, or a cloud-specific module.

Modules return structured facts like `changed`, `failed`, and their output. A well-written module is idempotent: applying the same desired state repeatedly produces the same result without extra changes.

A task calls one module. A playbook organizes plays, variables, handlers, and tasks together. I use fully qualified names such as `ansible.builtin.copy` so it's always clear where a module comes from.

---

### 11. How do you automate private VMs with Ansible when their IP addresses change?

**Answer:**

I use a dynamic inventory plugin for the cloud or virtualization platform, and group hosts by metadata I trust, such as environment, application, and role. Ansible asks the provider's API for the current private addresses or hostnames, so nobody has to maintain a static inventory by hand.

Internal DNS, a CMDB-backed inventory, or a bastion/proxy can provide the connection path where direct access isn't available.

The control node still needs authenticated network access, host-key verification, and credentials scoped to only what it needs. Dynamic inventory discovers hosts — it doesn't bypass network security.
