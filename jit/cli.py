import os
from contextlib import suppress
from typing import Annotated

import typer
from pathlib import Path

from jit.gitrepo import GitRepo, TreeEntry
from dotenv import load_dotenv

load_dotenv("../.env")

app = typer.Typer()

root_dir = None
git_repo = None


@app.command()
def init(repo_path: str):
    global root_dir
    repo: Path = Path(repo_path)
    root_dir = repo.absolute()
    git_repo = GitRepo.make(root_dir)
    print("Initializing repository at:", git_repo.root_dir)


def update_head(commit_sha):
    global git_repo
    head_path = git_repo.git_dir / "HEAD"
    with open(head_path, "w") as f:
        f.write(f"{commit_sha}")
    print("Updated HEAD to point to latest commit.")


@app.command()
def commit(message: Annotated[str, typer.Option("-m")]):
    global git_repo
    curr_dir = Path.cwd()
    git_path = curr_dir / ".git"
    if git_path is None:
        raise ValueError("Repository not initialized. Please run 'init' first.")
    git_repo = GitRepo.make(curr_dir)
    workspace_files = sorted(git_repo.list_files())
    entries = store_files(git_repo, workspace_files)
    tree_sha = store_tree(entries, git_repo)
    commit_sha = store_commit(git_repo, message, tree_sha)
    print(f"Tree sha: {tree_sha}\n")
    print(f"Commit sha: {commit_sha}\n")


def store_commit(git_repo, message, tree_sha):
    head_path = git_repo.git_dir / "HEAD"
    parent_sha = head_path.read_text().strip()
    commit_sha = git_repo.store_commit(
        tree_sha=tree_sha,
        message=message,
        parent_sha=parent_sha,
    )
    update_head(commit_sha)
    return commit_sha


def store_tree(entries, git_repo):
    tree_sha = git_repo.store_tree(entries)
    return tree_sha


def store_files(git_repo, workspace_files):
    entries = []
    for file in workspace_files:
        sha_hash = git_repo.store_file(file)
        entries.append(TreeEntry(file.name, sha=sha_hash))
    return entries


if __name__ == "__main__":
    app()
