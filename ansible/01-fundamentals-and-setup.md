# Ansible: Fundamentals and Setup

> What Ansible is, how to install and set it up, plus a quick revision recap of the whole tool.

## Key Concepts

### Quick interview recap

- Ansible is agentless and commonly connects to Linux nodes over SSH.
- Inventory defines hosts/groups; playbooks define desired automation.
- A module performs one action; tasks call modules; plays map tasks to hosts.
- Ad hoc commands are for one-time work; repeatable work belongs in playbooks.
- Prefer idempotent modules over `shell`.
- Facts describe managed hosts and support conditions/templates.
- Variables come from many scopes and follow precedence; extra vars have very high precedence.
- `loop` repeats a task and uses `item`.
- `when` is a raw Jinja expression without outer `{{ }}`.
- Handlers run when notified by a changed task.
- Tags select tasks, `--limit` restricts hosts and `--forks` controls parallel workers.
- `--syntax-check`, `--check`, `--diff` and canary runs reduce risk but do not replace real verification.
- Vault encrypts data at rest; protect decrypted data with access control and `no_log`.
- Roles and collections make automation reusable.
- Production work should be reviewed, pinned, limited, batched, monitored and recoverable.

### What is Ansible?

**Ansible** is an automation tool for configuration management, application deployment, orchestration, and general operational tasks. It has no agent to install. The control node reads YAML playbooks and inventory, connects to managed nodes over SSH for Linux, and runs modules that return structured results.

Core components:

- **Control node:** The machine where `ansible-core`, inventories, collections and playbooks are installed.
- **Managed node:** A target host managed by Ansible. A permanently installed Ansible agent is normally not required.
- **Inventory:** Hosts, groups and connection/group variables.
- **Module:** Reusable code that performs one focused operation, such as managing a package, file, user or service.
- **Task:** One call to a module with arguments.
- **Play:** Maps an ordered list of tasks/roles to a host pattern.
- **Playbook:** One or more plays stored as YAML.
- **Role:** A standard directory structure for reusable tasks, handlers, defaults, variables, templates and files.
- **Collection:** A distributable package containing modules, plugins, roles and documentation.

Basic execution flow:

```text
playbook
-> inventory and host-pattern resolution
-> SSH/network connection
-> optional privilege escalation
-> module execution
-> ok/changed/failed/unreachable result
-> handler execution when notified
-> play recap
```

Ansible aims for **idempotence**: you can run the same automation again and it won't make unnecessary changes. This depends on picking the right modules and writing the playbook correctly. An arbitrary shell command isn't automatically safe to repeat.

### Core concepts: control node, inventory, modules, plays, roles, collections

| Term | Meaning |
| --- | --- |
| Control node | The machine where `ansible-core`, inventories, collections, and playbooks are installed |
| Managed node | A target host managed by Ansible - a permanently installed Ansible agent is normally not required |
| Inventory | Hosts, groups, and connection/group variables |
| Module | Reusable code that performs one focused operation, such as managing a package, file, user, or service |
| Task | One call to a module with arguments |
| Play | Maps an ordered list of tasks/roles to a host pattern |
| Playbook | One or more plays stored as YAML |
| Role | A standard directory structure for reusable tasks, handlers, defaults, variables, templates, and files |
| Collection | A distributable package containing modules, plugins, roles, and documentation |

The relationship between them, from largest to smallest unit of work:

```
Collection
   |
   v
Role
   |
   v
Playbook
   |
   v
Play
   |
   v
Task
   |
   v
Module
   |
   v
Managed Node
```

The inventory is what tells Ansible *which* managed nodes a play should run against - it sits alongside this chain rather than inside it.

### Installation and initial setup

Install `ansible-core` on the control node using the approved operating-system package or Python environment. Managed nodes normally need:

- Network reachability from the control node.
- SSH access for the approved remote user.
- Python when required by the selected modules.
- Approved `sudo`/privilege-escalation permission for privileged tasks.

Verify installation:

```bash
ansible --version
ansible-playbook --version
ansible-config dump --only-changed
```

Use SSH keys or an enterprise credential mechanism rather than embedding passwords in inventory. Validate host keys; do not globally disable host-key checking merely to make automation connect.

Typical project layout:

```text
ansible/
├── ansible.cfg
├── inventories/
│   ├── dev/
│   │   ├── hosts.yml
│   │   ├── group_vars/
│   │   └── host_vars/
│   └── prod/
│       ├── hosts.yml
│       ├── group_vars/
│       └── host_vars/
├── playbooks/
│   └── site.yml
├── roles/
├── collections/
│   └── requirements.yml
└── requirements.yml
```

Do not change `sshd_config` to enable password or root login as a default setup shortcut. Use the organization's approved SSH, bastion, identity and privilege-escalation design.

## Interview Questions

<details><summary>Q1. [Intermediate] How have you used Ansible? Give a real example.</summary>

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

</details>

<details><summary>Q2. [Basic] How do you configure an Ansible agent?</summary>

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

</details>
