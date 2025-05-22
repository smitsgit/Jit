import os
from contextlib import suppress
from typing import Annotated, List

import typer
from pathlib import Path

from .gitrepo import GitRepo, FileEntry, DirEntry
from dotenv import load_dotenv

load_dotenv("../.env")

app = typer.Typer()

root_dir = None
git_repo = None

REGULAR_MODE = "100644"
EXECUTALE_MODE = "100755"

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
    root_tree_sha = None
    tree_container = {}


    curr_dir = Path.cwd()
    git_path = curr_dir / ".git"
    if git_path is None:
        raise ValueError("Repository not initialized. Please run 'init' first.")
    git_repo = GitRepo.make(curr_dir)
    roots = get_roots(git_repo.root_dir)
    for root in roots:
        print("Root", root)
        files, dirs = git_repo.list_files(root)
        print("Files - dirs", files, dirs)
        entries = store_files(git_repo, files)
        dir_entries = []
        for dir in dirs:
            dir_tree_sha = tree_container[str(root/dir)]
            dir_entries.append(DirEntry(dir.name, sha=dir_tree_sha))
        tree_sha = store_tree(entries, dir_entries, git_repo)
        tree_container[str(root)] = tree_sha
        root_tree_sha = tree_sha

    commit_sha = store_commit(git_repo, message, root_tree_sha)
    print(f"Tree sha: {root_tree_sha}\n")
    print(f"Commit sha: {commit_sha}\n")



def get_roots(root_dir: Path):
    ignore_directories = [".git", ".venv", "__pycache__", ".idea", "dist", "jit.egg-info"]
    paths = []
    for root, dirs, files in root_dir.walk(top_down=False):
        if ".git" not in str(root):
           paths.append(root)
    return paths


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


def store_tree(file_entries, dir_entries, git_repo):
    tree_sha = git_repo.store_tree(file_entries, dir_entries)
    return tree_sha


def store_files(git_repo, workspace_files: List[Path]):
    entries = []
    mode = REGULAR_MODE
    for file in workspace_files:
        sha_hash = git_repo.store_file(file)
        if os.access(file, os.X_OK):
            mode = EXECUTALE_MODE
        entries.append(FileEntry(file.name, mode=mode, sha=sha_hash))
    return entries



