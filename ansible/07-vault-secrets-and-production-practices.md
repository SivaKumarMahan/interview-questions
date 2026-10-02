# Ansible: Vault, Secrets, and Production Practices

> Protecting secrets with Ansible Vault and running automation safely in production.

## Key Concepts

### Ansible Vault

Ansible Vault encrypts variables and files at rest.

```bash
# Create a new encrypted file.
ansible-vault create secret.yml

# Edit without leaving a deliberately decrypted copy.
ansible-vault edit secret.yml

# View encrypted content.
ansible-vault view secret.yml

# Encrypt an existing file.
ansible-vault encrypt vars.yml

# Decrypt a file. Use only through an approved process.
ansible-vault decrypt vars.yml

# Change the vault password.
ansible-vault rekey secret.yml

# Encrypt one value for embedding in a variable file.
ansible-vault encrypt_string --name database_password
```

Run a playbook and prompt for the vault password:

```bash
ansible-playbook -i inventories/prod/hosts.yml \
  playbooks/site.yml \
  --ask-vault-pass
```

For multiple vault identities:

```bash
ansible-playbook -i inventories/prod/hosts.yml \
  playbooks/site.yml \
  --vault-id prod@prompt
```

Important limitations:

- Vault protects data **at rest**, not while decrypted in memory or passed to a module.
- Do not commit a vault password file beside encrypted content.
- Do not print decrypted values through `debug`.
- Use `no_log: true` on tasks that might return a secret.
- Restrict who can obtain each vault identity/password.
- Prefer an approved external secret manager such as Azure Key Vault for centrally managed runtime secrets when appropriate.

### Safety and production practices

Before a Production run:

1. Review the pull request and exact commit.
2. Pin and install approved collection/role dependencies.
3. Run linting and `--syntax-check`.
4. Inspect inventory with `--graph` and `--list-hosts`.
5. Run check/diff mode where meaningful.
6. Limit execution to a canary.
7. Execute in controlled batches using `serial`.
8. Monitor failure threshold and application health.
9. Continue only when the canary is healthy.
10. Preserve the run result and change evidence.

Useful validation commands:

```bash
ansible-lint

ansible-playbook -i inventories/prod/hosts.yml \
  playbooks/site.yml --syntax-check

ansible-playbook -i inventories/prod/hosts.yml \
  playbooks/site.yml --list-hosts

ansible-playbook -i inventories/prod/hosts.yml \
  playbooks/site.yml \
  --check --diff \
  --limit canary
```

Security practices:

- Use dedicated automation identities.
- Use SSH agent, managed identity or the approved credential provider.
- Restrict and audit `sudo`.
- Validate SSH host keys.
- Keep secrets out of inventory, Git and logs.
- Use Ansible Vault or Azure Key Vault as appropriate.
- Set secure owner/group/mode on managed files.
- Review third-party collections and roles.
- Use `no_log` for secret-bearing results.
- Separate Development and Production inventory and credentials.

## Interview Questions

### 1. How do you manage secrets securely in Ansible?

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
