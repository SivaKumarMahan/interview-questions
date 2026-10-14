# Ansible: Roles, Galaxy, and Configuration

> Reusable roles, Ansible Galaxy and collections, and `ansible.cfg` settings.

## Key Concepts

### Roles

Roles organize reusable content.

```bash
ansible-galaxy role init roles/webserver
```

Standard structure:

```text
roles/webserver/
├── defaults/main.yml
├── files/
├── handlers/main.yml
├── meta/main.yml
├── tasks/main.yml
├── templates/
├── tests/
└── vars/main.yml
```

- `defaults/`: Low-precedence defaults intended for callers to override.
- `vars/`: Higher-precedence role variables; use sparingly.
- `tasks/`: Main role tasks.
- `handlers/`: Handlers notified by role tasks.
- `templates/`: Jinja2 templates.
- `files/`: Static files.
- `meta/`: Role metadata and dependencies.

Example role task:

```yaml
# roles/webserver/tasks/main.yml
- name: Install web package
  ansible.builtin.package:
    name: "{{ webserver_package }}"
    state: present
```

Use the role:

```yaml
---
- name: Configure web servers
  hosts: webservers
  become: true
  roles:
    - role: webserver
```

Roles reduce duplication but should remain focused, documented, testable and versioned.

### Ansible Galaxy and collections

Ansible Galaxy distributes roles and collections.

```bash
# Search for roles.
ansible-galaxy role search nginx

# Show role details.
ansible-galaxy role info <namespace>.<role>

# Install a role.
ansible-galaxy role install <namespace>.<role>

# List installed roles.
ansible-galaxy role list

# Install a collection.
ansible-galaxy collection install azure.azcollection

# List installed collections.
ansible-galaxy collection list
```

Declare dependencies:

```yaml
# collections/requirements.yml
---
collections:
  - name: azure.azcollection
    version: "<approved-version>"
```

```bash
ansible-galaxy collection install \
  --requirements-file collections/requirements.yml
```

Review source, maintainer trust, license, version compatibility and security before using community content. Pin versions and test updates rather than downloading arbitrary latest content during a Production run.

### `ansible.cfg`

Example project-level configuration:

```ini
[defaults]
inventory = ./inventories/dev/hosts.yml
remote_user = automation
forks = 10
roles_path = ./roles
collections_path = ./collections
retry_files_enabled = False
interpreter_python = auto_silent

[privilege_escalation]
become = False
```

Configuration precedence and file discovery can cause surprises. Inspect active values:

```bash
ansible-config view
ansible-config dump --only-changed
ansible --version
```

Do not place private keys, passwords or vault passwords directly in `ansible.cfg`. Do not set `host_key_checking = False` globally without a reviewed risk decision.

## Interview Questions

<details><summary>Q1. [Basic] What is a playbook, and how would you install Nginx on 10 servers with Ansible?</summary>

**Answer:**

A **playbook** is a YAML file with one or more **plays**. Each play maps a group of hosts to an ordered list of **tasks**, and each task calls a **module** (for example `apt`, `dnf`, `service`, `template`). Modules are idempotent, so running the playbook again changes nothing if the servers are already in the desired state.

`inventories/prod/hosts.ini`:

```ini
[web]
web[01:10].example.com
```

`playbooks/nginx.yml`:

```yaml
- name: Install and start Nginx on web servers
  hosts: web
  become: true
  tasks:
    - name: Install nginx
      ansible.builtin.package:
        name: nginx
        state: present

    - name: Start and enable nginx
      ansible.builtin.service:
        name: nginx
        state: started
        enabled: true
```

```bash
ansible -i inventories/prod web -m ping                  # check connectivity first
ansible-playbook -i inventories/prod playbooks/nginx.yml --check --diff   # dry run
ansible-playbook -i inventories/prod playbooks/nginx.yml
```

Ansible runs on 5 hosts at a time by default (`forks = 5`); raise `forks` or use `serial` to control rolling batches.

</details>

<details><summary>Q2. [Basic] How do you structure an Ansible project?</summary>

**Answer:**

```text
ansible-project/
├── ansible.cfg                 # inventory path, roles path, forks, SSH settings
├── inventories/
│   ├── dev/
│   │   ├── hosts.ini
│   │   └── group_vars/
│   │       └── web.yml
│   └── prod/
│       ├── hosts.ini
│       ├── group_vars/
│       │   ├── all.yml
│       │   └── web.yml
│       └── host_vars/
│           └── web01.example.com.yml
├── playbooks/
│   ├── site.yml                # imports the other playbooks
│   └── nginx.yml
├── roles/
│   └── nginx/
│       ├── tasks/main.yml
│       ├── handlers/main.yml
│       ├── templates/nginx.conf.j2
│       ├── files/
│       ├── vars/main.yml
│       ├── defaults/main.yml   # lowest-priority, overridable variables
│       └── meta/main.yml       # role dependencies
├── collections/requirements.yml
└── README.md
```

Key points:

- One inventory folder per environment, so the same playbooks run against dev or prod by changing `-i`.
- Reusable logic lives in **roles**; playbooks just assign roles to host groups.
- Secrets are encrypted with **Ansible Vault** or pulled from a secret manager, never stored in plain text in `group_vars`.
- Pin collection and role versions in `requirements.yml`, and lint with `ansible-lint` in CI.

</details>
