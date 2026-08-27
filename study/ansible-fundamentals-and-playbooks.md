# Ansible Fundamentals and Playbooks

Core Ansible vocabulary, ad-hoc commands, OS-aware variables, and two versions of a real Nginx configuration playbook - including a common interview trap around configuration validation.

## Contents

1. [Core concepts](#1-core-concepts)
2. [Ad-hoc commands](#2-ad-hoc-commands)
3. [OS-specific variables](#3-os-specific-variables)
4. [Nginx configuration playbook](#4-nginx-configuration-playbook)
5. [Simpler Nginx playbook - and a validation trap](#5-simpler-nginx-playbook---and-a-validation-trap)

---

## 1. Core concepts

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

---

## 2. Ad-hoc commands

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

---

## 3. OS-specific variables

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

---

## 4. Nginx configuration playbook

A realistic playbook: install Nginx, push a validated configuration template, and reload only when the configuration actually changes.

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

What each piece is doing:

- `hosts: web` - run against the `web` inventory group.
- `become: true` - enables privilege escalation.
- `serial: 2` - updates two servers at a time instead of the whole fleet at once, so a bad config doesn't take down every web server simultaneously.
- `package` - installs Nginx idempotently (no-op if already installed).
- `template` - renders `nginx.conf.j2` and deploys it to `/etc/nginx/nginx.conf`.
- `validate: "nginx -t -c %s"` - runs `nginx -t` against the *rendered* file **before** it replaces the live configuration. If validation fails, the file is never put in place and the play fails safely.
- `notify: Reload Nginx` - triggers the handler only when the `template` task actually changes the file - not on every run.
- `service` - ensures Nginx is running and enabled at boot.
- The handler reloads Nginx (rather than restarting it), which is cheaper and doesn't drop existing connections.

---

## 5. Simpler Nginx playbook - and a validation trap

A shorter version, often used to test whether a candidate actually understands what each module does rather than pattern-matching keywords:

```yaml
- name: Configure web servers
  hosts: webservers
  become: true
  serial: 1
  tasks:
    - name: Install Nginx
      ansible.builtin.package:
        name: nginx
        state: present

    - name: Validate and enable Nginx
      ansible.builtin.service:
        name: nginx
        enabled: true
        state: started
```

**The trap:** the task is named "Validate and enable Nginx", but the `service` module does **not** validate the Nginx configuration. It only starts and enables the service - if the config is broken, `service` will happily try to start (or fail to start) Nginx without ever checking `nginx -t`.

Real validation has to come from somewhere else:

- Run `nginx -t` explicitly as a separate task (e.g. via the `command` module), or
- Use the `template` module's `validate` option (as in the fuller playbook above), which validates the *rendered* file before it's put in place.

Interview takeaway: don't assume a task name describes what a module actually does - check what the module's documented behavior is.
