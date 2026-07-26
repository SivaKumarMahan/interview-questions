# Ansible Notes

## Dynamic Inventory and Ansible Galaxy

Dynamic inventory plugins query an infrastructure provider, virtualization system, CMDB or another source at run time, then group hosts by trusted metadata. They are useful for cloud VMs whose private IPs change. Internal DNS names, a bastion, or an automation runner inside the private network can provide connectivity; inventory discovery does not bypass SSH/WinRM, firewall, authentication or host-key requirements.

Ansible Galaxy distributes reusable roles and collections. Install only reviewed, version-pinned content—for example `ansible-galaxy role install <role>` or `ansible-galaxy collection install <namespace.collection>`—and record dependency versions in `requirements.yml`. Review source, licenses, maintenance and secrets behavior before use; a community role should not receive unrestricted production credentials.
