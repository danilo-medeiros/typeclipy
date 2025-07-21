import argparse
import sys
import os
import threading
import random

from typeclipy.app import App

DEFAULT_WORD_LIST_LENGTH = 30

def pick_words(words):
    word_list = words.split("\n")
    res = []

    while len(res) <= DEFAULT_WORD_LIST_LENGTH:
        idx = random.randint(0, len(word_list) - 1)
        res.append(word_list[idx])

    return " ".join(res)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", nargs="+", help="The text you want to type")
    parser.add_argument("--file", nargs="+", help="The path(s) of the .txt file(s) that contains the text that you want to type")
    parser.add_argument("--minimal", help="Minimalist mode", action="store_true")
    parser.add_argument("--theme", help="Application theme", choices=["warm_sunset", "ocean_breeze", "solarized_dark"])
    parser.add_argument("--lang", help="Word list language", choices=["pt", "en"], default="en")
    parser.add_argument("--out", default="-", help="File to save the results")

    args = parser.parse_args()

    text_list = args.text or []

    if not sys.stdin.isatty():
        data = sys.stdin.read()
        text_list = [data.strip()]
        tty = open("/dev/tty")
        os.dup2(tty.fileno(), sys.stdin.fileno())
    elif args.file:
        text_list = []

        for file_path in args.file:
            with open(file_path, "r", encoding="utf-8") as f:
                text_list.append(f.read().strip())
    elif len(text_list) == 0:
        text_list = []
        file = f"words_{args.lang}.txt"

        base_dir = os.path.dirname(__file__)
        file_path = os.path.join(base_dir, "data", file)

        with open(file_path, "r", encoding="utf-8") as f:
            text_list.append(pick_words(f.read().strip()))

    screen_lock = threading.Lock()
    tests = []

    try:
        for idx, text in enumerate(text_list):
            app = App(text, has_next=(idx < len(text_list) - 1), minimal=args.minimal, theme=args.theme, screen_lock=screen_lock)
            stop = app.start()
            tests.append(app)

            if stop:
                break
    except KeyboardInterrupt:
        pass

    if not args.minimal:
        output_stream = open(args.out, "w") if args.out != "-" else sys.stdout

        for idx, test in enumerate(tests):
            print(f"{test.report()}", file=output_stream)

