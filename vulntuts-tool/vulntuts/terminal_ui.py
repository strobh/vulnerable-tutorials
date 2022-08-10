import dateparser


class TerminalUI:
    def _input(self, field_name, default=None):
        if default:
            return input(f"{field_name} [{default}]: ")
        else:
            return input(f"{field_name}: ")

    def _ask_for_date(self, field_name, default=None):
        # ask for date
        answer = self._input(field_name, default)

        # if a date was supplied, parse it and convert it to ISO format
        if answer:
            date = dateparser.parse(answer)
            if date:
                return date.astimezone().isoformat()

        # if no date was supplied, return the default
        return default

    def _ask_for_string(self, field_name, default=""):
        # ask for string
        answer = self._input(field_name, default)

        # return answer if not empty, or default otherwise
        if answer:
            return answer
        return default

    def _ask_for_text(self, field_name, default=""):
        print(f"{field_name} (stop with CTRL+D):")

        # initialize text
        text = []
        i = 0

        # read lines until the user stops
        while True:
            try:
                # read line
                line = input()

                # if first line is empty, break the loop
                if i == 0 and line == "":
                    break

                # append line to text
                text.append(line)
                i += 1
            # if the user pressed CTRL+D, break the loop
            except EOFError:
                break

        # create the text by joining the lines
        text = "\n".join(text).rstrip("\n")

        # return text if not empty, or default otherwise
        if text:
            return text
        return default

    def _ask_for_enum(self, field_name, enum_class, default):
        # ensure that the default is a value of the enum
        if not isinstance(default, enum_class):
            raise ValueError("Given default is not an intance of the enum")

        # convert the enum to a list of enum values
        enum_items = [enum_item.value for enum_item in enum_class]

        # calculate 1-indexed index of the default value
        default_index = enum_items.index(default.value) + 1

        # repeat until the user specified a valid value
        while True:
            # print enum values with index
            for index, enum_item in enumerate(enum_class, start=1):
                print(f"[{index}] {enum_item.value}")

            # ask for value
            answer = self._input(field_name, f"{default_index}/{default.value}")

            # if a value was supplied, check and return it
            if answer:
                try:
                    return enum_class(enum_items[int(answer) - 1])
                except ValueError:
                    print("Invalid value. Try again.")
            # if no value was supplied, return the default value
            else:
                return default

    def _ask_for_boolean(self, field_name, default=True):
        # repeat until the user specified a valid value
        while True:
            # ask for value
            default_text = "y" if default else "n"
            answer = self._input(f"{field_name} (y,n)", default_text)
            answer = answer.lower()

            # if a value was supplied, check and return it
            if answer:
                if answer == "1" or answer == "y" or answer == "yes":
                    return True
                elif answer == "0" or answer == "n" or answer == "no":
                    return False
                else:
                    print("Invalid value. Try again.")
            # if no value was supplied, return the default value
            else:
                return default

    def _ask_loop(self, name, default=False):
        return self._ask_for_boolean(f"Next {name}?", default)
