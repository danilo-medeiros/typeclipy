import re

class Buffer:
    def __init__(self, text, width, height = 30, index = 0, leading_spaces = False):
        self.text = text
        self.width = width
        self.height = height
        self.index = index
        self.misses = []
        self.miss_count = 0
        self.pos_x = 0
        self.pos_y = 0
        self.rendered_text = ""
        self.highlighted = (0, 0)
        self.positions = []
        self.leading_spaces = leading_spaces
        self.typed = 0
        self.render()
        self.update_height()

    def resize(self, width, height):
        self.width = width
        self.height = height
        self.render()
        self.update_height()

    # Resize buffer if content is smaller than height:
    def update_height(self):
        lc = self.line_count()
        if self.height > lc:
            self.height = max(lc, 8)

    def highlight(self):
        if self.index < len(self.text):
            word_bounds = self.word_bounds(self.index)

            if self.__is_delimiter(self.text[self.index]):
                self.highlighted = (-1, -1)
            else:
                self.highlighted = word_bounds

    def position(self):
        if self.index < len(self.text):
            return self.positions[self.index]

        return self.positions[-1]

    def render(self):
        rendered_text = ""
        col_index = 0
        line_index = 0
        text_index = 0

        while text_index < len(self.text):
            # let's calculate the position of each character, as it will not change later
            if len(self.rendered_text) == 0:
                self.positions.append((line_index, col_index))

            # Find word
            word_bounds = self.word_bounds(text_index)
            remaining_word_length = word_bounds[1] - text_index
            line_end = col_index + remaining_word_length

            if text_index == self.index:
                self.highlight()

            if line_end >= self.width - 1 or self.text[text_index] == "\n":
                col_index = 0
                line_index += 1
                rendered_text += "\n"
            else:
                col_index += 1
                rendered_text += self.text[text_index]

            text_index += 1

        self.rendered_text = rendered_text

    def line_count(self):
        return len(self.rendered_text.split("\n"))

    def curr_line(self):
        return len(self.rendered_text[:self.index].split("\n")) - 1

    def scroll_pos(self):
        current_line = self.curr_line()
        screen_height = self.height
        line_count = self.line_count()
        padding = 5

        if current_line + padding < screen_height - 1 or line_count <= screen_height:
            return 0

        if current_line + padding > line_count - 1:
            return line_count - screen_height

        return current_line + padding - screen_height

    def word_bounds(self, curr_index):
        start_index = curr_index

        while start_index > 0:
            if self.__is_delimiter(self.text[start_index - 1]):
                break
            else:
                start_index -= 1

        end_index = curr_index
        while end_index < len(self.text) - 1:
            if self.__is_delimiter(self.text[end_index + 1]):
                break
            else:
                end_index += 1

        return (start_index, end_index)

    def compute(self, input):
        if input == '\x7f':
            if self.index > 0:
                self.index -= 1
                if self.index in self.misses:
                    self.misses.remove(self.index)
                    self.highlight()
            return

        if input != self.text[self.index]:
            self.misses.append(self.index)
            self.miss_count += 1
        else:
            if self.index in self.misses:
                self.misses.remove(self.index)

        self.index += 1
        self.typed += 1

        if self.leading_spaces and input == "\n":
            while self.text[self.index] == " ":
                self.index += 1

        self.highlight()

    def delete_word(self):
        curr_index = self.index

        # If we are at the beginning of a word, go back one index
        if curr_index > 0 and self.text[curr_index-1] == " ":
            curr_index -= 1

        go_to = self.word_bounds(curr_index)[0]

        while True:
            if self.index in self.misses:
                self.misses.remove(self.index)

            if self.index == go_to or self.index == 0:
                break

            self.index -= 1

        self.highlight()

    def __is_delimiter(self, value):
        return re.match(r"[\s\n]$", value) is not None
