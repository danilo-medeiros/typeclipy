import argparse
import curses
import time
from curses import wrapper
from buffer import Buffer

parser = argparse.ArgumentParser()
parser.add_argument("--text", help="The text you want to type")
parser.add_argument("--file", help="The path of the .txt file that contains the text that you want to type")
args = parser.parse_args()

class App:
    def __init__(self, text):
        self.text = text
        self.padding_y = 2
        self.padding_x = 2
        self.auto_line_breaks = []

    def setup(self, stdscr):
        stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_RED)

    def teardown(self, stdscr):
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()

    def text_wrap(self, max_width):
        char_index = 0
        col = 0

        wrapped_text = ""

        while char_index < len(self.text):
            if self.text[char_index] == " ":
                next_space = self.text[char_index:].find(" ")
                next_break = self.text[char_index].find("\n")

                word_end = 0

                if next_space < next_break:
                    word_end = next_space
                else:
                    word_end = next_break

                word_length = word_end - char_index

                if col + word_length >= max_width:
                    wrapped_text += "\n"
                    char_index += 1
                    col = 0
                    continue

            wrapped_text += self.text[char_index]
            char_index += 1
            col += 1

        return wrapped_text

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
                text = "⏎\n"

            if miss:
                win.addstr(text, curses.color_pair(2))
            elif hit:
                win.addstr(text, curses.color_pair(1))
            elif underlined:
                win.addstr(text, curses.A_UNDERLINE)
            else:
                win.addstr(text)

            text_index += 1

        win.move(self.buffer.pos_y, self.buffer.pos_x)
        win.refresh()

    def run(self, stdscr):
        self.setup(stdscr)

        begin_x = round(curses.COLS * 0.15); begin_y = round(curses.LINES * 0.25)
        height = round(curses.LINES * 0.5); width = round(curses.COLS * 0.70)

        outer = curses.newwin(height, width, begin_y, begin_x - 1)
        outer.box()

        win = outer.derwin(height - self.padding_y, width - self.padding_x * 2, 1, self.padding_x)

        self.buffer = Buffer(self.text, width - self.padding_x * 2)

        self.print_rendered_text(win)
        win.move(0, 0)

        outer.refresh()
        win.refresh()

        start_time = 0
        first_key_stroke = True

        while self.buffer.index < len(self.text):
            c = win.get_wch()

            if first_key_stroke:
                start_time = time.perf_counter()
                first_key_stroke = False

            self.buffer.compute(c)
            self.print_rendered_text(win)

        end_time = time.perf_counter()
        win.clear()

        accuracy = (1.0 - self.buffer.miss_count / len(self.text)) * 100
        duration_s = end_time - start_time
        duration_min = duration_s / 60
        wpm = len(self.text) / 5 / duration_min

        win.addstr(0, 0, f"WPM: {wpm:.0f}")
        win.addstr(1, 0, f"Time: {duration_s:.2f}s")
        win.addstr(2, 0, f"Accuracy: {accuracy:.2f}%")
        win.addstr(height - 3, 0, "Press any key to exit...")
        curses.curs_set(0)
        ex = win.getch()

        self.teardown(stdscr)

text = args.text

if args.file != None:
    file = open(args.file)
    text = file.read().strip()

app = App(text)

try:
    wrapper(app.run)
except KeyboardInterrupt:
    pass

