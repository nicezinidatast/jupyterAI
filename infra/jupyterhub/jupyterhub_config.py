"""JupyterHub config — DockerSpawner + PlatformAuthenticator stub."""

import os

c = get_config()  # noqa: F821 — provided by jupyterhub at runtime

c.JupyterHub.bind_url = "http://:8000"
c.JupyterHub.authenticator_class = "platform_authenticator.PlatformAuthenticator"
c.JupyterHub.spawner_class = "dockerspawner.DockerSpawner"

c.DockerSpawner.image = os.environ.get("USER_IMAGE", "dataplatform/notebook-user:0.1.0")
c.DockerSpawner.remove = True
c.DockerSpawner.mem_limit = "4G"
c.DockerSpawner.cpu_limit = 2.0
c.DockerSpawner.network_name = os.environ.get("DOCKER_NETWORK", "dataplatform_default")

# Idle culler — 30 minutes
c.JupyterHub.services = [
    {
        "name": "idle-culler",
        "admin": True,
        "command": [
            "python",
            "-m",
            "jupyterhub_idle_culler",
            "--timeout=1800",
        ],
    }
]
