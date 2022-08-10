class BaseCommand(object):
    def get_name(self):
        raise NotImplementedError("Please specifiy a command name.")

    def get_help(self):
        raise NotImplementedError("Please specifiy a help text.")

    def uses_config(self):
        return False

    def setup_arguments(self, parser):
        pass

    def main(self, args):
        raise NotImplementedError("Please implement main() for the command.")
