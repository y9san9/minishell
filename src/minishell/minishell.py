"""
minishell - Bash replacement library for Python

Extremely simple, minimal shell integration with TTY support and argument parsing.

Example:
    from minishell import shell

    # Raw command string
    shell("ls -la | grep test")

    # With escaped arguments
    shell("git commit -m {}", "Fix bug #123")

    # Capture output
    result = shell.read("ls -la")
    result = shell.read("find {} -name {}", "/path", "*.py")
    print(result.output)

    # Access arguments
    print(shell.args[0])        # First positional
    print(shell.args.config)    # Named argument, dict if multiple provided
"""

import os
import sys
import subprocess
import tempfile
import shlex
from typing import overload


__all__ = ["Shell", "shell", "ArgsNamespace", "TempFile"]


class Shell:
    args: ArgsNamespace

    def __init__(self):
        self.args = _parse_args()

    def __call__(self, cmd: str, *args: str, exit_on_error: bool = True) -> int:
        """
        Execute command with optional argument escaping and TTY support.

        If additional arguments provided, they are escaped and formatted into cmd.
        If no args, cmd is executed as-is (raw).

        Usage:
            shell("ls -la | grep test")  # raw
            shell("echo {}", "hello")    # with escaping
            shell("git commit -m {}", "Fix #123")
        """
        if args:
            escaped_args = [shlex.quote(str(arg)) for arg in args]
            cmd = cmd.format(*escaped_args)

        return _run_raw(cmd, exit_on_error)

    def read(
        self,
        cmd: str,
        *args: str,
        exit_on_error: bool = True,
    ) -> tuple[str, int]:
        """
        Read output from command with optional argument escaping.

        Usage:
            shell.read("ls -la")
            shell.read("find {} -name {}", "/path", "*.py")

        Returns:
            Either str if exit_on_error is True or tuple[str, int] with both
            output and code if exit_on_error is False.
        """
        if args:
            escaped_args = [shlex.quote(str(arg)) for arg in args]
            cmd = cmd.format(*escaped_args)
        return _read_raw(cmd, exit_on_error)

    def __getitem__(
        self,
        item: str | tuple[str, ...],
    ) -> str:
        """
        Syntactic sugar for read with exit_on_error always True.
        You are getting the output and that's the mental model.
        """
        if isinstance(item, tuple):
            cmd = item[0]
            args = item[1:]
        else:
            cmd = item
            args = ()
        return self.read(cmd, *args)[0]


    def exit(self, message: str = "", code: int = 1):
        if message:
            print(message)
        sys.exit(code)

    @property
    def temp(self) -> TempFile:
        return TempFile()


class ArgsNamespace:
    _positional: list[str]
    _named: dict[str, str | list[str]]

    def __init__(self, positional: list[str], named: dict[str, str | list[str]]):
        self._positional = positional
        self._named = named

    @overload
    def __getitem__(self, key: int) -> str | None: ...

    @overload
    def __getitem__(self, key: str) -> str | list[str] | None: ...

    def __getitem__(self, key: str | int) -> str | list[str] | None:
        if isinstance(key, int):
            return self._positional[key] if 0 <= key < len(self._positional) else None
        return self._named.get(key)

    def __getattr__(self, key: str) -> str | list[str] | None:
        if key.startswith("_"):
            return super().__getattribute__(key)
        return self._named.get(key)


class TempFile:
    def __enter__(self):
        self.file = tempfile.NamedTemporaryFile(
            mode='w+',
            delete=False,
            prefix='shell_py_'
        )
        self.path = self.file.name
        self.file.close()
        return self

    def __exit__(self, *_):
        try:
            os.remove(self.path)
        except:
            pass

    def read(self):
        try:
            with open(self.path, 'r') as f:
                return f.read().strip()
        except:
            return ""

    def __str__(self):
        return self.path


def _parse_args():
    """
    Parse command-line arguments.

    Supports:
    - Positional: args[0], args[1], ...
    - Long options: --name, --name=value, --name value
    - Short options: -x, -x value
    - Repeated options become lists
    - Dashes in names converted to underscores
    """
    positional: list[str] = []
    named: dict[str, str | list[str]] = {}

    argv = sys.argv
    i = 0

    while i < len(argv):
        arg = argv[i]

        # Long option: --key or --key=value
        if arg.startswith("--"):
            key = arg[2:]
            key = key.split("=")[0]
            key = key.replace("-", "_")

            if "=" in arg:
                value = arg.split("=", 1)[1]
            elif i + 1 < len(argv) and not argv[i + 1].startswith("-"):
                value = argv[i + 1]
                i += 1
            else:
                value = "True"

            # Handle multiple occurrences
            if key in named:
                cached = named[key]
                if isinstance(cached, str):
                    cached = [cached]
                cached.append(value)
                named[key] = cached
            else:
                named[key] = value

        # Short option: -x
        elif arg.startswith("-") and arg != "-":
            key = arg[1:]
            key = key.replace("-", "_")

            if i + 1 < len(argv) and not argv[i + 1].startswith("-"):
                value = argv[i + 1]
                i += 1
            else:
                value = "True"

            # Handle multiple occurrences
            if key in named:
                cached = named[key]
                if isinstance(cached, str):
                    cached = [cached]
                cached.append(value)
                named[key] = cached
            else:
                named[key] = value

        # Positional argument
        else:
            positional.append(arg)

        i += 1

    return ArgsNamespace(positional, named)


def _run_raw(cmd: str, exit_on_error: bool = True) -> int:
    cmd = cmd.strip()
    try:
        result = subprocess.run(cmd, shell=True)
    except KeyboardInterrupt:
        sys.exit(0)

    if exit_on_error and result.returncode != 0:
        sys.exit(result.returncode)

    return result.returncode

def _read_raw(cmd: str, exit_on_error: bool):
    cmd = cmd.strip()
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
        )
        if exit_on_error and result.returncode != 0:
            print(result.stdout.strip())
            print(result.stderr.strip())
            sys.exit(result.returncode)
        return result.stdout.strip() or "", result.returncode
    except KeyboardInterrupt as e:
        raise e
    except Exception:
        return "", 1


shell = Shell()
