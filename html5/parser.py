import string

from .dom import Dom
from .constant import void_tag

__all__ = ['parse']


def parse(html5_code: str) -> Dom:
    return Html5Parser(html5_code).parse()


class Html5Parser(object):
    def __init__(self, html5_code: str) -> 'Html5Parser':
        self._code = html5_code
        self._parse_index = 0

        if '\n\r' in self._code:
            self._linesep = '\n'
        elif '\r' in self._code:
            self._linesep = '\r'
        else:
            self._linesep = '\n'

        # fuck BOM off
        while 1:
            if self._code[self._parse_index] == '<':
                break
            else:
                self._parse_index += 1

    def parse(self) -> Dom:
        root_node = Dom(None)
        while not self.parse_end():
            sub_node = self.parse_html_tag()
            root_node.children.append(sub_node)
            self.ignore_whitespace()
        return root_node

    def parse_html_tag_name(self) -> str:
        next_3_chars = self.get_next_n_chars(3)
        if next_3_chars == '!--':
            return next_3_chars
        else:
            self.backtrack(3)
        return self.get_str_until_char(string.whitespace + '>')

    def parse_html_tag_attribute_name(self) -> str:
        self.ignore_whitespace()
        return self.get_str_until_char(string.whitespace + '/=>')

    def parse_html_tag_attribute_value(self) -> str:
        self.ignore_whitespace()
        string_start_char = self.get_next_char()
        if string_start_char in "'\"":
            attr = self.get_str_until_char(string_start_char, escape=True)
            self.get_next_char()
            return string_start_char + attr + string_start_char
        else:
            self.backtrack()
            return ''

    def parse_html_tag_attribute(self) -> dict:
        attributes = dict()
        while 1:
            next_char = self.get_next_char()
            if next_char == '/':
                assert '>' == self.get_next_char()
                break
            elif next_char == '>':
                break
            else:
                self.backtrack()

            key = self.parse_html_tag_attribute_name()
            self.ignore_whitespace()
            equal_char = self.get_next_char()
            if equal_char == '=':
                value = self.parse_html_tag_attribute_value()
                attributes[key] = value
            else:
                self.backtrack()
                attributes[key] = None
        return attributes

    def parse_html_tag(self) -> Dom:
        self.ignore_whitespace()
        next_char = self.get_next_char()
        assert next_char == '<'
        tag_name = self.parse_html_tag_name()
        if tag_name == '!--':
            comment = self.parse_html_comment()
            dom = Dom(tag_name)
            dom.children.append(comment)
            return dom

        tag_attributes = self.parse_html_tag_attribute()
        dom = Dom(tag_name)
        dom.attributes = tag_attributes
        if tag_name in void_tag:
            return dom

        if tag_name == 'style':
            css = self.parse_style_code()
            dom.children.append(css)
            return dom
        elif tag_name == 'script':
            js = self.parse_js_code()
            dom.children.append(js)
            return dom

        while 1:
            if self.parse_end():
                return dom
            text = self.parse_html_plain_text()
            if text:
                dom.children.append(text)
            self.ignore_whitespace()
            next_char = self.get_next_char()
            assert next_char == '<'
            next_tag_name = self.parse_html_tag_name()
            if next_tag_name == '/' + tag_name:
                self.get_str_until_char('>')  # delete this line
                self.get_next_char()     # delete this line, just for eat >
                return dom
            else:
                self.back_until_char('<')
                sub_node = self.parse_html_tag()
                dom.children.append(sub_node)
        return dom

    def parse_html_plain_text(self) -> str:
        return self.get_str_until_char('<')

    def get_str_until_str(self, end_str: str, escape: bool=False) -> str:
        result = ''
        while 1:
            result += self.get_str_until_char(end_str[0], escape=escape)
            next_n_char = self.get_next_n_chars(len(end_str))
            if next_n_char == end_str:
                self.backtrack(len(end_str))
                return result
            else:
                self.backtrack(len(end_str) - 1)
                result = self.get_next_char()
        return result

    def get_str_until_char(self, end_chars: str, escape: bool=False) -> str:
        def get_str_until_with_escape():
            result = ''
            pre_is_escape_char = False
            while 1:
                next_char = self.get_next_char()
                if next_char in end_chars and pre_is_escape_char is False:
                    break
                else:
                    result += next_char

                if next_char == '\\' and pre_is_escape_char is False:
                    pre_is_escape_char = True
                else:
                    pre_is_escape_char = False
            self.backtrack()
            return result

        def get_str_until_without_escape():
            result = ''
            while 1:
                next_char = self.get_next_char()
                if next_char in end_chars:
                    break
                else:
                    result += next_char
            self.backtrack()
            return result

        if escape:
            return get_str_until_with_escape()
        return get_str_until_without_escape()

    def parse_js_code(self) -> str:
        code = ''
        while 1:
            code += self.get_str_until_char(""""'/<""")
            next_char = self.get_next_char()
            if next_char in """'\"""":
                code += self.get_str_until_char(next_char)
                assert next_char == self.get_next_char()
            elif next_char == '/':
                next_next_char = self.get_next_char()
                if next_next_char == '/':  # // comment
                    code += self.get_str_until_char(self._linesep)
                    code += self.get_next_char()
                elif next_next_char == '*':  # /* comment
                    code += self.get_str_until_str('*/')
                    code += self.get_next_n_chars(2)
                else:  # div operator or regex expression
                    self.backtrack(2)  # we have consume 2 chars
                    position = self.get_parse_position()
                    self.back_until_char('(,=:[!&|?{};')
                    self.ignore_whitespace()
                    if '/' == self.get_next_char():
                        # regex expression
                        is_regex = True
                    else:
                        is_regex = False
                    self.set_parse_position(position)
                    assert '/' == self.get_next_char()
                    if is_regex:
                        regex = self.get_str_until_char('/', escape=True)
                        code += ('/' + regex + '/')
                        assert '/' == self.get_next_char()
                    else:
                        code += '/'
            elif next_char == '<':
                next_8_char = self.get_next_n_chars(8)
                if next_8_char == '/script>':
                    break
                else:
                    self.backtrack(8)
                    code += next_char
            else:
                raise RuntimeError('parse_js_code')
        return code

    def parse_style_code(self) -> str:
        result = ''
        while 1:
            result += self.get_str_until_char(""""<'/""")
            next_char = self.get_next_char()
            if next_char in '"\'':
                result += (next_char + self.get_str_until_char(next_char) + next_char)
                assert next_char == self.get_next_char()
            if next_char == '/':
                if self.get_next_char() == '*':
                    result += '/*' + self.get_str_until_str('*/') + '*/'
                    next_2_chars = self.get_next_n_chars(2)
                    assert next_2_chars == '*/'
                else:
                    self.backtrack()
                    result += next_char
            elif next_char == '<':
                next_7_chars = self.get_next_n_chars(7)
                assert next_7_chars == '/style>'
                break
        return result

    def parse_html_comment(self) -> str:
        """<!-- this is html comment -->
               ^                        ^
               parse from this char     end position
        """
        result = self.get_str_until_str('-->')
        next_3_chars = self.get_next_n_chars(3)
        assert next_3_chars == '-->'
        return result

    def ignore_whitespace(self) -> None:
        while 1:
            try:
                ch = self.get_next_char()
            except IndexError:
                break
            if not self.is_white_char(ch):
                break
        self.backtrack()

    def get_next_char(self) -> str:
        ch = self._code[self._parse_index]
        self._parse_index += 1
        return ch

    def get_next_n_chars(self, n: int=1) -> str:
        result = ''
        for i in range(n):
            result += self.get_next_char()
        return result

    def back_until_char(self, until_chars: str) -> None:
        self.backtrack()
        while 1:
            next_char = self.get_next_char()
            if next_char in until_chars:
                break
            else:
                self.backtrack(2)
        self.backtrack()

    def get_parse_position(self) -> int:
        return self._parse_index

    def set_parse_position(self, new_position: int) -> None:
        self._parse_index = new_position

    def backtrack(self, n: int=1) -> None:
        self._parse_index -= n

    def parse_end(self) -> bool:
        if self._parse_index < len(self._code) - 1:
            return False
        return True

    @staticmethod
    def is_white_char(char: str) -> bool:
        return char in string.whitespace
