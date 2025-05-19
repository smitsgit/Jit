import os
import time
from contextlib import suppress
from pathlib import Path
from hashlib import sha1
from typing import List
from zlib import compress
from datetime import datetime, timezone


class Blob:
    def __init__(self, data):
        self.data = data

    def type_(self):
        return "blob"

    def get_binary_content(self):
        content = f"{self.type_()} {len(self.data)}\0{self.data}".encode("utf-8")
        return content

    def __repr__(self):
        return f"Blob({self.data})"


class TreeEntry:
    def __init__(self, name, mode="10644", sha=""):
        self.name = name
        self.mode = mode
        self.sha = sha

    def __repr__(self):
        return f"TreeEntry({self.name}, {self.mode}, {self.sha})"


class Tree:
    def __init__(self, entries: List[TreeEntry]):
        self.entries = entries

    def type_(self):
        return "tree"

    def get_binary_content(self):
        content = b""
        for entry in self.entries:
            content += content.join(
                [
                    entry.mode.encode("utf-8") + " ".encode("utf-8") + entry.name.encode("utf-8")
                    + "\0".encode("utf-8") + bytes.fromhex(entry.sha)
                ]
            )
        tree_content = f"{self.type_()} {len(content)}\0".encode("utf-8") + content
        return tree_content


class Author:
    def __init__(self, name, email, time=datetime.now(tz=timezone.utc)):
        self.name = name
        self.email = email
        self.time = time

    def get_binary_content(self):
        content = f"{self.name} <{self.email}> {self.time.strftime("%s %z")}".encode("utf-8")
        return content


class Commit:
    def __init__(self, tree_sha, author: Author, committer=None, message=None, parent_sha=None):
        self.tree_sha = tree_sha
        self.parent_sha = parent_sha
        self.author = author
        self.committer = committer
        self.message = message

    def type_(self):
        return "commit"

    def get_binary_content(self):
        content = b""
        content += f"tree {self.tree_sha}\n".encode("utf-8")
        if self.parent_sha:
            content += f"parent {self.parent_sha}\n".encode("utf-8")
        content += self.author.get_binary_content() + "\n".encode("utf-8")
        content += "\n".encode("utf-8")
        content += self.message.encode("utf-8")
        content += "\n".encode("utf-8")
        commit_content = f"{self.type_()} {len(content)}\0".encode("utf-8") + content
        return commit_content


class GitRepo:
    root_dir = None
    git_dir = None
    obj_dir = None
    refs_dir = None

    @classmethod
    def make(cls, root_dir):
        cls.root_dir = Path(root_dir)
        cls.git_dir = cls.root_dir / ".git"
        cls.obj_dir = cls.git_dir / "objects"
        cls.refs_dir = cls.git_dir / "refs"
        head_path = cls.git_dir / "HEAD"

        print("Creating internal git working directories")

        # Create the directories if they don't exist
        with suppress(FileExistsError, FileNotFoundError) as e:
            cls.git_dir.mkdir(parents=False, exist_ok=False)
            cls.obj_dir.mkdir(parents=False, exist_ok=False)
            cls.refs_dir.mkdir(parents=False, exist_ok=False)

            head_path.touch(exist_ok=False)

        return GitRepo()

    def list_files(self):
        ignore_directories = [".git", ".venv", "__pycache__", ".idea", "dist", "jit.egg-info"]
        """List all files in the given directory."""
        files = []
        for item in self.root_dir.iterdir():
            if item.is_file():
                print(item.name)
                files.append(item)
            elif item.is_dir() and item.name not in ignore_directories:
                self.list_files(item)
        return files

    def store_file(self, file):
        """Store a file in the git repository."""
        # Here you would implement the logic to store the file in the git repository
        # For example, you could copy the file to the .git/objects directory
        # and create a corresponding entry in the .git/refs directory.
        data = file.read_text()
        blob = Blob(data)
        content = blob.get_binary_content()
        return self.write_compressed_content(content)

    def store_tree(self, entries: List[TreeEntry]):
        """Store a tree in the git repository."""
        tree = Tree(entries)
        tree_content = tree.get_binary_content()
        return self.write_compressed_content(tree_content)

    def store_commit(self, tree_sha, message, parent_sha=None):
        """Store a commit in the git repository."""
        author_name = os.getenv("GIT_AUTHOR_NAME")
        author_email = os.getenv("GIT_AUTHOR_EMAIL")
        author = Author(name=author_name, email=author_email)
        commit = Commit(tree_sha=tree_sha, author=author, message=message, parent_sha=parent_sha)
        commit_content = commit.get_binary_content()
        return self.write_compressed_content(commit_content)

    def write_compressed_content(self, content: bytes):
        sha_hash = sha1(content).hexdigest()
        object_path = self.obj_dir / sha_hash[0:2] / sha_hash[2:]
        if object_path.exists():
            print(f"Object {sha_hash} already exists.")
            return sha_hash
        object_path.parent.mkdir(parents=True, exist_ok=False)
        object_path.write_bytes(compress(content))
        return sha_hash
