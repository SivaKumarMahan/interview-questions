# Ansible: Playbooks and Execution

> Playbook structure, running and validating playbooks, controlling runs with tags, limits, and forks, and handlers.

## Key Concepts

### Playbook structure

A valid modern playbook:

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
    - name: Select the web package
      ansible.builtin.set_fact:
        web_package: "{{ web_package_by_os[ansible_facts['os_family']] }}"

    - name: Install the web package
      ansible.builtin.package:
        name: "{{ web_package }}"
        state: present

    - name: Deploy web configuration
      ansible.builtin.template:
        src: web.conf.j2
        dest: /etc/web.conf
        owner: root
        group: root
        mode: "0644"
        validate: "/usr/local/bin/validate-web-config %s"
      notify: Restart web service

    - name: Ensure the service is running and enabled
      ansible.builtin.service:
        name: "{{ web_package }}"
        state: started
        enabled: true

  handlers:
    - name: Restart web service
      ansible.builtin.service:
        name: "{{ web_package }}"
        state: restarted
```

Key points:

- YAML indentation uses spaces, not tabs.
- A play targets `hosts`.
- `become: true` performs approved privilege escalation.
- Each task has a descriptive name.
- Fully qualified collection names such as `ansible.builtin.package` make module origin explicit.
- Module argument values describe desired state.
- A handler runs only when a notifying task reports `changed`.

### Nginx configuration playbook

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

### Running and validating playbooks

```bash
# Run with a specific inventory.
ansible-playbook -i inventories/dev/hosts.yml \
  playbooks/site.yml

# Parse and validate playbook syntax.
ansible-playbook -i inventories/dev/hosts.yml \
  playbooks/site.yml --syntax-check

# Predict changes where modules support check mode.
ansible-playbook -i inventories/dev/hosts.yml \
  playbooks/site.yml --check

# Show supported file/template differences.
ansible-playbook -i inventories/dev/hosts.yml \
  playbooks/site.yml --check --diff

# List tasks.
ansible-playbook -i inventories/dev/hosts.yml \
  playbooks/site.yml --list-tasks

# List tags.
ansible-playbook -i inventories/dev/hosts.yml \
  playbooks/site.yml --list-tags

# Start at an exact task name.
ansible-playbook -i inventories/dev/hosts.yml \
  playbooks/site.yml --start-at-task "Install the web package"
```

Check mode is a prediction, not a guarantee. Some modules don't support it fully, commands may get skipped or behave differently, and external systems can change between the check and the real run. Validate on a small environment or canary, then verify the real result.

`--start-at-task` is mainly for controlled recovery/debugging. Starting in the middle can skip prerequisites and produce an invalid state.

### Tags, limits and forks

#### Tags

```yaml
- name: Install NGINX
  ansible.builtin.package:
    name: nginx
    state: present
  tags:
    - install
    - web

- name: Deploy NGINX configuration
  ansible.builtin.template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
    mode: "0644"
  notify: Reload NGINX
  tags:
    - configure
    - web
```

```bash
# Execute matching tagged tasks.
ansible-playbook -i inventories/dev/hosts.yml \
  playbooks/site.yml --tags install

# Skip matching tagged tasks.
ansible-playbook -i inventories/dev/hosts.yml \
  playbooks/site.yml --skip-tags configure
```

Tags select tasks; they do not automatically guarantee that prerequisites ran.

#### Limits

```bash
# Restrict execution to one host.
ansible-playbook -i inventories/dev/hosts.yml \
  playbooks/site.yml --limit web1

# Restrict to a group intersection.
ansible-playbook -i inventories/prod/hosts.yml \
  playbooks/site.yml --limit 'webservers:&canary'
```

Always confirm the resulting host match. A mistyped pattern can match zero or unintended hosts.

#### Forks

```bash
ansible-playbook -i inventories/dev/hosts.yml \
  playbooks/site.yml --forks 10
```

`--forks 10` lets up to ten hosts run in parallel — it does not run ten tasks on one host. Pick your concurrency based on control-node capacity, network limits, any rate limits on dependencies, and how fast the service can safely roll out.

For controlled batches, use `serial`:

```yaml
- name: Rolling web deployment
  hosts: webservers
  serial: 2
  max_fail_percentage: 0
  tasks:
    - name: Deploy application
      ansible.builtin.include_role:
        name: web_application
```

### Handlers

Handlers perform an action only after a notifying task reports a change.

```yaml
tasks:
  - name: Deploy NGINX configuration
    ansible.builtin.template:
      src: nginx.conf.j2
      dest: /etc/nginx/nginx.conf
      owner: root
      group: root
      mode: "0644"
      validate: "nginx -t -c %s"
    notify: Reload NGINX

handlers:
  - name: Reload NGINX
    ansible.builtin.service:
      name: nginx
      state: reloaded
```

Handlers normally run near the end of the play and only once even if several changed tasks notify the same handler. Use `ansible.builtin.meta: flush_handlers` only when a subsequent task genuinely requires the handler to have run earlier.

A handler should normally react to a configuration or deployed artifact change. Installing a package and naming its handler identically does not clearly express intent.

## Interview Questions

### 1. Simpler Nginx playbook - and a validation trap

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
