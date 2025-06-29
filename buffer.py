class Buffer:
    def __init__(self, text, width, index = 0):
        self.text = text
        self.width = width
        self.index = index
        self.misses = []
        self.miss_count = 0
        self.pos_x = 0
        self.pos_y = 0
        self.rendered_text = ""
        self.highlighted = (0, 0)
        self.render()

    def render(self):
        rendered_text = ""

        col_index = 0
        line_index = 0
        text_index = 0
        
        while text_index < len(self.text):
            # Set position variables if we are at the right place
            if text_index == self.index:
                self.pos_x = col_index
                self.pos_y = line_index

            # Find word
            word_bounds = self.word_bounds(text_index)
            remaining_word_length = word_bounds[1] - text_index
            line_end = col_index + remaining_word_length

            if text_index == self.index:
                if self.__space_or_line_break(self.text[text_index]):
                    self.highlighted = (-1, -1)
                else:
                    self.highlighted = word_bounds

            if line_end >= self.width or self.text[text_index] == "\n":
                col_index = 0
                line_index += 1
                rendered_text += "\n"
            else:
                col_index += 1
                rendered_text += self.text[text_index]

            text_index += 1

        self.rendered_text = rendered_text

    def word_bounds(self, curr_index):
        start_index = curr_index

        while start_index > 0:
            if self.__space_or_line_break(self.text[start_index - 1]):
                break
            else:
                start_index -= 1

        end_index = curr_index
        while end_index < len(self.text) - 1:
            if self.__space_or_line_break(self.text[end_index + 1]):
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
                self.render()
            return

        if input != self.text[self.index]:
            self.misses.append(self.index)
            self.miss_count += 1

        self.index += 1
        self.render()

    def __space_or_line_break(self, value):
        return value == " " or value == "\n"
