import re
import ast
import sys
import traceback
from functools import partial

from pygments.styles import get_style_by_name
from pygments.lexers.python import PythonLexer

from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles.pygments import style_from_pygments_cls
from prompt_toolkit import prompt, HTML, PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.application.current import get_app_session
from prompt_toolkit.history import FileHistory

import trio

PS1 = HTML("<yellow>>>></yellow> ")
PS2 = HTML("<yellow>...</yellow> ")
STYLE = style_from_pygments_cls(get_style_by_name("monokai"))
TAB = " " * 4

_bindings = KeyBindings()
@_bindings.add("c-i")
def _bind(event):
    """Tab key."""
    event.current_buffer.insert_text(TAB)

_wrap_eval = """async def __wrap(nursery):
    result = {}
    _locals = locals()
    del _locals["nursery"]
    return (_locals, result)
"""

_wrap_exec = """async def __wrap(nursery):
    {}
    _locals = locals()
    del _locals["nursery"]
    return (_locals, None)
"""

class TrioRepl(object):
    async def run(self):
        session = PromptSession(
            style=STYLE,
            lexer=PygmentsLexer(PythonLexer),
            include_default_pygments_style=False,
            vi_mode=True,
            key_bindings=_bindings,
        )
        import trio
        async with trio.open_nursery() as nursery:
            while True:
                try:
                    with patch_stdout(nursery=nursery):
                        code = await session.prompt_async(PS1, default="")
                    try:
                        ast_code = ast.parse(code)
                    except SyntaxError as err:
                        if "unexpected EOF" in str(err):
                            # Loop for multiline input
                            indent_level = 1
                            blank = re.compile("^ +$")
                            while True:
                                indent = TAB * indent_level
                                nextline = await session.prompt_async(
                                    PS2, default=indent
                                )
                                if not nextline or blank.match(nextline):
                                    break
                                if nextline[-1] == ":":
                                    indent_level += 1
                                code += "\n    " + nextline
                            try:
                                ast_code = ast.parse(code)
                            except SyntaxError:
                                traceback.print_exc()
                                continue
                        else:
                            traceback.print_exc()
                            continue

                    if not ast_code.body:
                        continue
                    if isinstance(ast_code.body[0], ast.Expr):
                        exec(_wrap_eval.format(code))
                    else:
                        exec(_wrap_exec.format(code))

                    __wrap = locals()['__wrap']
                    try:
                        inner_locals, result = await __wrap(nursery)
                        if result is not None:
                            print(result)
                    except:
                        traceback.print_exc()
                    else:
                        for var, val in inner_locals.items():
                            sys.modules[__name__].__dict__[var] = val

                except KeyboardInterrupt:
                    continue
                except EOFError:
                    nursery.cancel_scope.cancel()


if __name__ == "__main__":
    trio.run(TrioRepl().run)
