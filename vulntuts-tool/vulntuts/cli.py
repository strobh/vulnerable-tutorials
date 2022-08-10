import argparse
import os
import shutil

import yaml

from vulntuts import storage
from vulntuts.commands.browser import BrowserCommand
from vulntuts.commands.data import DataCommand
from vulntuts.commands.experiment import ExperimentCommand
from vulntuts.commands.inspect import InspectCommand
from vulntuts.commands.queries import GenerateQueriesCommand
from vulntuts.commands.sample import SampleCommand
from vulntuts.commands.scan import ScanCommand
from vulntuts.commands.search import SearchCommand
from vulntuts.commands.suggestions import SuggestQueriesCommand
from vulntuts.errors import InvalidArgumentError, VulntutsError


def main():
    """Parse arguments and execute main method of the specified command."""
    # list of commands
    commands = [
        SuggestQueriesCommand(),
        GenerateQueriesCommand(),
        SearchCommand(),
        SampleCommand(),
        InspectCommand(),
        ExperimentCommand(),
        ScanCommand(),
        DataCommand(),
        BrowserCommand(),
    ]

    # create argument parser and parse arguments
    parser = _create_arg_parser(commands)
    args = parser.parse_args()

    # extract arguments as dictionary
    args_dict = vars(args)

    # set data directory to current working directory
    args_dict["data_dir"] = os.getcwd()

    # if the command uses the config, the command subparser has registered the config
    # parser as a parent, ensuring that the config argument is always set
    # (defaults to None if not specified in the call)
    if "config" in args_dict:
        args_dict["config"] = _process_config(args_dict.get("config"))

    try:
        # call main method of the specified command
        args.func(args_dict)
    except InvalidArgumentError as e:
        print(f"Invalid argument: {e}")
    except VulntutsError as e:
        print(f"Error: {e}")
    except KeyboardInterrupt:
        return


def _create_arg_parser(commands):
    # argparse formatter to limit width of help text to 80 characters
    def formatter(prog):
        # source: https://bugs.python.org/issue39809#msg363557
        width = min(80, shutil.get_terminal_size().columns - 2)
        return argparse.RawDescriptionHelpFormatter(prog, width=width)

    # overwrite HelpAction to extend main help with usage of sub-commands
    class _HelpAction(argparse._HelpAction):
        def __call__(self, parser, namespace, values, option_string=None):
            # function to remove a prefix text from a string
            def _remove_prefix(text, prefix):
                if text.startswith(prefix):
                    return text[len(prefix) :]
                return text

            # print help of main parser and heading for commands
            print(parser.format_help())
            print("commands usage:")

            # retrieve subparsers from parser
            subparsers_actions = [
                action
                for action in parser._actions
                if isinstance(action, argparse._SubParsersAction)
            ]
            # there will probably only be one subparser_action,
            # but better save than sorry
            for subparsers_action in subparsers_actions:
                # get all subparsers and print usage (remove `usage` prefix from string)
                for choice, subparser in subparsers_action.choices.items():
                    usage = _remove_prefix(subparser.format_usage(), "usage: ")
                    print(f"  {usage}", end="")

            parser.exit()

    # create argument parser
    parser = argparse.ArgumentParser(add_help=False, formatter_class=formatter)
    parser.add_argument(
        "-h",
        "--help",
        action=_HelpAction,
        default=argparse.SUPPRESS,
        help="Show this help message and exit",
    )

    # config argument parser
    config_parser = argparse.ArgumentParser(add_help=False)
    config_parser.add_argument(
        "-c",
        "--config",
        help=f"Specify a config file (default: {storage.CONFIG_FILE})",
        default=None,
    )

    # subparsers for commands
    command_subparsers = parser.add_subparsers(
        title="commands", dest="command", required=True, metavar="<command>"
    )

    # function to construct subparser from BaseCommand object
    def add_command(command):
        parent_parsers = []
        if command.uses_config():
            parent_parsers.append(config_parser)

        command_parser = command_subparsers.add_parser(
            command.get_name(),
            help=command.get_help(),
            parents=parent_parsers,
        )
        command_parser.set_defaults(func=command.main)
        command.setup_arguments(command_parser)

    # add commands to the argument parser
    for command in commands:
        add_command(command)

    return parser


def _process_config(config_arg):
    # function to load config from file (yaml format)
    def _load_config(config_file):
        with open(config_file, "r") as file:
            config = yaml.safe_load(file)
            if not isinstance(config, dict):
                raise InvalidArgumentError("The config file is invalid")
            return config

    # if path to config file is supplied, load it
    if config_arg:
        config_file = os.path.abspath(os.path.join(os.getcwd(), config_arg))
        if not os.path.isfile(config_file):
            raise InvalidArgumentError("The config file does not exist")
        return _load_config(config_file)
    # otherwise try default path to config file
    else:
        config_file = os.path.abspath(os.path.join(os.getcwd(), storage.CONFIG_FILE))
        if os.path.isfile(config_file):
            return _load_config(config_file)

    # default is an empty dict
    return dict()
