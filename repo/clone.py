"""TODO."""

import os
import pathlib
import shutil

import docker

IMAGE_NAME = "git-clone-image"
CONTAINER_WORKDIR = "/data"
CURRENT_DIR = pathlib.Path(__file__).parent


def downloads_directory() -> str:
    """Returns the directory where the repo will get cloned into."""
    return os.path.abspath(str(CURRENT_DIR.parent / "downloads"))


def clone_repo(repo: str) -> str:
    """Clones the given repo into a local directory."""
    client = docker.from_env()
    client.ping()
    client.images.build(
        path=str(CURRENT_DIR),
        dockerfile=str(CURRENT_DIR / "Dockerfile"),
        tag=IMAGE_NAME,
        rm=True,
        forcerm=True,
    )

    local_path = downloads_directory()
    if os.path.exists(local_path):
        shutil.rmtree(local_path)
    os.mkdir(local_path)

    if not repo.startswith("https://github.com/"):
        repo_url = f"https://github.com/{repo}"

    git_command = [
        "-c",
        "protocol.file.allow=never",
        "-c",
        "protocol.ext.allow=never",
        "clone",
        "--no-recurse-submodules",
        "--filter=blob:none",
        repo_url,
        CONTAINER_WORKDIR,
    ]
    client.containers.run(
        image=IMAGE_NAME,
        command=git_command,
        volumes={local_path: {"bind": CONTAINER_WORKDIR, "mode": "rw"}},
        working_dir=CONTAINER_WORKDIR,
        environment={"GIT_LFS_SKIP_SMUDGE": "1"},
        user="0:0",
        remove=True,
        detach=False,
        stdout=True,
        stderr=True,
    )

    return local_path
