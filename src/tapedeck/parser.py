def parse(code):
    args = code.split()
    command = None
    if args:
        command = args[0]
    result = ((command, *args[1:]),)
    return result
