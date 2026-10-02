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
