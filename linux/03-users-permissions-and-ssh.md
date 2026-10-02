# Linux: Users, Permissions, and SSH

> File permissions and ownership, special bits, umask, users, groups and sudo, SSH keys and access, and basic server hardening.

## Key Concepts

### File Permissions: The Security Foundation

Understanding permissions prevents security issues and deployment failures.

#### Understanding the permission matrix

```text
rwx rwx rwx
│   │   └── Others (everyone else)
│   └────── Group (file's group)
└────────── Owner (file creator)

r = read (4)    - Can view file content
w = write (2)   - Can modify file
x = execute (1) - Can run file as program
```

#### Permission management in practice

```bash
# Symbolic notation (readable)
chmod u+x script.sh       # Give owner execute permission
chmod g-w file.txt        # Remove group write permission
chmod o+r document.pdf    # Give others read permission
chmod a+x binary          # Give everyone execute permission

# Numeric notation (faster once you learn it)
chmod 755 script.sh       # rwxr-xr-x (common for scripts)
chmod 644 config.txt      # rw-r--r-- (common for config files)
chmod 600 private.key     # rw------- (private keys)
chmod 777 file.txt        # rwxrwxrwx (AVOID THIS - security risk!)
```

#### Ownership management

```bash
# Change file ownership
sudo chown user:group file.txt      # Change both user and group
sudo chown jenkins config.yaml      # Change only owner
sudo chown :docker script.sh        # Change only group

# Recursive ownership changes
sudo chown -R nginx:nginx /var/www/html   # Change entire directory tree
```

#### Users, groups and special permissions

```bash
id username
groups username
sudo useradd --create-home --shell /bin/bash username
sudo passwd username
sudo usermod -aG application-team username
sudo userdel --remove username
```

Check your distribution's account-management policy before creating or deleting users. `useradd` defaults vary between distributions, and removing a home directory can destroy data. At scale, prefer a central identity system over local accounts.

The key account files are `/etc/passwd`, `/etc/shadow` and `/etc/group`. Password hashes live in `/etc/shadow`, which only privileged users can read. UID ranges for system versus regular users are distribution-configurable, so don't assume a universal `0–999` boundary.

There are also three special permission bits, set as an extra digit before the normal three:

| Bit | Value | Effect |
|---|---|---|
| setuid | `4000` | An executable runs with the file owner's identity, not the identity of whoever ran it. |
| setgid | `2000` | An executable runs with the file's group identity. On a directory, new files inherit that directory's group. |
| sticky bit | `1000` | On a shared directory, only a file's owner or a privileged user can delete or rename it. |

Audit these bits carefully. Executables with setuid or setgid set can be used to escalate privileges if misconfigured.

## Interview Questions

<details><summary>Q1. [Basic] What does <code>chmod 755</code> mean?</summary>

**Answer:**

The three octal digits are for owner, group, and others: read is 4, write is 2, execute is 1. `755` means the owner gets read, write, execute; the group and everyone else get read and execute. On a directory, read lets you list names, write lets you create or delete entries, and execute lets you enter or access entries. On a regular file, execute just means it can be run.

```bash
chmod 755 /opt/app/bin/start
stat -c '%A %a %U:%G %n' /opt/app/bin/start
```

I don't use 755 for everything — config files and secrets need tighter permissions, and shared directories often need setgid or ACLs instead. Permissions also depend on the parent directories, ACLs, mount options, and SELinux or AppArmor.

</details>

<details><summary>Q2. [Basic] What does <code>chmod 754</code> set?</summary>

**Answer:**

It sets `rwxr-xr--`: the owner can read, write, and execute (7); the group can read and execute (5); everyone else can only read (4). On a directory, execute means being able to enter or access entries inside it, so someone with only read permission can list the names in it but can't actually go into it.

I check the target and its current permissions with `ls -ld`, avoid making sensitive files world-readable, and use groups or ACLs when plain mode bits aren't precise enough.

</details>

<details><summary>Q3. [Basic] What is <code>chown</code>?</summary>

**Answer:**

`chown user:group path` changes both owner and group; `chgrp` changes only the group. Ownership is what standard Linux permission checks and service access are based on.

Before a recursive change, I preview it with `find` first, confirm the mount boundaries and any symlinks, and check what the application actually needs — a wrong `chown -R` on `/`, a database, or a whole system tree can break things or expose data. Where supported I use `chown -R --from=old:group new:group /explicit/path`, or a targeted `find -xdev` instead.

Afterward I verify with `stat` or `getfacl`, confirm the service still runs and can read and write as expected, and check the SELinux context separately since ownership doesn't fix that. I put the change into package or configuration management so it stays in place.

</details>

<details><summary>Q4. [Intermediate] A script is executable by one user but not another. How do you resolve this?</summary>

**Answer:**

I run the script as the failing user and see whether I get "Permission denied" or an interpreter-not-found error — that tells me a lot. Then I check `namei -l /path/script` (execute or traverse permission is needed on every parent directory), `ls -l` or `getfacl`, `id`, whether the shebang's interpreter is itself executable, line endings, whether the mount has `noexec`, and SELinux/AppArmor/audit logs.

Running `bash script` directly can help tell whether it's the execute bit or `noexec` versus a problem in the script itself, but it's not a real fix. I grant access through the right group, ACL, or ownership and the minimum directory traversal needed — never world-writable or 777. For SELinux, I restore the correct label or policy rather than turning SELinux off.

Sometimes the user needs a new session for a group change to take effect. I confirm the intended user can now run it and that anyone unauthorized still can't, then put the permissions into configuration management.

</details>

<details><summary>Q5. [Basic] How do you set default file and directory permissions?</summary>

**Answer:**

By default, new files start at 666 and directories at 777, minus the umask. A umask of `022` gives 644 for files and 755 for directories; `027` gives 640 and 750. I set this in the shell profile or, for a service, in systemd's `UMask=` — though the application itself may set an explicit mode regardless.

For a shared project directory, I use setgid plus a default ACL:

```bash
chmod 2770 /srv/team
setfacl -m g:team:rwx,d:g:team:rwx,d:o::--- /srv/team
getfacl /srv/team
```

I test by actually creating a file or directory as the service user. Umask doesn't change files that already exist, and ACLs can change the effective permission on top of it. I avoid defaults that are more open than necessary.

</details>

<details><summary>Q6. [Basic] What are sticky bit, setuid, and setgid?</summary>

**Answer:**

The sticky bit (`+t`) is used on shared directories like `/tmp`, which typically has mode `1777`. It means only the file's owner, the directory's owner, or a privileged user can delete or rename a file there. Setgid on a directory (`2xxx`) makes new files inside inherit the directory's group; setgid on an executable makes it run with the file's group instead of the caller's.

Setuid on an executable (`4xxx`) makes it run as the file's owner — often root. Linux generally ignores setuid on shell scripts.

These bits matter for security. I list them with `find / -xdev -perm /6000 -type f`, check what package they belong to and why they're there, and remove any that shouldn't be there through an approved change. I'd rather use `sudo`, Linux capabilities, or a proper service design than a custom setuid program, and I test and audit whatever I change.

</details>

<details><summary>Q7. [Intermediate] A user cannot log in. How will you troubleshoot?</summary>

**Answer:**

I split the problem into network and authentication. On the client side: DNS, IP reachability, whether the port is open, and `ssh -vvv` for detail. On the server, using console or another access path: is sshd running and listening, is its config valid (`sshd -t`), what does the firewall or SELinux say, and what's the exact reason in the auth log.

Then I check the account itself: `getent passwd`, whether it's locked or expired (`passwd -S`, `chage -l`), its shell and home directory, the Allow/Deny and PAM rules, group membership, and whether the key actually matches. For SSH, the home directory usually can't be writable by others, `.ssh` needs mode 700, `authorized_keys` needs mode 600 with the right owner, and SELinux context may need restoring.

I make the smallest fix that solves the problem, test that the user can now log in and that unauthorized access is still denied, and never loosen security broadly to work around this. I record the actual root cause — an expired account, a wrong key, a permission or config issue — and follow up with an expiry alert or better onboarding automation.

</details>

<details><summary>Q8. [Intermediate] A user was added to sudoers, but sudo still does not work. What could be wrong?</summary>

**Answer:**

I capture the exact error `sudo` gives, then run `id user` and `sudo -l -U user`, and check `/etc/sudoers` and any included files, their order, group membership and whether the session needs a refresh, hostname or command restrictions, `secure_path`, and the account's PAM state. I only validate syntax with `visudo -c`, and only edit with `visudo` or `visudo -f`.

I give the narrowest set of commands needed rather than `ALL=(ALL) ALL`, prefer a group-based rule managed through configuration management, and then test both an allowed command and one that should stay denied.

I check audit logs to confirm the access is actually being used. Note that `NOPASSWD` only skips the password prompt — it doesn't grant authorization by itself, so adding it is not a general fix for sudo problems.

</details>

<details><summary>Q9. [Intermediate] A user's home directory is missing. How will you restore it?</summary>

**Answer:**

I first confirm the account's home path with `getent passwd user`, check whether the filesystem or mount is actually there, and rule out a network home that's just temporarily unavailable versus one that was actually deleted. If I'm about to restore data, I stop the user's processes first so nothing is writing to it.

To recreate it: `install -d -m 700 -o user -g group /home/user`, copy `/etc/skel` only for the default files, restore from backup while preserving ownership, ACLs, and extended attributes, and fix the SELinux context with `restorecon` if needed.

I avoid running a recursive chown across mounted or shared data without reviewing the scope first. I check that login, shell, SSH, and application files work, compare the restore against the original timing and content, and look into how the directory was deleted. Then I put backup, tighter access, and lifecycle automation in place so it doesn't happen again.

</details>

<details><summary>Q10. [Basic] How will you change user access or privileges?</summary>

**Answer:**

I start from the approved role and the principle of least privilege — only granting what's actually needed: which systems, which commands, which files, and for how long. I prefer group-based access over one-off permissions for individual users.

For sudo, I create a narrow file under `/etc/sudoers.d/` using `visudo -f`, list the exact commands where practical, and avoid broad passwordless root access.

For data access, I use owner and group permission bits or ACLs (`setfacl`), and confirm with `namei -l` or `getfacl`. I test with `sudo -l -U user` and an actual, non-destructive command, keep an emergency admin session open, and log the ticket and expiry date.

When access is removed, I revoke the group membership, sudo rule, and key entries, end any active sessions if needed, and check that no alternate way to get that privilege was left open.

</details>

<details><summary>Q11. [Basic] How do you change user access / privileges? <em>(asked in interview round)</em></summary>

- Add to a group: `usermod -aG docker alice`.
- Grant sudo: add the user to the `wheel` or `sudo` group, or add a file under `/etc/sudoers.d/` (edit it with `visudo`).
- File permissions: `chmod`, `chown`, and ACLs (`setfacl`).
- Change shell or lock the account: `chsh`, `passwd -l user` to lock it, `usermod -L` or `-U`.
- Best practice: give people only the access they actually need, manage access through groups instead of one-off rules per user, and review `/etc/sudoers` regularly.

</details>

<details><summary>Q12. [Basic] Do you need a password or key for SSH?</summary>

**Answer:**

SSH supports passwords, public keys, certificates, multi-factor auth through PAM, and federated or session-based systems. In production and cloud environments, password login and direct root login are usually disabled, and access goes through keys, certificates, or a session manager like SSM instead.

The client proves it holds the private key; the server just stores the matching public key in `authorized_keys` with the right ownership and permissions.

The private key needs protecting — a passphrase, an agent, or hardware storage where possible — and it should never be copied broadly onto servers or into CI systems. Each person should have their own key. Access is logged, and keys get rotated or revoked.

If a key is lost, I remove its public key, issue a new pair through a process that verifies identity, test the new access before closing the recovery session, and treat the old private key as compromised if it might still exist somewhere.

</details>

<details><summary>Q13. [Basic] How do you list all SSH users?</summary>

**Answer:**

There's no single "list of SSH users" to query. I build the picture from accounts with an interactive shell (`getent passwd`, excluding ones set to `nologin` or `false`), the `AllowUsers`/`AllowGroups`/`Deny*` rules, PAM and directory groups, sudo rules, and authorized keys or SSH certificates.

To see who's actually using SSH, I check the auth logs and current sessions with `who`, `w`, `last`, and `journalctl -u sshd`.

I never print private or sensitive key material. What comes out of a review is: the user, who owns the account, why it exists, how it authenticates, its privilege level, when it was last used, and when it expires.

Stale accounts or keys get disabled through an approved process, and I monitor for new ones. Service accounts should use a non-interactive shell unless they genuinely need SSH.

</details>

<details><summary>Q14. [Basic] What command generates an SSH key?</summary>

**Answer:**

For a modern user key I use:

```bash
ssh-keygen -t ed25519 -a 100 -C "sunil@company-laptop-2026"
```

I put it in a protected path, set a strong passphrase, and use `ssh-agent` rather than leaving the private key unencrypted on disk. The `.pub` file gets shared; the private key never gets emailed, checked into a repository, or copied onto a server.

If policy or old compatibility requires RSA instead, I use RSA 3072 or 4096. I install the public key for the right account and test a second working session before removing any old access.

</details>

<details><summary>Q15. [Basic] Command to generate an SSH key <em>(asked in interview round)</em></summary>

```bash
ssh-keygen -t ed25519 -C "you@example.com"      # modern, preferred
ssh-keygen -t rsa -b 4096 -C "you@example.com"  # if ed25519 unsupported
```

This creates a private key at `~/.ssh/id_ed25519` and a public key at `~/.ssh/id_ed25519.pub`. Never share the private key. To copy the public key to a server, run `ssh-copy-id user@host` — it appends the key to `~/.ssh/authorized_keys`.

</details>

<details><summary>Q16. [Intermediate] How do you enable SSH key authentication between two Linux servers?</summary>

The goal is to let Server A connect to Server B with a key instead of a password.

#### Generate a key on Server A

```bash
ssh-keygen -t ed25519
```

This generates two files:

- `~/.ssh/id_ed25519` — the private key. Keep it secure and never copy it to Server B.
- `~/.ssh/id_ed25519.pub` — the public key. This one is safe to copy to Server B.

#### Copy the public key to Server B

```bash
ssh-copy-id user@serverB
```

This adds the public key to `~/.ssh/authorized_keys` on Server B with the right permissions.

#### Test the connection

From Server A:

```bash
ssh user@serverB
```

SSH may ask for the private key's passphrase if you set one, but it should not ask for the remote account's password.

#### How it works

- SSH uses public-key cryptography.
- Server B checks whether the public key is listed in `~/.ssh/authorized_keys`.
- Server A proves it holds the matching private key.
- The private key never leaves Server A.

</details>

<details><summary>Q17. [Intermediate] What if SSH key authentication still asks for the account password?</summary>

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

</details>

<details><summary>Q18. [Intermediate] You cannot SSH into a remote machine. How do you debug?</summary>

**Answer:**

I let the exact client error guide the next step. A timeout points to routing, a firewall, or a security group. "Connection refused" means nothing is listening. "Permission denied" means the connection reached SSH but authentication failed.

I run `ssh -vvv user@host`, check DNS resolves correctly, and test `nc -vz host 22` from the same network the client is on.

Using console or bastion access, I check `ss -lntp`, `systemctl status sshd`, `sshd -t`, the host firewall, disk space, and `/var/log/auth.log` or `/var/log/secure`. For key problems I check the intended user, the ownership of the home directory and `.ssh`, that `.ssh` is mode `700`, that `authorized_keys` is mode `600`, and the server's SSH configuration.

I make one controlled fix at a time and retest. I don't weaken authentication or open port 22 to the whole internet as a shortcut.

</details>

<details><summary>Q19. [Intermediate] Ping works, but SSH fails using hostname. Why?</summary>

**Answer:**

Ping only proves an ICMP reply came back — it doesn't prove TCP port 22 or SSH authentication works. I compare `getent ahosts hostname` against the expected IP, test both `ssh -vvv user@hostname` and `ssh user@IP`, and check `nc -vz hostname 22`.

If the IP works but the hostname doesn't, the likely causes are a stale or wrong DNS record, IPv6 being picked when only IPv4 works, an SSH `Host` rule in `~/.ssh/config`, or a host-key mismatch after the address changed.

I fix the DNS or client config, and I verify the host key through a trusted source before updating `known_hosts`. I never just delete a host-key warning, since it can be a sign of a man-in-the-middle attack.

</details>

<details><summary>Q20. [Intermediate] What do you do if a user loses an SSH private key?</summary>

**Answer:**

I treat the key as potentially compromised. Using a separate, approved admin path, I find and remove its exact public-key line from every `authorized_keys` file, bastion, Git service, and automation account that trusted it.

I check the authentication logs for that key's fingerprint or user, and rotate other secrets if the lost device could have exposed them too.

The user generates a new passphrase-protected key on a trusted device, and administrators only ever receive the public half. I add it with correct ownership and permissions, test that it works, and record who owns it, why, and when it expires.

I never try to reconstruct or send a replacement private key over any channel. Centralized SSH certificates or managed access make future revocation and expiry much easier to handle.

</details>

<details><summary>Q21. [Intermediate] What if a user loses their SSH key? <em>(asked in interview round)</em></summary>

You cannot recover the private key. It was never stored on the server, so it is gone for good.

1. Generate a new key pair on the client.
2. Push the new public key to the server. If SSH access is lost entirely, use another path in: the cloud console or a serial connection, an SSM session, a bastion host with a separate credential, or a configuration tool like Ansible to add the new key.
3. Remove the old public key from `~/.ssh/authorized_keys` so it can no longer log in. Rotate anything that key could have reached.

</details>

<details><summary>Q22. [Advanced] You need to secure a Linux server exposed to the internet with a weak root password. What steps do you take?</summary>

**Answer:**

I treat this as a possible compromise, not just a hardening exercise. I restrict access at the cloud firewall to approved networks, preserve authentication and audit evidence, and review successful logins, user accounts, SSH keys, sudo changes, running processes, anything persistent, and outbound connections.

If I suspect it was actually compromised, I isolate it and rebuild from a trusted image rather than trying to clean it in place.

I rotate the root password and every reachable secret, create named admin accounts with least privilege — meaning only the access each person actually needs — sudo, and MFA or bastion access, test that the new access works, then set `PermitRootLogin no` and normally turn off password-based SSH entirely.

I patch the system, remove services that aren't needed, turn on the host firewall and SELinux, centralize logs, and enable something like fail2ban or an EDR tool where it fits, and confirm backups are working.

I make these changes with a second session or console open, so I don't lock administrators out by mistake.

</details>
