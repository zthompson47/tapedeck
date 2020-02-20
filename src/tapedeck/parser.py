def parse(code):
    args = code.split()
    command = None
    if args:
        command = args[0]
    return ((command, *args[1:]),)
