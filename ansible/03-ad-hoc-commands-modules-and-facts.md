# Ansible: Ad Hoc Commands, Modules, and Facts

> Running one-off ad hoc commands, what modules are, command vs shell, and gathering facts.

## Key Concepts

### Ad hoc commands

An ad hoc command performs a one-time task:

```text
ansible <host-pattern> -i <inventory> -m <module> -a '<arguments>'
```

Use ad hoc commands for investigation or carefully controlled one-time actions. Put repeatable configuration in a playbook under source control.

#### Connectivity and information

```bash
# Verify Ansible connectivity. This is not an ICMP ping.
ansible all -i inventories/dev/hosts.yml \
  -m ansible.builtin.ping

# Target one inventory group.
ansible webservers -i inventories/dev/hosts.yml \
  -m ansible.builtin.ping

# Run a command without a shell.
ansible all -i inventories/dev/hosts.yml \
  -m ansible.builtin.command \
  -a 'uptime'

ansible all -i inventories/dev/hosts.yml \
  -m ansible.builtin.command \
  -a 'df -h'

ansible all -i inventories/dev/hosts.yml \
  -m ansible.builtin.command \
  -a 'free -m'
```

Use `ansible.builtin.command` when shell features are not required. Use `ansible.builtin.shell` only when a command genuinely needs pipes, redirection, variable expansion or another shell feature.

```bash
ansible all -i inventories/dev/hosts.yml \
  -m ansible.builtin.shell \
  -a 'printf "Hello from %s\n" "$(hostname)"'
```

Shell input must be trusted and quoted carefully. Prefer purpose-built modules.

#### Files and directories

```bash
# Copy a control-node file to managed nodes.
ansible all -i inventories/dev/hosts.yml \
  -m ansible.builtin.copy \
  -a 'src=/etc/hosts dest=/tmp/hosts mode=0644'

# Create a directory.
ansible all -i inventories/dev/hosts.yml \
  -m ansible.builtin.file \
  -a 'path=/tmp/test_dir state=directory mode=0755'

# Create an empty file.
ansible all -i inventories/dev/hosts.yml \
  -m ansible.builtin.file \
  -a 'path=/tmp/file.txt state=touch mode=0644'

# Remove a file.
ansible all -i inventories/dev/hosts.yml \
  -m ansible.builtin.file \
  -a 'path=/tmp/file.txt state=absent'

# Ensure a line exists.
ansible all -i inventories/dev/hosts.yml \
  -m ansible.builtin.lineinfile \
  -a 'path=/tmp/test.conf line="feature=true" create=true'

# Remove a matching line.
ansible all -i inventories/dev/hosts.yml \
  -m ansible.builtin.lineinfile \
  -a 'path=/tmp/test.conf regexp="^feature=" state=absent'
```

#### Packages and services

Use the generic package module when the package name and behavior are portable:

```bash
ansible webservers -i inventories/dev/hosts.yml \
  --become \
  -m ansible.builtin.package \
  -a 'name=nginx state=present'
```

Use the operating-system-specific module when its features are required:

```bash
# Red Hat-family example.
ansible webservers -i inventories/dev/hosts.yml \
  --become \
  -m ansible.builtin.dnf \
  -a 'name=httpd state=present'

# Debian-family example.
ansible webservers -i inventories/dev/hosts.yml \
  --become \
  -m ansible.builtin.apt \
  -a 'name=nginx state=present update_cache=true'
```

Manage a service declaratively:

```bash
ansible webservers -i inventories/dev/hosts.yml \
  --become \
  -m ansible.builtin.service \
  -a 'name=nginx state=started enabled=true'

ansible webservers -i inventories/dev/hosts.yml \
  --become \
  -m ansible.builtin.service \
  -a 'name=nginx state=stopped'
```

#### Users and SSH keys

```bash
# Create a user.
ansible all -i inventories/dev/hosts.yml \
  --become \
  -m ansible.builtin.user \
  -a 'name=deploy state=present create_home=true'

# Remove a user. Review data-removal requirements before using remove=true.
ansible all -i inventories/dev/hosts.yml \
  --become \
  -m ansible.builtin.user \
  -a 'name=deploy state=absent'

# Add an approved public key to a user.
ansible all -i inventories/dev/hosts.yml \
  --become \
  -m ansible.posix.authorized_key \
  -a "user=deploy state=present key=\"{{ lookup('ansible.builtin.file', '/secure/path/deploy.pub') }}\""
```

`authorized_key` is in the `ansible.posix` collection, so declare/install the approved collection version.

#### Reboot

```bash
ansible webservers -i inventories/dev/hosts.yml \
  --become \
  -m ansible.builtin.reboot
```

A fleet-wide reboot is high impact, so don't just reboot `all` casually. Use `--limit`, serial or canary execution, maintenance approval, and a service-health check instead.

### Ad-hoc commands

Ad-hoc commands are one-line Ansible commands used for quick administrative or troubleshooting tasks, without writing a playbook.

Basic syntax:

```bash
ansible <host-pattern> -m <module> -a "<arguments>"
```

Examples:

```bash
ansible all -m ping

ansible all -m shell -a "df -h"

ansible all -m shell -a "free -m"

ansible all -m command -a "uptime"

ansible webservers -m ansible.builtin.package -a "name=nginx state=present" -b

ansible webservers -m ansible.builtin.service -a "name=nginx state=started" -b

ansible webservers -m ansible.builtin.service -a "name=nginx state=restarted" -b

ansible webservers -m ansible.builtin.service -a "name=nginx"

ansible webservers -m ansible.builtin.file -a "path=/opt/myapp state=directory mode=0755" -b

ansible webservers -m ansible.builtin.copy -a "src=app.conf dest=/etc/myapp/app.conf" -b
```

`-b` (`--become`) requests privilege escalation - most of these package/service/file operations need root.

**`command` vs `shell`**

- `command` is for straightforward commands with no shell features involved.
- `shell` is used when shell features such as pipes, redirection, and shell operators are required.

Ad-hoc commands are best for quick, one-off operations. Playbooks are better for repeatable, complex automation that needs to be version-controlled and reviewed.

### Facts

Facts are system information gathered from managed nodes. By default, a normal play gathers facts unless `gather_facts: false` is set.

```bash
# Gather all available facts.
ansible all -i inventories/dev/hosts.yml \
  -m ansible.builtin.setup

# Return selected facts.
ansible all -i inventories/dev/hosts.yml \
  -m ansible.builtin.setup \
  -a 'filter=ansible_os_family'

ansible all -i inventories/dev/hosts.yml \
  -m ansible.builtin.setup \
  -a 'filter=ansible_distribution*'

ansible all -i inventories/dev/hosts.yml \
  -m ansible.builtin.setup \
  -a 'filter=ansible_*_mb'

ansible all -i inventories/dev/hosts.yml \
  -m ansible.builtin.setup \
  -a 'filter=ansible_*'
```

Interface fact names depend on the host's interface names; do not assume every machine uses `eth0`.

Common facts and magic variables:

```yaml
ansible_facts['os_family']
ansible_facts['distribution']
ansible_facts['distribution_major_version']
ansible_facts['hostname']
ansible_facts['memtotal_mb']
ansible_facts['processor_vcpus']
inventory_hostname
inventory_hostname_short
group_names
groups
hostvars
ansible_play_hosts
ansible_play_batch
```

`inventory_hostname` is available even when fact gathering is disabled. `ansible_hostname` depends on gathered/cached facts.

## Interview Questions

<details><summary>Q1. [Basic] What is an Ansible module?</summary>

**Answer:**

A module is a reusable unit that Ansible runs to perform one action, for example `package`, `service`, `copy`, `user`, `template`, or a cloud-specific module.

Modules return structured facts like `changed`, `failed`, and their output. A well-written module is idempotent: applying the same desired state repeatedly produces the same result without extra changes.

A task calls one module. A playbook organizes plays, variables, handlers, and tasks together. I use fully qualified names such as `ansible.builtin.copy` so it's always clear where a module comes from.

</details>

<details><summary>Q2. [Basic] What is the difference between the <code>command</code> and <code>shell</code> modules?</summary>

**Answer:**

`ansible.builtin.command` runs a program directly, without a shell interpreting it. That means pipes, redirects, glob expansion, and variables don't work. It's the safer default because it avoids shell injection.

`ansible.builtin.shell` runs through a shell, so use it only when you genuinely need shell features.

Given the choice, I prefer a dedicated Ansible module over either one. Where I can, I use `creates`/`removes` or a module that's already idempotent, and I quote any variables carefully when `shell` really is unavoidable.

</details>
