from prompt_toolkit.completion import Completer
from prompt_toolkit.completion.word_completer import WordCompleter
from prompt_toolkit.document import Document

from .aria2.proxy import CMD as aria2_cmd
from .mpd.proxy import CMD as mpd_cmd
from .etree.proxy import CMD as etree_cmd

class TapedeckCompleter(Completer):
    def __init__(self, td_cmd):
        self.td_cmd = td_cmd
        self.root_opts = [
            "aria2.", "etree.", "mpd.",
            "trio", "trignalc",
            "quit",
        ]
        self.root = WordCompleter(self.root_opts)

    def get_completions(self, document, event):
        text = document.text_before_cursor.lstrip()
        if "." in text and not self.td_cmd.namespace:
            completer = None
            words = ["~"]
            first_term = text.split(".")[0]
            if first_term == "aria2":
                words += list(aria2_cmd.keys())
            elif first_term == "mpd":
                words += list(mpd_cmd.keys())
            elif first_term == "etree":
                words += list(etree_cmd.keys())
            completer = WordCompleter(words, ignore_case=True)

            # If we have a sub completer, use this for the completions.
            if completer is not None:
                # Add one first_term idx because of "." in "aria2.".
                remaining_text = document.text[len(first_term) + 1:].lstrip()
                move_cursor = len(document.text) - len(remaining_text)
                new_document = Document(
                    remaining_text,
                    cursor_position=document.cursor_position - move_cursor)
                for c in completer.get_completions(new_document, event):
                    yield c
        elif self.td_cmd.namespace:
            words = ["~"]
            if self.td_cmd.namespace == "aria2.":
                first_term = "aria2"
                words += list(aria2_cmd.keys())
            elif self.td_cmd.namespace == "mpd.":
                first_term = "mpd"
                words += list(mpd_cmd.keys())
            completer = WordCompleter(words, ignore_case=True)
            for c in completer.get_completions(document, event):
                yield c
        else:
            for c in self.root.get_completions(document, event):
                yield c
