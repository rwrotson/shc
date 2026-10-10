# Shortcuts

A shortcut is a named shell command template. `shc` reads shortcuts from a YAML file and adds one command per shortcut, so `shc gco main` runs `git checkout main`.

## The shortcuts file

`shc config path` prints the file and plugin directory locations. By default both are in the platform user config directory (`~/Library/Application Support/shc/` on macOS, `~/.config/shc/` on Linux). Override them with `SHC_SHORTCUTS__FILE` and `SHC_SHORTCUTS__PLUGINS_DIR`; see [Configuration](configuration.md).

A missing or empty file means no shortcuts. `shc config add` and `shc config remove` keep comments, key order, and quoting.

```yaml
shortcuts:
  gco:
    command: "git checkout {force} {create} {branch}"
    help: Check out a branch.
    requirements: [git]
    arguments:
      - name: branch
        autocompletion: git_branches   # defined in a plugin
    options:
      - name: force
        type: bool
        flag: -f
      - name: create
        type: bool
        flag: -b
        help: Create the branch first.
```

### Shortcut keys

| Key | Required | Meaning |
|-----|----------|---------|
| `command` | yes | Shell command template with `{name}` placeholders |
| `help` | no | Help text shown by `shc <name> --help` |
| `short_help` | no | Text shown in the `shc --help` command list; derived from `help` if unset |
| `epilog` | no | Text shown after the help |
| `requirements` | no | Executables that must be on `PATH`; checked before running |
| `arguments` | no | Positional parameters, in order |
| `options` | no | `--option` parameters |

Shortcut names use letters, digits, `-`, and `_`, and start with a letter or digit. `config` and `completion` are reserved.

### Parameter keys

Arguments and options share these keys:

| Key | Meaning |
|-----|---------|
| `name` | Python identifier used in placeholders; options are called as `--kebab-case` |
| `help` | Help text |
| `type` | Value type; `str` if unset (see [Types](#types)) |
| `default` | Default value |
| `default_factory` | Name of a plugin function that returns the default; exclusive with `default` |
| `choices` | Allowed values; requires type `str` or `list[str]` |
| `autocompletion` | Name of a plugin function that completes the value |
| `parser` | Name of a plugin function that converts the raw string |
| `flag` | Options only: how the option is written into the command (see [Rendering](#rendering)) |

These keys are passed to Typer unchanged: `show_default`, `show_choices`, `show_envvar`, `hidden`, `envvar`, `case_sensitive`, `min`, `max`, `clamp`, `formats`, `mode`, `encoding`, `errors`, `lazy`, `atomic`, `exists`, `file_okay`, `dir_okay`, `writable`, `readable`, `resolve_path`, `allow_dash`, and `path_type` (`str` or `bytes`). See [Typer's parameter types](https://typer.tiangolo.com/tutorial/parameter-types/).

An argument without a default is required, and a required argument cannot follow an optional one. An option without a default is empty; a `bool` option is off.

## Rendering

`{name}` is replaced with the parameter's value quoted for the shell, so `my file.txt` stays one word. `{name!r}` inserts the value without quoting, for globs and variables. `{{` and `}}` are literal braces.

| Value | Without `flag` | With `flag: --sort` |
|-------|----------------|---------------------|
| `"a b"` | `'a b'` | `--sort 'a b'` |
| `["a", "b"]` | `a b` | `--sort a --sort b` |
| `true` | `--option-name` | `--sort` |
| `false` or empty | nothing | nothing |

Dates and times are written in ISO 8601 format. `flag` only changes the rendered command; the option keeps its `--kebab-case` name in `shc`. For example, the `force` option above is called as `shc gco main --force` and runs `git checkout -f main`.

`shc --dry-run <name> ...` prints the rendered command instead of running it. Otherwise `shc` runs the command in the shell and exits with its exit code.

## Types

| Type | Notes |
|------|-------|
| `str`, `int`, `float`, `bool` | |
| `Path` | Combine with `exists`, `file_okay`, `dir_okay`, and the other path keys |
| `datetime` | Use `formats` to set accepted formats |
| `UUID` | |
| `FileText`, `FileBinaryRead` | Typer opens the file; the template receives its name |
| `list[T]` | Repeat the option: `--tag a --tag b` |
| `tuple[T1, T2]` | One option with several values: `--pair key 3` |
| `Optional[T]`, `T \| None` | |

`T` is one of the plain types. Type names are looked up in this list, never evaluated.

## Plugins

Plugins are `*.py` files in the plugin directory. Decorated functions are registered under a name that the shortcuts file refers to:

```python
import subprocess

from shc import plugin


@plugin.autocompletion("git_branches")
def git_branches(incomplete: str) -> list[str]:
    result = subprocess.run(
        ["git", "branch", "--format=%(refname:short)"], capture_output=True, text=True
    )
    return [name for name in result.stdout.split() if name.startswith(incomplete)]


@plugin.default_factory("current_branch")
def current_branch() -> str:
    result = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True)
    return result.stdout.strip()


@plugin.parser("upper")
def upper(value: str) -> str:
    return value.upper()
```

| Decorator | Called with | Returns |
|-----------|-------------|---------|
| `autocompletion` | The text typed so far | Completions, or `(value, help)` pairs |
| `default_factory` | Nothing | The default value |
| `parser` | The raw string | The converted value |

Names are unique within each kind. Built-in plugins:

- `default_factory`: `list`, `tuple`, `now`, `today`, `cwd`, `home`
- `autocompletion`: `path`

Plugins run as Python code in the `shc` process; load only files you trust.

## Managing shortcuts

| Command | Action |
|---------|--------|
| `shc config list` | List shortcuts |
| `shc config show NAME` | Print one shortcut's YAML |
| `shc config add NAME COMMAND [-d TEXT] [-r EXE]... [--force]` | Add a shortcut; each placeholder becomes a string argument |
| `shc config remove NAME` | Remove a shortcut |
| `shc config edit` | Open the file in `$VISUAL` or `$EDITOR` (`vi` by default), then validate it |
| `shc config validate` | Check the file, its plugins, and every shortcut's parameters; report unused parameters |
| `shc config path` | Print the file and plugin directory paths |

All of them accept the global `--output-format json`.

A shortcut that fails to load is left out of `shc --help` with a warning in the log; running it prints the error. Built-in commands keep working when the file is invalid, so `shc config edit` can fix it.

## Shell completion

```bash
shc completion install
```

Completion covers shortcut names and values from `autocompletion` plugins.

## Exit codes

| Code | Meaning |
|------|---------|
| The command's exit code | The shortcut ran |
| 1 | Shortcut not found or already exists; file cannot be read or written |
| 2 | Invalid shortcuts file, plugin error, or invalid command-line usage |
| 127 | An executable in `requirements` is not on `PATH` |
