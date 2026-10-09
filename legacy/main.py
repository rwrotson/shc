from typer import Typer

app = Typer(help="Custom CLI generated from YAML")

# Register commands dynamically
for cmd_name, cmd_info in config.get("commands", {}).items():
    def make_command(cmd: str, args: list | None = None):
        """Wrapper function to create a typer command."""
        def command_function(*cmd_args):
            formatted_cmd = cmd
            if args:
                for i, arg in enumerate(args):
                    formatted_cmd = formatted_cmd.replace(f"{{{arg['name']}}}", str(cmd_args[i]))
            echo(f"Running: {formatted_cmd}")
            subprocess.run(formatted_cmd, shell=True)
        return command_function

    arguments = cmd_info.get("arguments", [])
    cmd_function = make_command(cmd_info["command"], arguments)

    for arg in reversed(arguments):  # Reverse to maintain order
        cmd_function = Argument(
            ...,
            help=arg["help"],
            show_default=False,
        )(cmd_function)

    app.command(name=cmd_name, help=cmd_info["description"])(cmd_function)


if __name__ == "__main__":
    app()