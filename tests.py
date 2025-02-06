import unittest
from unittest.mock import patch, MagicMock
import sre
from click.testing import CliRunner
from kubernetes.client.rest import ApiException


class TestSRE(unittest.TestCase):
    @patch('sre.get_k8s_client')
    def test_list_deployments(self, mock_get_k8s_client):
        mock_api = MagicMock()
        mock_get_k8s_client.return_value = mock_api

        mock_deployments = [
            MagicMock(metadata=MagicMock(name='dep1', namespace='namespace1')),
            MagicMock(metadata=MagicMock(name='dep2', namespace='namespace2'))
        ]


        mock_api.list_deployment_for_all_namespaces.return_value.items = mock_deployments

        mock_deployments[0].metadata.name = 'dep1'
        mock_deployments[0].metadata.namespace = 'namespace1'
        mock_deployments[1].metadata.name = 'dep2'
        mock_deployments[1].metadata.namespace = 'namespace2'
        runner = CliRunner()
        result = runner.invoke(sre.list)

        mock_api.list_deployment_for_all_namespaces.assert_called_once()

        self.assertIn("Deployment: dep1 Namespace: namespace1", result.output)
        self.assertIn("Deployment: dep2 Namespace: namespace2", result.output)


    @patch('sre.get_k8s_client')
    def test_list_deployments_in_namespace(self, mock_get_k8s_client):
        mock_api = MagicMock()
        mock_get_k8s_client.return_value = mock_api
        mock_deployments = [
            MagicMock(metadata=MagicMock(name='dep1', namespace='namespace1')),
            MagicMock(metadata=MagicMock(name='dep2', namespace='namespace1'))
        ]
        mock_api.list_namespaced_deployment.return_value.items = mock_deployments
        mock_deployments[0].metadata.name = 'dep1'
        mock_deployments[0].metadata.namespace = 'namespace1'
        mock_deployments[1].metadata.name = 'dep2'
        mock_deployments[1].metadata.namespace = 'namespace1'
        runner = CliRunner()
        result = runner.invoke(sre.list, ['--namespace', 'namespace1'])
        mock_api.list_namespaced_deployment.assert_called_once_with(namespace='namespace1')

        self.assertIn("Deployment: dep1 Namespace: namespace1", result.output)
        self.assertIn("Deployment: dep2 Namespace: namespace1", result.output)

    @patch('sre.get_k8s_client')
    def test_scale_deployment(self, mock_get_k8s_client):
        mock_api = MagicMock()
        mock_get_k8s_client.return_value = mock_api
        mock_api.patch_namespaced_deployment.return_value = MagicMock()
        runner = CliRunner()
        result = runner.invoke(sre.scale, ['--deployment', 'myapp', '--replicas', 5, '--namespace', 'mynamespace'])
        mock_api.patch_namespaced_deployment.assert_called_with(
            name='myapp',
            namespace='mynamespace',
            body={'spec': {'replicas': 5}}
        )

        self.assertIn("Scaled deployment myapp to 5 replicas", result.output)

    @patch('sre.get_k8s_client')
    def test_info_deployment(self, mock_get_k8s_client):
        mock_api = MagicMock()
        mock_get_k8s_client.return_value = mock_api
        deployment = MagicMock()
        deployment.metadata.name = "myapp"
        deployment.metadata.namespace = "mynamespace"
        deployment.spec.replicas = 3
        deployment.status.replicas = 3
        deployment.status.available_replicas = 3
        deployment.spec.strategy.type = "RollingUpdate"
        mock_api.read_namespaced_deployment.return_value = deployment
        runner = CliRunner()
        result = runner.invoke(sre.info, ['--deployment', 'myapp', '--namespace', 'mynamespace'])

        self.assertIn("Deployment: myapp", result.output)
        self.assertIn("Namespace: mynamespace", result.output)
        self.assertIn("Replicas: 3", result.output)
        self.assertIn("Deployment Strategy: RollingUpdate", result.output)


    @patch('sre.get_k8s_client')
    @patch('sre.get_core_client')
    def test_pod_status_check(self, mock_get_core_client, mock_get_k8s_client):
        mock_api = MagicMock()
        mock_get_k8s_client.return_value = mock_api
        mock_core_api = MagicMock()
        mock_get_core_client.return_value = mock_core_api
        mock_deployment = MagicMock()
        mock_deployment.metadata.name = "myapp"
        mock_deployment.metadata.namespace = "mynamespace"
        mock_deployment.spec.replicas = 3
        mock_deployment.status.replicas = 3
        mock_deployment.status.available_replicas = 3
        mock_deployment.spec.template.metadata.labels = {"app": "myapp"}
        mock_api.read_namespaced_deployment.return_value = mock_deployment
        mock_pod = MagicMock()
        mock_pod.metadata.name = "myapp-pod-1"
        mock_pod.status.phase = "Running"
        mock_core_api.list_namespaced_pod.return_value.items = [mock_pod]
        runner = CliRunner()
        result = runner.invoke(sre.diagnostic, ['--deployment', 'myapp', '--namespace', 'mynamespace', '--pod'])

        self.assertIn("Pod: myapp-pod-1 - Status: Running", result.output)

    @patch('sre.get_k8s_client')
    def test_deployment_not_found(self, mock_get_k8s_client):
        mock_api = MagicMock()
        mock_get_k8s_client.return_value = mock_api
        mock_api.read_namespaced_deployment.side_effect = ApiException(status=404, reason="Not Found")
        runner = CliRunner()
        result = runner.invoke(sre.diagnostic, ['--deployment', 'nonexistent-deployment', '--namespace', 'mynamespace'])

        self.assertIn("Deployment nonexistent-deployment not found in namespace mynamespace", result.output)

if __name__ == '__main__':
    unittest.main()
