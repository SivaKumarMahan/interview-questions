# Linux Network Access Notes

## Q: How do you enable SSH key authentication between two Linux servers?

The goal is to allow Server A to connect to Server B with a key instead of the remote account's password.

### Generate a key on Server A

```bash
ssh-keygen -t ed25519
```

This generates:

- `~/.ssh/id_ed25519` → Private key; keep it secure and never copy it to Server B.
- `~/.ssh/id_ed25519.pub` → Public key; this is safe to copy to Server B.

### Copy the public key to Server B

```bash
ssh-copy-id user@serverB
```

This adds the public key to `~/.ssh/authorized_keys` with suitable permissions.

### Test the connection

From Server A:

```bash
ssh user@serverB
```

SSH may ask for the private-key passphrase if one was configured, but it should not ask for the remote account's password.

### How it works

- SSH uses public-key cryptography.
- Server B checks whether the public key exists in `~/.ssh/authorized_keys`.
- Server A proves that it holds the matching private key.
- The private key never leaves Server A.

---

## Q: What if SSH key authentication still asks for the account password?

On Server B, check ownership and permissions:

```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

Check `/etc/ssh/sshd_config`:

```text
PubkeyAuthentication yes
```

Test the configuration before reloading SSH:

```bash
sudo sshd -t
sudo systemctl reload sshd
```

Keep the current session open until a second session successfully connects. Disabling password authentication is a separate hardening change and should be done only after key access and an emergency access method are confirmed.

---
