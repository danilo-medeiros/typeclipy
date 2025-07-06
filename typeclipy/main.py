import argparse
import sys
import os

from typeclipy.app import App

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", nargs="+", help="The text you want to type")
    parser.add_argument("--file", nargs="+", help="The path(s) of the .txt file(s) that contains the text that you want to type")
    parser.add_argument("--minimal", help="Don't show results", action="store_true")
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

    try:
        for idx, text in enumerate(text_list):
            app = App(text, has_next=(idx < len(text_list) - 1), minimal=args.minimal)
            stop = app.start()

            if stop:
                break
    except KeyboardInterrupt:
        pass

