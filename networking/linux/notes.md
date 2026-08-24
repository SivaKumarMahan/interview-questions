# Linux Network Access Notes

## Q: How do you enable SSH key authentication between two Linux servers?

The goal is to let Server A connect to Server B with a key instead of a password.

### Generate a key on Server A

```bash
ssh-keygen -t ed25519
```

This generates two files:

- `~/.ssh/id_ed25519` — the private key. Keep it secure and never copy it to Server B.
- `~/.ssh/id_ed25519.pub` — the public key. This one is safe to copy to Server B.

### Copy the public key to Server B

```bash
ssh-copy-id user@serverB
```

This adds the public key to `~/.ssh/authorized_keys` on Server B with the right permissions.

### Test the connection

From Server A:

```bash
ssh user@serverB
```

SSH may ask for the private key's passphrase if you set one, but it should not ask for the remote account's password.

### How it works

- SSH uses public-key cryptography.
- Server B checks whether the public key is listed in `~/.ssh/authorized_keys`.
- Server A proves it holds the matching private key.
- The private key never leaves Server A.

---

## Q: What if SSH key authentication still asks for the account password?

On Server B, check the ownership and permissions:

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

Keep your current session open until a second session connects successfully. Disabling password authentication is a separate hardening step — only do that after key access and a backup access method are confirmed to work.

---
