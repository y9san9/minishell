# minishell

> An idiot admires complexity, a genius admires simplicity
>
> ©️ _Legend Terry A. Davis_

I want to ditch Bash and replace all use cases of it with Python. I recently learned that there's no good alternative for Bash. You can argue that there is, but then compare what they can write in Bash and how unreadable it becomes with any of the traditional shell solutions out there.

## Goals

- `minishell` is going to be extremely simple
- Compete with Bash only
- Do not add features just because other libraries have them
- Stay focused: execute commands and parse arguments, nothing more

## Philosophy

Bash works because it's **the** shell. You can't replicate that. But you can make Python script writing as painless as Bash for everything else: better error handling, better argument parsing, better readability.

`minishell` provides just what you need:

- `shell(cmd, *args)` - Run commands with full TTY support and optional argument escaping
- `shell[cmd, *args]` - Same as previous, but capture output
- `shell.args[1], shell.args.named_argument` - Parse CLI arguments automatically

That's it. No frameworks, no magic.

## Quick Start

```python
# Raw command
shell("ls -la | grep test")

# With escaped arguments (safe!)
filename = "file with spaces.txt"
shell("rm {}", filename)

# Capture output
output = shell["pwd"]
print("Current dir:", output)

# Arguments are auto-parsed
app_name = shell.args.app_name
if not app_name:
    shell.exit("Error: --app-name required")
```

## API

### `shell(cmd, *args)`

Execute a command with optional argument escaping.

- **cmd**: Command string with optional `{}` placeholders
- **args**: Arguments to format and escape

```python
shell("echo hello")           # raw
shell("echo {}", "hello")     # with escaping
```

### `shell[cmd, *args]`

Execute command and capture output. Returns the output string.

```python
output = shell["pwd"]
# With escaped arguments
output = shell["find {} -name {}", "/path", "*.py"]
```

### `shell.read(cmd, *args, exit_on_error=False)`

Execute command and capture output with more control.

- Returns `tuple[output, exit_code]`
- Set `exit_on_error=True` to exit on non-zero code
  (usually it's better to use `shell[cmd, *args]` instead)

```python
output, code = shell.read("ls")
output, code = shell.read("find {} -name {}", "/path", "*.py", exit_on_error=True)
```

### `shell.args`

Automatically parsed command-line arguments.

```python
# Positional
print(shell.args[0])

# Named arguments
print(shell.args.config)
print(shell.args.verbose)

# Multiple values become lists
if isinstance(shell.args.file, list):
    for f in shell.args.file:
        print(f)
```

## Installation

```bash
pip install minishell
```

Or just copy `minishell.py` to your project.

## Why not Bash?

| Feature | Bash | minishell |
|---------|------|-----------|
| Argument parsing | 50+ lines | 3 lines |
| Variable syntax | `$VAR`, `${VAR}` | f-strings |
| Error handling | `set -e` (fragile) | Explicit |
| Type hints | None | Full typing |
| Readability | Medium | High |

## Contributing

We need Bash specialists to provide code examples that are:
- Cleaner/simpler in Bash than in Python with `minishell`
- Real-world use cases we should optimize for

Alternatively, suggest improvements to keep the library minimal and focused. Pure critique without suggestions is also appreciated!

The bar for adding features: _Does this save significant boilerplate compared to Bash?_
