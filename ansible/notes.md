# Ansible Notes

## Dynamic Inventory and Ansible Galaxy

A dynamic inventory plugin asks a cloud provider, virtualization system, CMDB, or other source for the current list of hosts, then groups them using metadata you trust. This is useful for cloud VMs, since their private IP addresses often change.

Dynamic inventory only discovers hosts — it doesn't skip normal connection rules. You still need working SSH or WinRM access, a firewall path that's actually open, valid authentication, and correct host keys. Internal DNS names, a bastion host, or an automation runner inside the private network can provide that connectivity.

Ansible Galaxy distributes reusable roles and collections. Only install content you've reviewed, and pin the version — for example:

```bash
ansible-galaxy role install <role>
ansible-galaxy collection install <namespace.collection>
```

Record the versions you depend on in `requirements.yml`.

Before using a community role or collection, check its source, license, and how well it's maintained, and check how it handles secrets. A community role should never get unrestricted production credentials.
