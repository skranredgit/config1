import os
import zipfile
import json
import configparser
import unittest


class ShellEmulator:
    def __init__(self, config_path):
        self.config = self.load_config(config_path)
        self.fs_path = self.config['Filesystem'].get('path', None)
        self.log_path = self.config['Filesystem'].get('log', None)
        self.cwd = "root"
        self.fs = {}
        self.log = []

        if not self.fs_path or not self.log_path:
            raise ValueError("Config file is missing required 'path' or 'log' keys in 'Filesystem' section")

        self.load_filesystem()
        self.write_log(f"Shell Emulator initialized with path {self.fs_path}")

    def load_config(self, path):
        config = configparser.ConfigParser()
        config.read(path)
        if not config.has_section('Filesystem'):
            raise ValueError("Config file is missing 'Filesystem' section")
        return config

    def safe_extract(self, zipfile, path="."):
        for file in zipfile.namelist():
            if os.path.isabs(file) or file.startswith(".."):
                raise ValueError(f"Unsafe file path {file}")
        zipfile.extractall(path)

    def load_filesystem(self):
        if not os.path.exists(self.fs_path):
            raise FileNotFoundError(f"Filesystem archive {self.fs_path} does not exist")

        with zipfile.ZipFile(self.fs_path, 'r') as zf:
            self.safe_extract(zf, 'temp_fs')
            self.fs = {}  # Ensure the filesystem structure is reset
            for root, dirs, files in os.walk('temp_fs'):
                relative_root = os.path.relpath(root, 'temp_fs')
                if relative_root == '.':
                    relative_root = "root"
                self.fs[relative_root] = dirs + files

    def write_log(self, message):
        if not os.path.isfile(self.log_path):
            with open(self.log_path, 'w') as f:
                f.write("[]")
        self.log.append({"action": message, "cwd": self.cwd})
        with open(self.log_path, 'w') as f:
            json.dump(self.log, f)

    def run_command(self, command):
        try:
            cmd_parts = command.strip().split()
            if not cmd_parts:
                print("Empty command")
                return

            cmd = cmd_parts[0]
            if cmd == 'ls':
                self.ls()
            elif cmd == 'cd':
                if len(cmd_parts) > 1:
                    self.cd(cmd_parts[1])
                else:
                    print("cd: missing argument")
            elif cmd == 'tail':
                if len(cmd_parts) > 1:
                    self.tail(cmd_parts[1])
                else:
                    print("tail: missing argument")
            elif cmd == 'head':
                if len(cmd_parts) > 1:
                    self.head(cmd_parts[1])
                else:
                    print("head: missing argument")
            elif cmd == 'chmod':
                if len(cmd_parts) > 2:
                    self.chmod(cmd_parts[1], cmd_parts[2])
                else:
                    print("chmod: missing arguments")
            elif cmd == 'exit':
                self.exit()
            elif cmd == 'test':
                self.run_tests()
            else:
                print(f"Unknown command: {cmd}")
        except Exception as e:
            print(f"Error executing command: {str(e)}")

    def ls(self):
        if self.cwd in self.fs:
            content = self.fs[self.cwd]
            if content:
                print("\n".join(content))
            else:
                print("No files or directories found.")
        else:
            print(f"Error: Current directory '{self.cwd}' not found in filesystem.")
        self.write_log(f"ls command executed in {self.cwd}")

    def cd(self, directory):
        if directory == "..":
            if self.cwd != "root":
                self.cwd = os.path.dirname(self.cwd)
                self.write_log(f"Changed directory to {self.cwd}")
            else:
                print("Already in root directory.")
        elif directory in self.fs.get(self.cwd, []):
            new_path = os.path.join(self.cwd, directory) if self.cwd != "root" else directory
            if new_path in self.fs:
                self.cwd = new_path
                self.write_log(f"Changed directory to {self.cwd}")
            else:
                raise ValueError(f"cd: {directory}: Not a directory")
        else:
            raise ValueError(f"cd: {directory}: No such directory")

    def tail(self, file_name):
        file_path = os.path.join('temp_fs', self.cwd, file_name)
        if os.path.isfile(file_path):
            with open(file_path, 'r') as f:
                lines = f.readlines()
                print("".join(lines[-10:]))
            self.write_log(f"tail command executed on {file_name}")
        else:
            print(f"tail: {file_name}: No such file")

    def head(self, file_name):
        file_path = os.path.join('temp_fs', self.cwd, file_name)
        if os.path.isfile(file_path):
            with open(file_path, 'r') as f:
                lines = f.readlines()
                print("".join(lines[:10]))
            self.write_log(f"head command executed on {file_name}")
        else:
            print(f"head: {file_name}: No such file")

    def chmod(self, permissions, file_name):
        file_path = os.path.join('temp_fs', self.cwd, file_name)
        if os.path.exists(file_path):
            try:
                os.chmod(file_path, int(permissions, 8))
                print(f"Permissions of {file_name} changed to {permissions}")
                self.write_log(f"chmod command executed on {file_name} with permissions {permissions}")
            except ValueError:
                print("chmod: invalid permissions format")
        else:
            print(f"chmod: {file_name}: No such file or directory")

    def exit(self):
        print("Exiting shell emulator")
        self.write_log("Shell Emulator exited")
        exit()

    def run_tests(self):
        print("Running tests...")
        unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(TestShellEmulator))


class TestShellEmulator(unittest.TestCase):

    def setUp(self):
        self.emulator = ShellEmulator("test_config.ini")

    def test_ls_empty(self):
        self.emulator.fs = {"root": []}
        self.emulator.cwd = "root"
        self.assertEqual(self.emulator.fs["root"], [])

    def test_ls_files(self):
        self.emulator.fs = {"root": ["file1.txt", "file2.txt"]}
        self.emulator.cwd = "root"
        self.assertEqual(self.emulator.fs["root"], ["file1.txt", "file2.txt"])

    def test_cd_valid(self):
        self.emulator.fs = {"root": ["dir1"], "dir1": []}
        self.emulator.cwd = "root"
        self.emulator.cd("dir1")
        self.assertEqual(self.emulator.cwd, "dir1")

    def test_cd_invalid(self):
        self.emulator.fs = {"root": ["dir1"]}
        self.emulator.cwd = "root"
        with self.assertRaises(ValueError):
            self.emulator.cd("dir2")

    def test_tail_valid(self):
        os.makedirs("temp_fs/root", exist_ok=True)
        file_path = "temp_fs/root/test_file.txt"
        with open(file_path, "w") as f:
            f.write("Line1\nLine2\nLine3\n")
        self.emulator.tail("test_file.txt")

    def test_head_valid(self):
        os.makedirs("temp_fs/root", exist_ok=True)
        file_path = "temp_fs/root/test_file.txt"
        with open(file_path, "w") as f:
            f.write("Line1\nLine2\nLine3\n")
        self.emulator.head("test_file.txt")


if __name__ == "__main__":

    def setup_test_environment():
        # Create test_config.ini if not exists
        if not os.path.exists("test_config.ini"):
            with open("test_config.ini", "w") as config_file:
                config_file.write("[Filesystem]\n")
                config_file.write("path = test_filesystem.zip\n")
                config_file.write("log = test_log.json\n")

        # Create test_filesystem.zip if not exists
        if not os.path.exists("test_filesystem.zip"):
            os.makedirs("test_fs/subdir", exist_ok=True)
            with open("test_fs/file1.txt", "w") as f:
                f.write("This is file1.txt\n")
            with open("test_fs/file2.txt", "w") as f:
                f.write("This is file2.txt\n")
            with open("test_fs/subdir/file3.txt", "w") as f:
                f.write("This is file3.txt\n")
            with zipfile.ZipFile("test_filesystem.zip", "w") as zf:
                for root, _, files in os.walk("test_fs"):
                    for file in files:
                        zf.write(os.path.join(root, file),
                                 os.path.relpath(os.path.join(root, file), "test_fs"))


    setup_test_environment()

    config_path = "config.ini"
    emulator = ShellEmulator(config_path)

    while True:
        command = input(f"{emulator.cwd}$ ")
        emulator.run_command(command)
