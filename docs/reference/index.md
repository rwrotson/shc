# API Reference

The pages below are generated from public objects in `src/shc/`.

| Module | Purpose |
|--------|---------|
| `shc.main` | Initialize logging and run the CLI |
| `shc.cli.app` | Register command groups and global options |
| `shc.cli.callbacks.meta` | Handle eager metadata options |
| `shc.cli.commands.config` | Manage the shortcuts configuration |
| `shc.cli.commands.completion` | Install or print shell completion |
| `shc.cli.context` | Share settings, console, output format, and dry-run flag with commands |
| `shc.cli.shortcuts.group` | Add a command for every configured shortcut |
| `shc.cli.shortcuts.builder` | Build Typer commands from shortcut declarations |
| `shc.cli.shortcuts.types` | Translate type strings into Typer types |
| `shc.cli.shortcuts.loading` | Open the shortcuts store and plugin registry |
| `shc.cli.errors` | Report service errors and set exit codes |
| `shc.services.errors` | Define expected use-case failures |
| `shc.services.shortcuts.models` | Declare shortcuts and their parameters |
| `shc.services.shortcuts.parsing` | Validate the shortcuts configuration |
| `shc.services.shortcuts.render` | Substitute values into command templates |
| `shc.services.shortcuts.run` | Check requirements and run shortcut commands |
| `shc.services.shortcuts.store` | Define the shortcuts storage interface |
| `shc.services.shortcuts.manage` | List, show, add, remove, and validate shortcuts |
| `shc.services.plugins.markers` | Mark plugin functions with decorators |
| `shc.services.plugins.registry` | Load plugins and resolve them by name |
| `shc.services.plugins.builtin_plugins` | Provide built-in default factories and completions |
| `shc.plugin` | Public decorators for plugin files |
| `shc.config.settings` | Define and load application settings |
| `shc.utils.console` | Configure and share the Rich console |
| `shc.utils.log` | Configure console and file logging |
| `shc.utils.meta` | Read installed distribution metadata |
| `shc.utils.output` | Render text or JSON command output |
| `shc.utils.stdin` | Read piped stdin |
| `shc.utils.format` | Define the Rich theme |
| `shc.utils.emoji` | Define console emoji |
| `shc.utils.progress` | Create Rich progress bars |
| `shc.utils.misc` | Locate the project root |
| `shc.utils.shortcut_store` | Read and write the shortcuts YAML file |
