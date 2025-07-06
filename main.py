import argparse
import curses
import time
import re
import threading
import sys
import os

from curses import wrapper
from buffer import Buffer

parser = argparse.ArgumentParser()
parser.add_argument("--text", nargs="+", help="The text you want to type")
parser.add_argument("--file", nargs="+", help="The path(s) of the .txt file(s) that contains the text that you want to type")
parser.add_argument("--minimal", help="Don't show results", action=argparse.BooleanOptionalAction)
args = parser.parse_args()

# TODO:
# - Improve app responsivity during runtime

class App:
    def __init__(self, text, has_next, minimal):
        self.text = text
        self.debug = False
        self.autoplay = False
        self.waiting = True
        self.done = False
        self.screen_lock = threading.Lock()
        self.result_menu_option = 0
        self.has_next = has_next
        self.minimal = minimal

        self.menu_options = ["Retry", "Exit"]
        if self.has_next:
            self.menu_options.insert(0, "Next")

    def setup(self, stdscr):
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)
        curses.curs_set(0)
        self.define_colors()

        if curses.COLS > 200:
            self.x = round(curses.COLS * 0.25)
            self.y = round(curses.LINES * 0.25)
            self.height = round(curses.LINES * 0.5)
            self.width = round(curses.COLS * 0.5)
        elif curses.COLS > 100:
            self.x = round(curses.COLS * 0.15)
            self.y = round(curses.LINES * 0.25)
            self.height = round(curses.LINES * 0.5)
            self.width = round(curses.COLS * 0.70)
        else:
            self.x = 0
            self.y = 0
            self.height = curses.LINES
            self.width = curses.COLS

        self.buffer_x = self.x + 2
        self.buffer_y = self.y + 1

        # Subtract space for:
        # - 2 columns for borders,
        # - 1 column for line break (enter),
        # - 1 column for left padding to align content.
        self.buffer_width = self.width - 4

        # We need to subtract 3 lines from the height to set the buffer height:
        # 1 for the top border, 1 for the bottom border, and 2 for the status bar.
        self.buffer_height = self.height - 4

    def define_colors(self):
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_RED)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)

        self.colors = {
            "success": curses.color_pair(1),
            "error": curses.color_pair(2),
            "reverse": curses.color_pair(3),
        }

    def teardown(self, stdscr):
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()

    def print_rendered_text(self, win):
        text_index = 0

        win.move(0, 0)

        while text_index < len(self.buffer.text):
            miss = text_index in self.buffer.misses
            hit = text_index < self.buffer.index and not miss
            typed = miss or hit
            underlined = not typed and text_index >= self.buffer.highlighted[0] and text_index <= self.buffer.highlighted[1]

            text = self.buffer.rendered_text[text_index]

            if self.buffer.text[text_index] == "\n":
                text = "↵\n"

            try:
                if miss:
                    win.addstr(text, self.colors["error"])
                elif hit:
                    win.addstr(text, self.colors["success"])
                elif underlined:
                    win.addstr(text, curses.A_UNDERLINE)
                else:
                    win.addstr(text)
            except Exception as e:
                error = f"Error trying to print character '{text}', index #{text_index}. Text around: '{self.buffer.rendered_text[text_index - 10:text_index + 10]}'"
                buffer_info = f"self.buffer_width: {self.buffer_width}, self.buffer_height: {self.buffer_height}"
                outer_info = f"self.width: {self.width}, self.height: {self.height}"
                self.log(f"{error}\nbuffer:\t{buffer_info}\nouter:\t{outer_info}")

            text_index += 1

        win.move(self.buffer.pos_y, self.buffer.pos_x)

        if len(self.buffer.rendered_text) > self.buffer.index:
            if self.buffer.text[self.buffer.index] == "\n":
                win.addstr(self.buffer.pos_y, self.buffer.pos_x, "↵\n", self.colors["reverse"])
            else:
                win.addstr(self.buffer.pos_y, self.buffer.pos_x, self.buffer.rendered_text[self.buffer.index], self.colors["reverse"])

        win.refresh(self.buffer.scroll_pos(), 0, self.buffer_y, self.buffer_x, self.buffer_height + self.y, self.buffer_width + self.x)

    def log(self, message):
        if self.debug:
            self.debug_window.move(0, 0)
            self.debug_window.deleteln()
            self.debug_window.addstr(0, 0, message)
            self.debug_window.refresh()

    def accuracy(self):
        return f"{((1.0 - self.buffer.miss_count / self.buffer.index) * 100):.2f}%"

    def wpm(self, now):
        duration_s = now - self.start_time
        duration_min = duration_s / 60
        return int((self.buffer.index + 1) / 5 / duration_min)

    def render_status_bar(self, status_bar, set_interval = False):
        status_bar.erase()

        if self.done:
            status_bar.refresh()
            return

        if self.waiting:
            status_bar.addstr(0, 1, "Ready")
        else:
            now = time.perf_counter()
            wpm = self.wpm(now)

            if wpm < 300:
                status_bar.addstr(0, 0, f"  WPM: {wpm}")

            status_bar.addstr(0, 17, f"Time: {int(now - self.start_time)}s")
            status_bar.addstr(0, 35, f"Accuracy: {self.accuracy()}")

        status_bar.refresh()

        def wrapper():
            with self.screen_lock:
                self.render_status_bar(status_bar)

        t = threading.Timer(0.5, wrapper)
        t.daemon = True
        t.start()

    def render_result(self, result_win):
        end_time = time.perf_counter()

        duration_s = end_time - self.start_time
        duration_min = duration_s / 60

        wpm = self.wpm(end_time)
        result_win.addstr(0, 0, f"WPM: {wpm:.0f}")

        if duration_s > 60:
            rest = (duration_min - int(duration_min)) * 60
            result_win.addstr(1, 0, f"Time: {int(duration_min)}m {int(rest)}s")
        else:
            result_win.addstr(1, 0, f"Time: {duration_s:.2f}s")

        result_win.addstr(2, 0, f"Accuracy: {self.accuracy()}")

    def render_result_menu(self, result_win):
        while True:
            menu_index = 0

            for idx, option in enumerate(self.menu_options):
                prefix = "›  " if idx == self.result_menu_option else "   "
                text = f"{prefix}{option}".ljust(10)
                color = self.colors["reverse"] if idx == self.result_menu_option else 0
                result_win.addstr(5 + idx, 0, text, color)

            result_win.refresh()
            key = result_win.getch()

            self.log(f"User pressed key: {key}")

            if key in (curses.KEY_DOWN, ord("j")) and self.result_menu_option < len(self.menu_options) - 1:
                self.result_menu_option += 1

            elif key in (curses.KEY_UP, ord("k")) and self.result_menu_option > 0:
                self.result_menu_option -= 1

            elif key in (curses.KEY_ENTER, 10, 13):
                return

    def run(self, stdscr):
        self.setup(stdscr)

        self.buffer = Buffer(self.text, self.buffer_width, self.buffer_height)

        # Resize default dimensions if buffer height is smaller than expected
        diff = self.buffer_height - self.buffer.height
        self.height = self.height - diff
        self.buffer_height = self.buffer_height - diff
        self.y = self.y + diff // 2
        self.buffer_y = self.buffer_y + diff // 2

        outer = curses.newwin(self.height, self.width, self.y, self.x)
        outer.box()

        stop = False

        if self.debug:
            self.debug_window = curses.newwin(6, curses.COLS, curses.LINES - 5, 0)
            self.debug_window.refresh()

        self.log(f"Starting application, has_next={self.has_next}")

        win = curses.newpad(self.buffer.line_count(), self.buffer_width)

        status_bar = outer.derwin(1, self.buffer_width + 2, self.buffer_height + 2, 1)
        status_bar.bkgd(" ", self.colors["reverse"])

        outer.refresh()

        while True:
            self.print_rendered_text(win)
            self.render_status_bar(status_bar)
            win.move(0, 0)

            self.start_time = 0

            while self.buffer.index < len(self.text):
                c = self.buffer.text[self.buffer.index]
                if self.autoplay:
                    time.sleep(0.1)
                else:
                    c = win.get_wch()

                self.buffer.compute(c)

                if self.waiting:
                    self.start_time = time.perf_counter()
                    self.waiting = False
                    self.render_status_bar(status_bar, True)

                with self.screen_lock:
                    self.print_rendered_text(win)


            self.done = True

            win.clear()
            win.refresh(self.buffer.scroll_pos(), 0, self.buffer_y, self.buffer_x, self.buffer_height + self.y, self.buffer_width + self.x)

            if self.minimal:
                break

            result_win = outer.derwin(self.buffer_height, self.buffer_width, 1, 2)
            result_win.keypad(True)
            self.render_result(result_win)
            self.render_result_menu(result_win)

            selected_menu_option = self.menu_options[self.result_menu_option]

            if selected_menu_option == "Retry":
                self.buffer = Buffer(self.text, self.buffer_width, self.buffer_height)
                self.waiting = True
                self.done = False

                del result_win
                outer.clear()
                outer.box()
                outer.refresh()

                continue
            if selected_menu_option == "Exit":
                stop = True
                break

            if selected_menu_option == "Next":
                break

        self.teardown(stdscr)
        return stop

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
        stop = wrapper(app.run)
        if stop:
            break
except KeyboardInterrupt:
    pass

