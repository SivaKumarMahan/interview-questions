# Installing Docker with Ansible

The role or playbook should configure Docker repeatably rather than use shell commands for every step. It installs repository prerequisites, configures Docker's signed package repository, installs a pinned/approved engine version, starts the service, and verifies it.

```yaml
---
- name: Install Docker Engine on Ubuntu
  hosts: docker_hosts
  become: true
  serial: 2

  tasks:
    - name: Install repository prerequisites
      ansible.builtin.apt:
        name:
          - ca-certificates
          - curl
        state: present
        update_cache: true

    - name: Configure Docker apt repository
      ansible.builtin.deb822_repository:
        name: docker
        types: [deb]
        uris: https://download.docker.com/linux/ubuntu
        suites: ["{{ ansible_distribution_release }}"]
        components: [stable]
        architectures: [amd64]
        signed_by: https://download.docker.com/linux/ubuntu/gpg
        state: present

    - name: Install Docker packages
      ansible.builtin.apt:
        name:
          - docker-ce
          - docker-ce-cli
          - containerd.io
        state: present
        update_cache: true

    - name: Enable and start Docker
      ansible.builtin.systemd_service:
        name: docker
        enabled: true
        state: started

    - name: Read installed Docker version
      ansible.builtin.command: docker version --format '{{ "{{" }}.Server.Version{{ "}}" }}'
      register: docker_version
      changed_when: false

    - name: Show installed version
      ansible.builtin.debug:
        var: docker_version.stdout
```

I test with syntax/lint and `--check --diff` where supported, deploy in batches, and verify service, socket permissions, container runtime, logging, disk retention, and monitoring. I do not automatically add every user to the `docker` group because access to the Docker socket is effectively root-equivalent. Package version and architecture should be variables for production roles.

