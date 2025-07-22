from pygments.lexers import PythonLexer, JavascriptLexer, CLexer, CppLexer, RubyLexer, JavaLexer
from pygments import lex
from pygments.token import Token

TOKEN2PAIR = {
    Token.Keyword:  5,
    Token.Literal.String: 6,
    Token.Literal.Number: 7,
    Token.Comment: 8,
    Token.Name.Function: 9,
    Token.Operator: 10,
    Token.Name: 11,
    Token.Function.Name: 12,
    Token.Text: 0,
}

LEXERS = {
    "js": JavascriptLexer,
    "py": PythonLexer,
    "c": CLexer,
    "cpp": CppLexer,
    "rb": RubyLexer,
    "java": JavaLexer
}

def color_list(file_type, text):
    colors = []
    lexer = LEXERS.get(file_type, None)

    if lexer == None:
        return []

    for tok, text in lex(text, lexer()):
        while tok not in TOKEN2PAIR and tok.parent:
            tok = tok.parent
        pair_number = TOKEN2PAIR.get(tok, 0)
        for t in text:
            colors.append(pair_number)

    return colors
