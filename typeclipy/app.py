import curses
import time
import re
import threading
import signal
import resource
import sys

from curses import wrapper
from typeclipy.buffer import Buffer

# TODO:
# - Save results on txt file
# - Send results to stdout
# - Send results to logging directory
# - English dictionary
# - Portuguese dictionary
# - Syntax highlighting for code snippets
# - Lazy rendering
# - Bug: First line is not rendered when the text is larger than the buffer height
# - Bug: The result screen is rendered with strange characters
# - Reset menu option after retry

class State:
    def __init__(self, debug_view, has_next=False, minimal=False):
        self.debug = False
        self.autoplay = False
        self.waiting = True
        self.done = False
        self.result_menu_option = 0
        self.has_next = has_next
        self.minimal = minimal
        self.end_time = None
        self.debug_view = debug_view

        self.menu_options = ["Exit", "Retry"]
        if self.has_next:
            self.menu_options.insert(0, "Next")

    def log(self, message):
        self.debug_view.log(message)

class View:
    def __init__(self, colors):
        self.window = None
        self.colors = colors

    def clear(self):
        if self.window != None:
            self.window.clear()

    def render(self):
        pass

class ChildView(View):
    def __init__(self, y, x, height, width, colors):
        super().__init__(colors)
        self.y = y
        self.x = x
        self.height = height
        self.width = width

    def clear(self):
        if self.window != None:
            self.window.clear()
            del self.window

    def render(self):
        self.window = curses.newwin(self.height, self.width, self.y, self.x)
        self.window.bkgd(" ", self.colors["background"])
        self.window.clear()

    def resize(self, y, x, height, width):
        self.y = y
        self.x = x
        self.height = height
        self.width = width

class ScrollView(View):
    def __init__(self, height, width, colors):
        super().__init__(colors)

    def render(self):
        self.window = curses.newpad(height, width)
        self.window.clear()

class TextView(ScrollView):
    def __init__(self, height, width, colors, buffer):
        super().__init__(height, width, colors)
        self.buffer = buffer

class Container(ChildView):
    def __init__(self, y, x, height, width, colors, text):
        super().__init__(y, x, height, width, colors)
        self.buffer = Buffer(text, width - 4, height - 4)
        self.text_view = TextView(self.buffer.line_count(), self.buffer.width, colors, self.buffer)

    def render(self):
        super().render()
        self.window.box()
        self.text_view.render()
        self.window.refresh()

class DebugView(ChildView):
    def __init__(self, y, x, height, width, colors):
        super().__init__(y, x, height, width, colors)

class Screen(View):
    def __init__(self, theme, screen_lock):
        self.theme = theme
        self.screen_lock = screen_lock

    def setup(self, stdscr):
        self.stdscr = stdscr
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)
        curses.curs_set(0)
        self.define_colors()
        self.set_dimensions()
        stdscr.bkgd(" ", self.colors["background"])
        stdscr.clear()
        stdscr.refresh()
        signal.signal(signal.SIGWINCH, self.on_resize)

    def set_dimensions(self):
        self.scr_height, self.scr_width = self.stdscr.getmaxyx()
        curses.resizeterm(self.scr_height, self.scr_width)

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
        curses.start_color()

        background = 235
        success = 70
        primary = 250
        danger = 160

        if self.theme == "warm_sunset":
            background = 52
            success = 142
            primary = 223
            danger = 203
        elif self.theme == "ocean_breeze":
            background = 17
            success = 79
            primary = 188
            danger = 124
        elif self.theme == "solarized_dark":
            background = 235
            success = 108
            primary = 136
            danger = 167

        curses.init_pair(1, success, background)
        curses.init_pair(2, primary, danger)
        curses.init_pair(3, background, primary)
        curses.init_pair(4, primary, background)

        self.colors = {
            "success": curses.color_pair(1),
            "error": curses.color_pair(2),
            "reverse": curses.color_pair(3),
            "background": curses.color_pair(4)
        }

    def on_resize(self, signum, frame):
        pass

class App(Screen):
    def __init__(self, text, has_next, minimal, theme = None, screen_lock = threading.Lock()):
        super().__init__(theme, screen_lock)

        self.text = text
        self.debug = False
        self.autoplay = False
        self.waiting = True
        self.done = False
        self.result_menu_option = 0
        self.has_next = has_next
        self.minimal = minimal
        self.buffer = None
        self.container = None
        self.debug_window = None
        self.text_view = None
        self.status_bar = None
        self.result_view = None
        self.end_time = None

        self.menu_options = ["Exit", "Retry"]
        if self.has_next:
            self.menu_options.insert(0, "Next")

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
            period_or_comma = re.match(r"[,.]$", self.buffer.text[text_index]) is not None
            underlined = not typed and text_index >= self.buffer.highlighted[0] and text_index <= self.buffer.highlighted[1] and not period_or_comma

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
        if self.buffer.index > 0:
            return f"{((1.0 - self.buffer.miss_count / self.buffer.index) * 100):.2f}%"
        return ""

    def wpm(self, now):
        duration_s = now - self.start_time
        duration_min = duration_s / 60
        return int((self.buffer.index + 1) / 5 / duration_min)

    def render_status_bar(self):
        self.status_bar.erase()

        if self.done:
            self.status_bar.refresh()
            return

        if self.waiting:
            self.status_bar.addstr(0, 1, "Ready")
        else:
            now = time.perf_counter()
            wpm = self.wpm(now)
            wpm_s = "--"

            if wpm < 300:
                wpm_s = f"{wpm}"

            self.status_bar.addstr(0, 0, f"  WPM: {wpm_s}")
            self.status_bar.addstr(0, 17, f"Time: {int(now - self.start_time)}s")
            self.status_bar.addstr(0, 35, f"Accuracy: {self.accuracy()}")

        self.status_bar.refresh()
        self.container.refresh()

    def render_result(self):
        if self.end_time == None:
            self.end_time = time.perf_counter()

        duration_s = self.end_time - self.start_time
        duration_min = duration_s / 60

        wpm = self.wpm(self.end_time)
        self.result_view.addstr(0, 0, f"WPM: {wpm:.0f}")

        if duration_s > 60:
            rest = (duration_min - int(duration_min)) * 60
            self.result_view.addstr(1, 0, f"Time: {int(duration_min)}m {int(rest)}s")
        else:
            self.result_view.addstr(1, 0, f"Time: {duration_s:.2f}s")

        self.result_view.addstr(2, 0, f"Accuracy: {self.accuracy()}")


    def log_memory_usage(self):
        usage = resource.getrusage(resource.RUSAGE_SELF)
        mem_kb = usage.ru_maxrss

        # On macOS, ru_maxrss is in *bytes*, not kilobytes
        if sys.platform == "darwin":
            mem_kb = mem_kb / 2024

        mem_mb = mem_kb / 1024
        self.log(f"Memory usage: {mem_mb:.2f} MB")

    def render_result_menu(self):
        while True:
            menu_index = 0

            for idx, option in enumerate(self.menu_options):
                prefix = "›  " if idx == self.result_menu_option else "   "
                text = f"{prefix}{option}".ljust(10)
                color = self.colors["reverse"] if idx == self.result_menu_option else 0
                self.result_view.addstr(5 + idx, 0, text, color)

            self.result_view.refresh()
            key = self.result_view.getch()

            if key in (curses.KEY_DOWN, ord("j")) and self.result_menu_option < len(self.menu_options) - 1:
                self.result_menu_option += 1

            elif key in (curses.KEY_UP, ord("k")) and self.result_menu_option > 0:
                self.result_menu_option -= 1

            elif key in (curses.KEY_ENTER, 10, 13):
                return

            else:
                continue

    def on_resize(self, signum, frame):
        with self.screen_lock:
            try:
                self.text_view.clear()
                self.status_bar.clear()
                if self.debug:
                    self.debug_window.clear()
                if self.done:
                    self.result_view.clear()
                self.container.clear()
                self.stdscr.clear()
                curses.endwin()
                self.stdscr.refresh()
                self.set_dimensions()

                self.render()
            except Exception as err:
                print(f"an error occurred when resizing the screen: {err}")

    def render(self):
        if self.buffer != None:
            self.buffer.resize(self.buffer_width, self.buffer_height)
        else:
            self.buffer = Buffer(self.text, self.buffer_width, self.buffer_height)

        # Resize default dimensions if buffer height is smaller than expected
        diff = self.buffer_height - self.buffer.height
        self.height -= diff
        self.buffer_height -= diff
        self.y = self.y + diff // 2
        self.buffer_y += diff // 2

        if self.container != None:
            del self.container

        self.container = curses.newwin(self.height, self.width, self.y, self.x)

        self.container.bkgd(" ", self.colors["background"])
        self.container.clear()
        self.container.box()

        if self.text_view != None:
            del self.text_view

        self.text_view = curses.newpad(self.buffer.line_count(), self.buffer_width)
        self.text_view.bkgd(" ", self.colors["background"])
        self.text_view.clear()

        if self.status_bar != None:
            del self.status_bar

        self.status_bar = self.container.derwin(1, self.buffer_width + 2, self.buffer_height + 2, 1)
        # self.log(f"status_bar dimensions: {self.buffer_width + 2} {self.buffer_height + 2}\nScreen dimensions: {self.scr_width} {self.scr_height}\ncols and LINES: {curses.COLS} {curses.LINES}")
        self.status_bar.bkgd(" ", self.colors["reverse"])

        if self.debug:
            if self.debug_window != None:
                del self.debug_window

            self.debug_window = curses.newwin(6, curses.COLS, curses.LINES - 5, 0)
            self.debug_window.refresh()

        self.container.refresh()

        if self.done:
            if self.result_view != None:
                del self.result_view

            self.result_view = self.container.derwin(self.buffer_height, self.buffer_width, 1, 2)
            self.result_view.keypad(True)

            self.render_result()

    def run(self, stdscr):
        stop = False

        self.setup(stdscr)
        self.render()

        debug_view = DebugView(6, curses.COLS, curses.LINES - 5, 0, self.colors)
        state = State(debug_view, self.has_next, self.minimal)
        container = Container(self.y, self.x, self.height, self.width, self.colors, self.text)

        def update_status_bar():
            while True:
                with self.screen_lock:
                    self.render_status_bar()

                if self.done:
                    break

                time.sleep(1)

        # Retry loop. The user continues here if he chooses 'Retry' at the end
        while True:
            self.print_rendered_text(self.text_view)

            t = threading.Thread(target=update_status_bar, daemon=True)
            t.start()

            self.text_view.move(0, 0)

            self.start_time = 0

            # Main loop. Iterates through all characters of the text
            while self.buffer.index < len(self.text):
                c = self.buffer.text[self.buffer.index]
                seq = []

                if self.autoplay:
                    time.sleep(0.1)
                else:
                    try:
                        c = self.text_view.get_wch()
                        seq.append(c)

                        if c == '\x1b':
                            c2 = self.text_view.get_wch()

                            if c2 != -1:
                                seq.append(c2)
                    except curses.error:
                        continue

                # Esc + Del?
                if seq == ['\x1b', '\x7f']:
                    self.buffer.delete_word()
                elif c != curses.KEY_RESIZE:
                    self.buffer.compute(c)

                    if self.waiting:
                        self.start_time = time.perf_counter()
                        self.end_time = None
                        self.waiting = False

                with self.screen_lock:
                    self.print_rendered_text(self.text_view)

            self.done = True

            self.text_view.clear()
            self.text_view.refresh(self.buffer.scroll_pos(), 0, self.buffer_y, self.buffer_x, self.buffer_height + self.y, self.buffer_width + self.x)

            if self.minimal:
                break

            self.result_view = self.container.derwin(self.buffer_height, self.buffer_width, 1, 2)
            self.result_view.keypad(True)

            self.render_result()
            self.render_result_menu()

            selected_menu_option = self.menu_options[self.result_menu_option]

            if selected_menu_option == "Retry":
                self.buffer = Buffer(self.text, self.buffer_width, self.buffer_height)
                self.waiting = True
                self.done = False

                del self.result_view
                self.container.clear()
                self.container.box()
                self.container.refresh()

                continue
            if selected_menu_option == "Exit":
                stop = True
                break

            if selected_menu_option == "Next":
                break

        self.teardown(stdscr)
        return stop

    def start(self):
        return wrapper(self.run)
