# Ansible: Debugging and Troubleshooting

> Debugging playbooks and a troubleshooting flow for unreachable hosts, privilege failures, module errors, and unexpected changes.

## Key Concepts

### Debugging

Display a message:

```yaml
- name: Display managed-node information
  ansible.builtin.debug:
    msg:
      - "Inventory host: {{ inventory_hostname }}"
      - "Hostname: {{ ansible_facts['hostname'] }}"
      - "OS family: {{ ansible_facts['os_family'] }}"
      - "Memory MB: {{ ansible_facts['memtotal_mb'] }}"
      - "vCPUs: {{ ansible_facts['processor_vcpus'] }}"
```

Display a variable:

```yaml
- name: Display non-secret application settings
  ansible.builtin.debug:
    var: application_settings
    verbosity: 1
```

Useful verbosity:

```bash
ansible-playbook -i inventories/dev/hosts.yml \
  playbooks/site.yml -v

ansible-playbook -i inventories/dev/hosts.yml \
  playbooks/site.yml -vvv
```

Higher verbosity can reveal connection details, command arguments, and sensitive data. Use it carefully: redact shared logs, and apply `no_log: true` to tasks that handle secrets. `no_log` cuts down output exposure, but it won't fix a secret flow that's badly designed in the first place.

The final recap is more reliable than terminal color alone:

```text
ok changed unreachable failed skipped rescued ignored
```

Colors can be configured and may not render in every terminal or CI log.

### Troubleshooting flow

#### Host is unreachable

Check:

```bash
ansible web1 -i inventories/dev/hosts.yml \
  -m ansible.builtin.ping -vvv

ssh -vv automation@<resolved-host>
```

Investigate inventory address/user/port, DNS, route, NSG/firewall, bastion/proxy, private-key permissions, host-key mismatch and SSH service.

#### Permission denied or become failure

Check:

- Correct remote user.
- SSH key/identity.
- `become: true` or `--become` only where required.
- `sudo` policy for the automation user.
- Whether a password prompt is expected.
- File ownership and SELinux/AppArmor policy.

Do not fix the problem by giving unrestricted passwordless root access without review.

#### Module failure

Check:

- Fully qualified module name and collection installation.
- Module documentation:

```bash
ansible-doc ansible.builtin.copy
ansible-doc ansible.posix.authorized_key
```

- Required Python/interpreter on the managed node.
- Argument types and YAML indentation.
- Operating-system compatibility.
- Module return fields with appropriate verbosity.

#### Wrong hosts changed

Stop the run if it's safe to do so, and preserve evidence. Then check the inventory source and host pattern, and assess or restore the affected configuration. To prevent this, use separate inventories, `--list-hosts`, `--limit`, and require approval for broad patterns.

#### Task always reports changed

Prefer an idempotent module. If a command is unavoidable, set accurate `changed_when`, `failed_when`, `creates`, or `removes` behavior, and verify the real desired state.
