# Ansible: Variables, Loops, Conditions, and Lookups

> Variable sources and types, loops, `when` conditions, and lookups.

## Key Concepts

### Variables

Variables describe environment and host differences without duplicating task logic.

Sources include:

- Role defaults.
- Inventory and dynamic inventory.
- `group_vars` and `host_vars`.
- Play variables.
- `vars_files`.
- Role variables.
- Facts.
- Registered task results.
- `set_fact`.
- Extra variables (`-e`/`--extra-vars`).

#### Static play variables

```yaml
---
- name: Install required packages
  hosts: webservers
  become: true
  vars:
    required_packages:
      - git
      - maven
      - nginx

  tasks:
    - name: Install packages
      ansible.builtin.package:
        name: "{{ required_packages }}"
        state: present
```

#### Extra variables

```yaml
---
- name: Manage an application user
  hosts: all
  become: true
  tasks:
    - name: Ensure requested user exists
      ansible.builtin.user:
        name: "{{ application_user }}"
        state: present
```

```bash
ansible-playbook -i inventories/dev/hosts.yml \
  playbooks/user.yml \
  --extra-vars 'application_user=deploy'
```

Extra variables have very high precedence. Treat externally supplied values as controlled input and validate them. Do not pass passwords directly on the command line because process listings, shell history and CI logs can expose them.

#### Registered variables

```yaml
- name: Read service status
  ansible.builtin.command:
    cmd: systemctl is-active nginx
  register: nginx_status
  changed_when: false
  failed_when: nginx_status.rc not in [0, 3]

- name: Display status
  ansible.builtin.debug:
    var: nginx_status.stdout
```

Registered variables exist for the current playbook run and are host-specific. A registered loop result contains a `results` list.

Variable precedence is detailed and important: when the same variable appears in several places, the higher-precedence source wins. Use:

```bash
ansible-inventory -i inventories/dev/hosts.yml --host web1
```

and targeted debug output to inspect resolved non-secret values.

### OS-specific variables with facts

A common real-world requirement: install "the web server package" across a mixed fleet of Debian- and RedHat-family hosts, where the package name differs per distribution family.

```yaml
---
- name: Configure web servers
  hosts: webservers
  become: true
  gather_facts: true

  vars:
    web_package_by_os:
      Debian: nginx
      RedHat: httpd

  tasks:
    - name: Install web server
      ansible.builtin.package:
        name: "{{ web_package_by_os[ansible_os_family] }}"
        state: present
```

`gather_facts: true` collects information such as `ansible_os_family`, `ansible_distribution`, hostname, IP addresses, and memory/CPU information. `ansible_os_family` is then used as the lookup key into the `web_package_by_os` dictionary:

```
Debian  -> nginx
RedHat  -> httpd
```

This is the idiomatic way to write one task that behaves correctly across different Linux families, instead of branching with `when` conditions for every package name.

### Loops

Modern playbooks normally use `loop`, and the current item is referenced as `item`:

```yaml
- name: Create application users
  ansible.builtin.user:
    name: "{{ item }}"
    state: present
  loop:
    - hardik
    - virat
    - rohit
```

Loop over dictionaries:

```yaml
- name: Create application directories
  ansible.builtin.file:
    path: "{{ item.path }}"
    state: directory
    owner: "{{ item.owner }}"
    group: "{{ item.group }}"
    mode: "{{ item.mode }}"
  loop:
    - path: /opt/orders
      owner: orders
      group: orders
      mode: "0750"
    - path: /var/log/orders
      owner: orders
      group: orders
      mode: "0750"
```

Use `loop_control` for clearer output:

```yaml
loop_control:
  label: "{{ item.path }}"
```

Legacy `with_items` remains recognizable, but `loop` is clearer for new content. The variable is `item`, not `items`.

### Conditions

`when` controls whether a task runs. It contains a raw Jinja expression and does not use `{{ }}` around the full condition.

```yaml
- name: Install Git on Red Hat-family systems
  ansible.builtin.dnf:
    name: git
    state: present
  when: ansible_facts['os_family'] == "RedHat"

- name: Install Git on Debian-family systems
  ansible.builtin.apt:
    name: git
    state: present
    update_cache: true
  when: ansible_facts['os_family'] == "Debian"
```

Condition based on a registered result:

```yaml
- name: Check whether configuration exists
  ansible.builtin.stat:
    path: /etc/orders/orders.conf
  register: orders_config

- name: Back up existing configuration
  ansible.builtin.copy:
    src: /etc/orders/orders.conf
    dest: /etc/orders/orders.conf.backup
    remote_src: true
    mode: preserve
  when: orders_config.stat.exists
```

For multiple required conditions:

```yaml
when:
  - maintenance_enabled | bool
  - ansible_facts['os_family'] == "Debian"
```

### Lookups

Lookups retrieve data on the **control node** from files, environment variables, secret systems or other sources.

```text
lookup(...) -> usually one value/string
query(...)  -> list, useful for loops
```

Read a control-node file:

```yaml
vars:
  welcome_text: "{{ lookup('ansible.builtin.file', playbook_dir + '/files/welcome.txt') }}"

tasks:
  - name: Display welcome text
    ansible.builtin.debug:
      msg: "Welcome: {{ welcome_text }}"
```

Don't use `debug` on a secret lookup result. For Azure Key Vault or another external secret provider, use the approved collection or plugin, an identity with only the access it needs, and `no_log`. Never copy the secret into inventory or source control.
