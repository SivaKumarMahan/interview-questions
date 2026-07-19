# Ansible Cheatcode

## Inventory and connectivity

```bash
ansible-inventory -i inventory.yml --graph
ansible all -i inventory.yml -m ping
ansible all -i inventory.yml -m setup -a 'filter=ansible_distribution*'
ansible all -i inventory.yml -a 'uptime'
```

Ansible `ping` verifies SSH, Python/module execution, and response; it is not ICMP.

## Playbooks

```bash
ansible-playbook -i inventory.yml site.yml --syntax-check
ansible-playbook -i inventory.yml site.yml --check --diff
ansible-playbook -i inventory.yml site.yml --limit <canary-host>
ansible-playbook -i inventory.yml site.yml
```

## Vault

```bash
ansible-vault create group_vars/prod/vault.yml
ansible-vault edit group_vars/prod/vault.yml
ansible-vault encrypt <file>
ansible-vault decrypt <file>
```

Use an approved password/identity source; never pass a Vault password on the command line or commit it.

## Minimal safe play

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

Prefer modules to shell, validate in a canary, and verify application health after the play.
