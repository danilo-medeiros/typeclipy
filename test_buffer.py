from buffer import Buffer

class TestBuffer:
    def test_initialize(self):
        buf = Buffer("Hello World", 80)
        assert buf.text == "Hello World"
        assert buf.width == 80
        assert buf.index == 0

    def test_compute_match(self):
        buf = Buffer("Hello World", 80)
        buf.compute("H")
        assert len(buf.misses) == 0
        assert buf.index == 1

    def test_compute_miss(self):
        buf = Buffer("Hello World", 80, 30, 6)
        buf.compute("F")
        assert len(buf.misses) == 1
        assert buf.misses == [6]
        assert buf.index == 7

    def test_compute_match_with_line_breaks(self):
        buf = Buffer("Hello World\nWith line\nbreaks", 80, 30, 15)
        buf.compute("h")
        assert buf.misses == []
        assert buf.index == 16

    def test_compute_miss_with_line_breaks(self):
        buf = Buffer("Hello World\nWith line\nbreaks", 80, 30, 15)
        buf.compute("g")
        assert buf.misses == [15]
        assert buf.index == 16

    def test_render(self):
        buf = Buffer("Hello World", 80, 30, 5)
        assert buf.pos_x == 5
        assert buf.pos_y == 0
        assert buf.rendered_text == "Hello World"
        assert buf.highlighted == (-1, -1)

    def test_position_after_computes(self):
        buf = Buffer("Hello World", 80)
        buf.compute("H")
        buf.compute("e")
        buf.compute("l")
        assert buf.pos_x == 3
        assert buf.pos_y == 0

    def test_position_after_backspace(self):
        buf = Buffer("Hello World", 80)
        buf.compute("H")
        buf.compute("e")
        buf.compute("e")
        buf.compute('\x7f')
        assert buf.pos_x == 2
        assert buf.pos_y == 0
        assert buf.misses == []
        assert buf.miss_count == 1

    def test_position_with_line_breaks(self):
        buf = Buffer("Hello World\nWith line\nbreaks", 80, 30, 15)
        assert buf.rendered_text == "Hello World\nWith line\nbreaks"
        assert buf.pos_y == 1
        assert buf.pos_x == 3
        assert buf.highlighted == (12, 15)

    def test_position_with_line_wrap(self):
        buf = Buffer("Hello World, this example has a very long line", 20, 30, 21)
        assert buf.rendered_text == "Hello World, this\nexample has a very\nlong line"
        assert buf.pos_y == 1
        assert buf.pos_x == 3
        assert buf.highlighted == (18, 24)

    def test_render_with_line_wrap_on_space(self):
        buf = Buffer("Hello world", 6, 30, 6)
        assert buf.pos_x == 0
        assert buf.pos_y == 1
        assert buf.rendered_text == "Hello\nworld"
        assert buf.highlighted == (6, 10)

    def test_word_bounds(self):
        buf = Buffer("Hello World!", 80)
        assert buf.word_bounds(6) == (6, 11)

    def test_word_bounds_with_line_breaks(self):
        buf = Buffer("Hello World\nWith line\nbreaks", 80, 30, 15)
        assert buf.word_bounds(10) == (6, 10)

    def test_word_bounds_strip_commas(self):
        buf = Buffer("This sentence, has a comma", 80)
        assert buf.word_bounds(5) == (5, 12)

    def test_line_count(self):
        buf = Buffer("Hello World with one line", 80)
        assert buf.line_count() == 1

    def test_line_count_with_line_wrap(self):
        buf = Buffer("Hello very long line", 12)
        assert buf.line_count() == 2

    def test_curr_line(self):
        text = "\n".join([f"asdf" for i in range(20)])
        buf = Buffer(text, 10, 5, 26)
        assert buf.line_count() == 20
        assert buf.curr_line() == 5

    def test_scroll_pos(self):

#         Inputs:
#         * Line count
#         * Screen height
#         * Current line
#         * Padding
        text = "\n".join([f"a" for i in range(15)])
        buf = Buffer(text, 10, 10, 12)

        assert buf.height == 10
        assert buf.line_count() == 15
        assert buf.curr_line() == 6
        assert buf.scroll_pos() == 1

        buf = Buffer(text, 10, 10, 14)

        assert buf.height == 10
        assert buf.line_count() == 15
        assert buf.curr_line() == 7
        assert buf.scroll_pos() == 2

        buf = Buffer(text, 10, 10, 22)

        assert buf.height == 10
        assert buf.line_count() == 15
        assert buf.curr_line() == 11
        assert buf.scroll_pos() == 5

