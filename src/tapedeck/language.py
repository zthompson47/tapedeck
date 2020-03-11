import re

keywords = [
    "play", "fetch", "latest", 
    "and", "then",
]

single_char = {
    '=': 'ASSIGN',
    ';': 'SEMI',
    '(': 'LPAREN',
    ')': 'RPAREN',
    ',': 'COMMA',
    '`': 'DEREF',
    '+': 'PLUS',
    '-': 'MINUS',
    '*': 'TIMES',
    '/': 'DIVIDE',
    '<': 'LT',
    '>': 'GT',
    '!': 'LNOT',
    '^': 'GROW',
}

double_char = {
    "<<": "L",
    ">>": "R",
    '<=': 'LE',
    '>=': 'GE',
    '==': 'EQ',
    '!=': 'NE',
    '&&': 'ANDI',
    '||': 'ORI',
}

regexp = {
    "namespace": re.compile(r"(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)\."),
    "command": re.compile(r"[a-zA-Z_][a-zA-z0-9_]*"),
    "string": re.compile(r"\".*?\""),
    "name": re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*"),
    "int": re.compile(r"[0-9]+"),
    "float": re.compile(r"""
        [0-9]+\.[0-9]*  # digit on left
        | [0-9]*\.[0-9]+  # digit on right
    """, re.VERBOSE),
}


class Token:
    def __init__(self, type, value, lineno):
        self.type = type
        self.value = value
        self.lineno = lineno

    def __repr__(self):
        return f"Token({self.type}, {self.value}, {self.lineno})"

    def lnum(self, obj):
        obj.lineno = self.lineno
        return obj


def tokenize(code):
    if not code.endswith("\n"):
        code += "\n"
    index = 0
    lineno = 1
    while index < len(code):

        # Whitespace
        if code[index] in " \t\r":
            index += 1

        # Newline
        elif code[index] == "\n":
            lineno += 1
            index += 1

        # Single-line comment
        elif code[index] == "#":
            end = code.find("\n", index + 1)
            index = end

        # Multi-line comment
        elif code[index:index + 2] == "/*":
            end = code.find("*/", index + 2)
            if end >= 0:
                lineno += code[index + 2:end].count("\n")
                index = end + 2
            else:
                print("unterminated comment")
                index = len(code)

        # Double character symbols
        elif code[index:index + 2] in double_char:
            chars = code[index:index + 2]
            yield Token(double_char[chars], chars, lineno)
            index += 2

        # Single character symbols
        elif code[index] in single_char:
            char = code[index]
            yield Token(single_char[char], char, lineno)
            index += 1

        # Strings
        elif regexp["string"].match(code[index:]):
            m = regexp["string"].match(code[index:])
            value = m.group(0)
            yield Token('STRING', value, lineno)
            index += len(m.group(0))

        # Floats
        elif regexp["float"].match(code[index:]):
            m = regexp["float"].match(code[index:])
            value = m.group(0)
            yield Token('FLOAT', value, lineno)
            index += len(m.group(0))

        # Integers
        elif regexp["int"].match(code[index:]):
            m = regexp["int"].match(code[index:])
            value = m.group(0)
            yield Token('INTEGER', value, lineno)
            index += len(m.group(0))

        # Commands
        elif regexp["namespace"].match(code[index:]):
            m = regexp["namespace"].match(code[index:])
            value = m.group("name")
            yield Token("NAMESPACE", value, lineno)
            index += len(m.group(0))
            if regexp["command"].match(code[index:]):
                m = regexp["command"].match(code[index:])
                value = m.group(0)
                yield Token("COMMAND", value, lineno)
                index += len(m.group(0))

        elif regexp["name"].match(code[index:]):
            m = regexp["name"].match(code[index:])
            value = m.group(0)
            yield Token('NAME', value, lineno)
            index += len(m.group(0))

        # No match
        else:
            print(lineno, f"Illegal character {repr(code[index])}")
            index += 1


def parse(code):
    args = code.split()
    command = None
    if args:
        command = args[0]
    result = ((command, *args[1:]),)
    return result
