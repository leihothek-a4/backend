# Backend Setup

## Prerequisites

Install Ansible:
```bash
sudo apt update
sudo apt install ansible
```

## Installation

Run the Ansible playbook to install all system dependencies:
```bash
ansible-playbook playbook.yml
```

## Post-Installation

Activate the virtual environment:
```bash
source venv/bin/activate
```

Your Python environment is now ready with all dependencies installed.
