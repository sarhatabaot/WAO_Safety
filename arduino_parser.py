from typing import List


class ArduinoParser:
    @staticmethod
    def _parse_single(value: str, format_specifier: str):
        try:
            if format_specifier == "i":
                return int(value)
            elif format_specifier == "f":
                return float(value)
            elif format_specifier == "s":
                return value
            else:
                return None
        except ValueError:
            return None

    @staticmethod
    def parse(format_str: str, response: str):
        # TODO: dangerous code. can enter infinite loop
        """
        Tries to extract values from a string created using formatting.
        Limitations: Must be only one way to parse to string
        :param format_str: format string with only. For example 'Int Value {i} Float Value {f}'.
        :param response: text to parse
        :return: values extracted from the response.
        """
        delimiters: List[str] = []
        format_specifiers: List[str] = []

        last_i = 0

        while last_i < len(format_str) and (
                format_str.find("{", last_i) != -1 or format_str.find("}", last_i) != -1):

            format_start = format_str.find("{", last_i)
            format_end = format_str.find("}", last_i)

            start_escaped = False
            end_escaped = False

            if format_end != len(format_str) - 1:
                end_escaped = format_str[format_end + 1] == "}"

            if format_start != len(format_str) - 1:
                start_escaped = format_str[format_start + 1] == "{"

            # both escaped
            if start_escaped and end_escaped:
                last_i = max(format_start + 2, format_end + 2)
            # both not escaped
            elif not start_escaped and not end_escaped:
                if format_end < format_start:
                    return None

                format_specifier = format_str[format_start + 1: format_end]
                format_specifiers.append(format_specifier)

                before = format_str[last_i: format_start]
                delimiters.append(before)

                last_i = format_end + 1
            # one of them escaped. Error
            else:
                return None

        if last_i <= len(format_str):
            delimiters.append(format_str[last_i:])

        if len(format_specifiers) == 0:
            return tuple([])

        results = []

        remaining_response = response

        for i in range(len(format_specifiers)):
            before = delimiters[i]
            after = delimiters[i + 1]

            before_index = remaining_response.find(before)
            if after != "":
                after_index = remaining_response.find(after, before_index + len(before))

                if before_index != 0 or after_index == -1:
                    return None

                str_to_parse = remaining_response[before_index + len(before): after_index]
                remaining_response = remaining_response[after_index:]
            else:
                str_to_parse = remaining_response[before_index + len(before):]
                remaining_response = ""

            value = ArduinoParser._parse_single(str_to_parse, format_specifiers[i])

            if value is None:
                return None

            results.append(value)

        return tuple(results)
