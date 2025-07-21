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
    parser.add_argument("--minimal", help="Don't show results", action="store_true")
    parser.add_argument("--theme", help="Application theme. Options: warm_sunset, ocean_breeze, solarized_dark")
    parser.add_argument("--lang", help="Word list language. Options: en, pt")

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
    else:
        text_list = []
        file = "words_en.txt"
        if args.lang in ["en", "pt"]:
            file = f"words_{args.lang}.txt"

        base_dir = os.path.dirname(__file__)
        file_path = os.path.join(base_dir, "data", file)

        with open(file_path, "r", encoding="utf-8") as f:
            text_list.append(pick_words(f.read().strip()))

    screen_lock = threading.Lock()

    try:
        for idx, text in enumerate(text_list):
            app = App(text, has_next=(idx < len(text_list) - 1), minimal=args.minimal, theme=args.theme, screen_lock=screen_lock)
            stop = app.start()

            if stop:
                break
    except KeyboardInterrupt:
        pass

