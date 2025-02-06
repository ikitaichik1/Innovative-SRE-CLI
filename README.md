# SRE CLI Tool

This is a command-line interface (CLI) tool to manage and diagnose Kubernetes deployments, services, and pods.<br>
Write logs to "sre_cli.log" at the script's directory, Can modify path in [sre.py](./sre.py#L8)

## Features

- List deployments in a specific or all namespaces
- Scale deployments by specifying the number of replicas
- View detailed deployment information (replicas, strategy, associated services, endpoints, etc.)
- Run diagnostics to check the health of deployments and pods
- Rollout new changes by restarting deployments
- Fetch logs from deployments or specific pod
 
## Requirements

- Python 3.4+ (recommended: Python 3.8+).
- Kubernetes cluster with API access.
- Access to the `kubeconfig` file or Kubernetes in-cluster configuration. (Using config.load_incluster_config() or config.load_kube_config())

## Installation and usage

### 1. Install dependencies

```bash
pip install -r requirements.txt
or
pip install kubernetes click
```

### 2. Usage for sre.py
```bash
python sre.py [OPTIONS] COMMAND [ARGS]...
  Home Assignment: Innovative SRE CLI
Options:
  --help  Show this message and exit.

Commands:
  diagnostic
  info
  list
  logs
  rollout
  scale

```

**You can use sre.py COMMAND --help to see info about the command:**
```bash
python sre.py diagnostic --help
Usage: sre.py diagnostic [OPTIONS]

Options:
  --deployment TEXT  Name of the deployment to diagnose.  [required]
  --namespace TEXT   Namespace of the deployment to search in.  [required]
  --pod              This is a flag, pass for pod level diagnostics
  --help             Show this message and exit.
```

### 2. Usage for tests.py
```bash
python tests.py
```

