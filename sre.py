import click
import logging
import os
from kubernetes import client, config
import readline
from kubernetes.client.rest import ApiException
from kubernetes.config import ConfigException

log_file = "sre_cli.log"
try:
    open(log_file, 'a').close()
    os.chmod(log_file, 0o666)
except Exception:
    pass

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def get_k8s_client():
    try:
        config.load_incluster_config()
    except ConfigException:
        config.load_kube_config()
    return client.AppsV1Api()


def get_core_client():
    try:
        config.load_incluster_config()
    except ConfigException:
        config.load_kube_config()
    return client.CoreV1Api()


def completer(text, state):
    """Auto-completion for CLI commands."""
    options = ['list', 'scale', 'rollout', 'diagnostic']
    matches = [cmd for cmd in options if cmd.startswith(text)]
    return matches[state] if state < len(matches) else None


readline.parse_and_bind("tab: complete")
readline.set_completer(completer)


@click.group()
def cli():
    """Home Assignment: Innovative SRE CLI"""
    pass


@click.command()
@click.option('--namespace', help='List deployments in the specified namespace, if not specified will list deployments in all namespaces')
def list(namespace):
    api = get_k8s_client()
    logging.info(f"-- list started --")
    try:
        if namespace:
            deployments = api.list_namespaced_deployment(namespace=namespace).items
        else:
            deployments = api.list_deployment_for_all_namespaces().items
        for dep in deployments:
            click.echo(f"Deployment: {dep.metadata.name} Namespace: {dep.metadata.namespace}")
            logging.info(f"Listed deployment: {dep.metadata.name} in {dep.metadata.namespace}")
    except Exception as e:
        logging.error(f"Error listing deployments: {e}")
        click.echo(f"Error listing deployments: {e}", err=True)


@click.command()
@click.option('--deployment', required=True, help='Name of the deployment to scale.')
@click.option('--replicas', required=True, type=int, help='Number of replicas to scale to.')
@click.option('--namespace', help='Namespace of the deployment, if not specified will search in all namespaces')
def scale(deployment, replicas, namespace):
    api = get_k8s_client()
    logging.info(f"-- scale started --")
    try:
        if replicas <= 0:
            click.echo("Replicas must be a positive integer.", err=True)
            return

        if namespace:
            deployment_obj = api.read_namespaced_deployment(name=deployment, namespace=namespace)
        else:
            deployments = []
            for d in api.list_deployment_for_all_namespaces().items:
                if d.metadata.name == deployment:
                    deployments.append(d)

            if not deployments:
                click.echo(f"Deployment {deployment} not found in any namespace.", err=True)
                logging.error(f"Deployment {deployment} not found in any namespace.")
                return

            if len(deployments) > 1:
                click.echo("Multiple deployments have the same name:")
                for i, dep in enumerate(deployments, 1):
                    click.echo(f"{i}. Namespace: {dep.metadata.namespace}")
                choice = click.prompt("Enter the number of the namespace to scale", type=int)
                if choice < 1 or choice > len(deployments):
                    click.echo("Invalid selection.", err=True)
                    return

                deployment_obj = deployments[choice-1]
            else:
                deployment_obj = deployments[0]

        deployment_obj.spec.replicas = replicas
        api.patch_namespaced_deployment(name=deployment_obj.metadata.name, namespace=deployment_obj.metadata.namespace, body=deployment_obj)

        click.echo(f"Scaled deployment {deployment} to {replicas} replicas in namespace {deployment_obj.metadata.namespace}")
        logging.info(f"Scaled {deployment} to {replicas} replicas in {deployment_obj.metadata.namespace}")

    except ConfigException as e:
        logging.error(f"Kubernetes configuration error: {e}")
        click.echo(f"Kubernetes configuration error: {e}. Please check your kubeconfig.", err=True)

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        click.echo(f"An unexpected error occurred: {e}", err=True)



@click.command()
@click.option('--deployment', required=True, help='Name of the deployment to show.')
@click.option('--namespace', help='Namespace of the deployment, if not specified will show info of first deployment found')
def info(deployment, namespace):
    api = get_k8s_client()
    core_api = get_core_client()

    try:
        if not namespace:
            click.echo(f"Namespace {namespace} not specified. Please specify a namespace.")
            deployments = []
            for d in api.list_deployment_for_all_namespaces().items:
                if d.metadata.name == deployment:
                    deployments.append(d)
            if not deployments:
                click.echo(f"Deployment {deployment} not found in any namespace.", err=True)
                logging.error(f"Deployment {deployment} not found in any namespace.")
                return

            dep = deployments[0]
            namespace = dep.metadata.namespace
        else:
            dep = api.read_namespaced_deployment(name=deployment, namespace=namespace)

        click.echo(f"Deployment: {dep.metadata.name}")
        click.echo(f"Namespace: {dep.metadata.namespace}")
        click.echo(f"Replicas: {dep.spec.replicas}")
        click.echo(f"Deployment Strategy: {dep.spec.strategy.type}")
        logging.info(f"-- info started --")
        logging.info(f"Deployment {deployment} - Desired: {dep.spec.replicas}, Current: {dep.status.replicas}, Available: {dep.status.available_replicas}")

        try:
            svc = core_api.read_namespaced_service(name=deployment, namespace=namespace)
            click.echo("Associated Service:")
            click.echo(f"- Service: {svc.metadata.name}")
            logging.info(f"Service: {svc.metadata.name} in namespace {namespace}")
            click.echo(f"-  Type: {svc.spec.type}")
            click.echo(f"-  Ports: {', '.join([str(port.port) for port in svc.spec.ports])}")
            logging.info(f"Service {svc.metadata.name} has ports: {', '.join([str(port.port) for port in svc.spec.ports])}")
        except ApiException as e:
            logging.warning(f"Service {dep.metadata.name} not found in namespace {namespace}")
            click.echo(f"No service named {dep.metadata.name} found in namespace {namespace}", err=True)

        try:
            ep = core_api.read_namespaced_endpoints(name=deployment, namespace=namespace)
            click.echo("Associated Endpoints:")
            click.echo(f"- Endpoint: {ep.metadata.name}")
            logging.info(f"Endpoint: {ep.metadata.name} in namespace {namespace}")
            for subset in ep.subsets:
                for address in subset.addresses or []:
                    click.echo(f"- Address: {address.ip}")
                    logging.info(f"Endpoint {ep.metadata.name} has address: {address.ip}")
        except ApiException as e:
            logging.warning(f"Endpoints for service {dep.metadata.name} not found in namespace {namespace}")
            click.echo(f"No endpoints found for service {dep.metadata.name} in namespace {namespace}", err=True)


    except ApiException as e:
        if e.status == 404:
            logging.error(f"Deployment {deployment} not found in namespace {namespace}")
            click.echo(f"Deployment {deployment} not found in namespace {namespace}", err=True)
        else:
            logging.error(f"API error occurred: {e}")
            click.echo(f"API error occurred: {e}", err=True)

    except ConfigException as e:
        logging.error(f"Kubernetes configuration error: {e}")
        click.echo(f"Kubernetes configuration error: {e}. Please check your kubeconfig.", err=True)

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        click.echo(f"An unexpected error occurred: {e}", err=True)


@click.command()
@click.option('--deployment', required=True, help='Name of the deployment to diagnose.')
@click.option('--namespace', required=True, help='Namespace of the deployment to search in.')
@click.option('--pod', is_flag=True,help='Include pod-level diagnostics, such as pending, failed, or crash-looping pods.')
def diagnostic(deployment, namespace, pod):
    api = get_k8s_client()
    core_api = get_core_client()

    try:
        dep = api.read_namespaced_deployment(name=deployment, namespace=namespace)

        click.echo(f"Deployment: {dep.metadata.name}")
        click.echo(f"Namespace: {dep.metadata.namespace}")
        click.echo(f"Desired Replicas: {dep.spec.replicas}")
        click.echo(f"Current Replicas: {dep.status.replicas}")
        click.echo(f"Available Replicas: {dep.status.available_replicas}")
        logging.info(f"-- diagnostics started --")
        logging.info(f"Deployment {deployment} - Desired: {dep.spec.replicas}, Current: {dep.status.replicas}, Available: {dep.status.available_replicas}")


        if dep.spec.replicas != dep.status.replicas:
            click.echo(
                f"Warning: Desired replicas ({dep.spec.replicas}) don't match current replicas ({dep.status.replicas})!")
            logging.warning(
                f"Desired replicas ({dep.spec.replicas}) don't match current replicas ({dep.status.replicas})!")

        if dep.status.replicas != dep.status.available_replicas:
            click.echo(
                f"Warning: Not all replicas are available. Available: {dep.status.available_replicas}, Total: {dep.status.replicas}")
            logging.warning(
                f"Not all replicas are available. Available: {dep.status.available_replicas}, Total: {dep.status.replicas}")


        if pod:
            labels = dep.spec.template.metadata.labels
            if not labels:
                click.echo(f"Deployment {deployment} has no labels.")
                return

            label_selector = ""
            for key, value in labels.items():
                if label_selector:
                    label_selector += ","
                label_selector += f"{key}={value}"
            pods = core_api.list_namespaced_pod(namespace=namespace, label_selector=label_selector).items

            if not pods:
                click.echo(f"No pods found for deployment {deployment} in namespace {namespace}.")
                logging.warning(f"No pods found for deployment {deployment} in namespace {namespace}")
                return

            for p in pods:
                click.echo(f"\nPod: {p.metadata.name} - Status: {p.status.phase}")
                logging.info(f"Pod: {p.metadata.name} - Status: {p.status.phase}")


                for container_status in p.status.container_statuses:
                    if container_status.state.waiting:
                        waiting_reason = container_status.state.waiting.reason
                        click.echo(f"  Container: {container_status.name} - Waiting due to: {waiting_reason}")
                        logging.info(f"Container: {container_status.name} - Waiting due to: {waiting_reason}")

                    elif container_status.state.terminated:
                        terminated_reason = container_status.state.terminated.reason
                        click.echo(f"  Container: {container_status.name} - Terminated due to: {terminated_reason}")
                        logging.info(f"Container: {container_status.name} - Terminated due to: {terminated_reason}")

                    elif container_status.state.running:
                        click.echo(f"  Container: {container_status.name} - Running successfully")
                        logging.info(f"Container: {container_status.name} - Running successfully")

                    if container_status.resources:
                        cpu_request = container_status.resources.requests.get('cpu', 'Not Set')
                        memory_request = container_status.resources.requests.get('memory', 'Not Set')
                        cpu_limit = container_status.resources.limits.get('cpu', 'Not Set')
                        memory_limit = container_status.resources.limits.get('memory', 'Not Set')

                        click.echo(
                            f"  Container Resources - CPU Request: {cpu_request}, Memory Request: {memory_request}")
                        click.echo(f"  Container Resources - CPU Limit: {cpu_limit}, Memory Limit: {memory_limit}")
                        logging.info(
                            f"Container Resources for {container_status.name} - CPU Request: {cpu_request}, Memory Request: {memory_request}, CPU Limit: {cpu_limit}, Memory Limit: {memory_limit}")


                if p.status.phase in ["Failed", "Unknown", "Pending"]:
                    click.echo(f"Pod {p.metadata.name} is in {p.status.phase} state. Further investigation is required.")
                    logging.warning(f"Pod {p.metadata.name} is in {p.status.phase} state.")

                for container in p.spec.containers:
                    click.echo(f"    CPU Request: {container.resources.requests.get('cpu', 'Not set')}")
                    click.echo(f"    CPU Limit: {container.resources.limits.get('cpu', 'Not set')}")
                    click.echo(f"    Memory Request: {container.resources.requests.get('memory', 'Not set')}")
                    click.echo(f"    Memory Limit: {container.resources.limits.get('memory', 'Not set')}")
                    logging.info(f"Container {container.name} - CPU Request: {container.resources.requests.get('cpu', 'Not set')}, CPU Limit: {container.resources.limits.get('cpu', 'Not set')}, Memory Request: {container.resources.requests.get('memory', 'Not set')}, Memory Limit: {container.resources.limits.get('memory', 'Not set')}")

                total_restarts = sum(container.restart_count for container in p.status.container_statuses)
                if total_restarts > 0:
                    click.echo(f"Pod {p.metadata.name} has {total_restarts} restarts.")
                    logging.warning(f"Pod {p.metadata.name} has {total_restarts} restarts.")


    except ApiException as e:
        if e.status == 404:
            logging.error(f"Deployment {deployment} not found in namespace {namespace}")
            click.echo(f"Deployment {deployment} not found in namespace {namespace}", err=True)
        else:
            logging.error(f"API error occurred: {e}")
            click.echo(f"API error occurred: {e}", err=True)

    except ConfigException as e:
        logging.error(f"Kubernetes configuration error: {e}")
        click.echo(f"Kubernetes configuration error: {e}. Please check your kubeconfig.", err=True)

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        click.echo(f"An unexpected error occurred: {e}", err=True)

@click.command()
@click.option('--deployment', required=True, help='Name of the deployment to restart.')
@click.option('--namespace', required=True, help='Namespace of the deployment.')
def rollout(deployment, namespace):
    try:
        api = get_k8s_client()
        logging.info(f"-- rollout started --")
        api.read_namespaced_deployment(name=deployment, namespace=namespace)
        patch_body = {"spec": {"template": {"metadata": {"annotations": {"kubectl.kubernetes.io/restartedAt": "now"}}}}}
        api.patch_namespaced_deployment(name=deployment, namespace=namespace, body=patch_body)
        click.echo(f"Rolled out deployment {deployment} in namespace {namespace}")
        logging.info(f"Rolled out deployment {deployment} in namespace {namespace}")

    except ApiException as e:
        if e.status == 404:
            logging.error(f"Deployment {deployment} not found in namespace {namespace}")
            click.echo(f"Deployment {deployment} not found in namespace {namespace}", err=True)
        else:
            logging.error(f"API error occurred: {e}")
            click.echo(f"API error occurred: {e}", err=True)

    except ConfigException as e:
        logging.error(f"Kubernetes configuration error: {e}")
        click.echo(f"Kubernetes configuration error: {e}. Please check your kubeconfig.", err=True)

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        click.echo(f"An unexpected error occurred: {e}", err=True)


@click.command()
@click.option('--deployment', help='Name of the deployment to fetch logs from.')
@click.option('--pod', help='Name of the pod to fetch logs from.')
@click.option('--namespace', required=True, help='Namespace of the deployment.')
@click.option('--tail', default=50, type=int, help='Number of log lines to retrieve. Default is 50.')
def logs(deployment, pod, namespace, tail):
    api = get_k8s_client()
    core_api = get_core_client()

    if not deployment and not pod:
        click.echo("You must specify either --deployment or --pod.", err=True)
        return

    logging.info("-- logs started --")

    try:
        if deployment:
            dep = api.read_namespaced_deployment(name=deployment, namespace=namespace)

            labels = dep.spec.template.metadata.labels
            if not labels:
                click.echo(f"Deployment {deployment} has no labels.")
                return

            label_selector = ""
            for key, value in labels.items():
                if label_selector:
                    label_selector += ","
                label_selector += f"{key}={value}"
            pods = core_api.list_namespaced_pod(namespace=namespace, label_selector=label_selector).items
            if not pods:
                click.echo(f"No pods found for deployment {deployment} in namespace {namespace}.", err=True)
                logging.error(f"No pods found for deployment {deployment} in namespace {namespace}.")
                return

            for pod_obj in pods:
                fetch_pod_logs(core_api, pod_obj.metadata.name, namespace, tail)

        elif pod:
            fetch_pod_logs(core_api, pod, namespace, tail)

    except ApiException as e:
        if e.status == 404:
            logging.error(f"Resource not found: {e}")
            click.echo(f"Resource not found: {e}", err=True)
        else:
            logging.error(f"API error occurred: {e}")
            click.echo(f"API error occurred: {e}", err=True)

    except ConfigException as e:
        logging.error(f"Kubernetes configuration error: {e}")
        click.echo(f"Kubernetes configuration error: {e}. Please check your kubeconfig.", err=True)

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        click.echo(f"An unexpected error occurred: {e}", err=True)


def fetch_pod_logs(core_api, pod_name, namespace, tail):
    try:
        log_params = {"name": pod_name, "namespace": namespace, "tail_lines": tail}

        logs = core_api.read_namespaced_pod_log(**log_params)

        click.echo(f"Logs for pod {pod_name} (namespace: {namespace}):")
        click.echo(logs if logs else "No logs available.")

        logging.info(f"Fetched logs for pod {pod_name} in namespace {namespace}")

    except ApiException as e:
        logging.warning(f"Could not retrieve logs for pod {pod_name}: {e}")
        click.echo(f"Could not retrieve logs for pod {pod_name}: {e}", err=True)


cli.add_command(list)
cli.add_command(scale)
cli.add_command(info)
cli.add_command(diagnostic)

cli.add_command(rollout)
cli.add_command(logs)

if __name__ == '__main__':
    cli()


