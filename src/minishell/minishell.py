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

import sys
import subprocess
import shlex
from typing import final, overload


__all__ = ["Shell", "shell", "ArgsNamespace", "Color"]


@final
class Shell:
    def __init__(self):
        self.args = _parse_args()
        self.color = Color()


    def __call__(self, cmd: str, *args: str, **kwargs: str):
        """
        Execute command with optional argument escaping and TTY support.

        If additional arguments provided, they are escaped and formatted into cmd.
        If no args, cmd is executed as-is (raw).

        Usage:
            shell("ls -la | grep test")  # raw
            shell("echo {}", "hello")    # with escaping
            shell("git commit -m {message}", message="Fix #123")
        """
        cmd = self.prepare(cmd, *args, **kwargs)
        _run_raw(cmd)

    def read(
        self,
        cmd: str,
        *args: str,
        exit_on_error: bool = False,
        **kwargs: str,
    ) -> tuple[str, int]:
        """
        Read output from command with optional argument escaping.

        Usage:
            shell.read("ls -la")
            shell.read("find {} -name {format}", "/path", format="*.py")
        """
        cmd = self.prepare(cmd, *args, **kwargs)
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
        return self.read(cmd, *args, exit_on_error=True)[0]

    def prepare(self, cmd: str, *args: str, **kwargs: str):
        escaped_args = [shlex.quote(str(arg)) for arg in args]
        escaped_kwargs = {k: shlex.quote(v) for k, v in kwargs.items()}
        return cmd.format(*escaped_args, **escaped_kwargs)

    def print(
        self,
        *text: str,
        sep: str = " ",
        end: str | None = "\n",
        color: str | None = None,
        hex: str | None = None,
    ):
        print(self.color(sep.join(text), color=color, hex=hex), end=end)


    def exit(
        self,
        *text: str,
        code: int = 1,
        sep: str = " ",
        end: str | None = "\n",
        color: str | None = None,
        hex: str | None = None,
    ):
        if text:
            string = self.color(sep.join(text), color=color, hex=hex)
            print(string, end=end)
        sys.exit(code)


@final
class Color:
    reset = "\033[0m"
    red = "\033[31m"
    green = "\033[32m"
    yellow = "\033[33m"
    blue = "\033[34m"
    magenta = "\033[35m"
    cyan = "\033[36m"

    def __call__(
        self,
        text: str,
        *,
        color: str | None = None,
        hex: str | None = None,
    ) -> str:
        if not sys.stdout.isatty():
            return text
        if color is not None:
            return f"{color}{text}{self.reset}"
        if hex is not None:
            hex = hex.lstrip("#")
            r, g, b = int(hex[0:2], 16), int(hex[2:4], 16), int(hex[4:6], 16)
            return f"\033[38;2;{r};{g};{b}m{text}{self.reset}"
        return text

@final
class ArgsNamespace:
    def __init__(self, positional: list[str], named: dict[str, str | list[str]]):
        self._positional = positional
        self._named = named

    @overload
    def __getitem__(self, key: int) -> str | None: ...

    @overload
    def __getitem__(self, key: str) -> str | list[str] | None: ...

    @overload
    def __getitem__(self, key: tuple[str, ...]) -> str | list[str] | None:
        """
        This overload merges keys you provided into a single list or string.
        Useful to combine shorthand and full property names.

        Example:
            program -I test --interface prod

            If `values = shell.args["I", "interface"]` is used, you get both values.
        """

    def __getitem__(self, key: str | int | tuple[str, ...]) -> str | list[str] | None:
        if isinstance(key, int):
            return self._positional[key] if 0 <= key < len(self._positional) else None
        # The Merger (read the doc for this overload)
        if isinstance(key, tuple):
            result: str | list[str] | None = None
            def append(value: str):
                nonlocal result
                if result is None:
                    result = value
                else:
                    if isinstance(result, str):
                        result = [result]
                    result.append(value)
            for item in key:
                values = self._named.get(item)
                if isinstance(values, str):
                    append(values)
                elif isinstance(values, list):
                    for value in values:
                        append(value)
            return result
        return self._named.get(key)

    def __getattr__(self, key: str) -> str | list[str] | None:
        if key.startswith("_"):
            return super().__getattribute__(key)
        return self._named.get(key)


def _parse_args():
    """
    Parse command-line arguments.

    Supports:
    - Positional: args[0], args[1], ...
    - Long options: --name, --name value
    - Short options: -x, -x value, -xyz
    - Repeated options become lists
    - Dashes in names converted to underscores
    - Use -- to stop parsing named parameters
    """
    positional: list[str] = []
    named: dict[str, str | list[str]] = {}

    argv = sys.argv
    i = 0
    stop_named = False

    def named_append(key: str, value: str):
        if key not in named:
            named[key] = value
        else:
            cached = named[key]
            if isinstance(cached, str):
                cached = [cached]
            cached.append(value)
            named[key] = cached

    while i < len(argv):
        arg = argv[i]

        if stop_named:
            positional.append(arg)
            i += 1
            continue

        if arg == "--":
            stop_named = True
            i += 1
            continue

        if arg.startswith("--") and not stop_named:
            key = arg[2:]
            key = key.replace("-", "_")

            if i + 1 < len(argv) and not argv[i + 1].startswith("-"):
                value = argv[i + 1]
                i += 1
            else:
                value = "True"

            named_append(key, value)

        # Short option(s): -x or combined -xyz
        elif arg.startswith("-") and arg != "-" and not stop_named:
            flags = arg[1:]

            for key in flags[:-1]:
                named_append(key, "True")

            last = flags[-1]

            # Idk how to better interpret this. On one hand there's sed that
            # allows us to do 'sed -Ep program', on the other hand you may not
            # expect that the last flag consumes things. So as of now the only
            # way to pass value to shorthand flag is to separate it from other
            # flags
            if len(flags) == 1 and i + 1 < len(argv) and not argv[i + 1].startswith("-"):
                value = argv[i + 1]
                i += 1
            else:
                value = "True"

            named_append(last, value)
        else:
            positional.append(arg)

        i += 1

    return ArgsNamespace(positional, named)


def _run_raw(cmd: str):
    cmd = cmd.strip()
    try:
        result = subprocess.run(cmd, shell=True)
    except KeyboardInterrupt:
        sys.exit(0)

    if result.returncode != 0:
        sys.exit(result.returncode)

def _read_raw(cmd: str, exit_on_error: bool):
    cmd = cmd.strip()
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
    )
    if exit_on_error and result.returncode != 0:
        sys.exit(result.returncode)
    return result.stdout.strip() or "", result.returncode


shell = Shell()
