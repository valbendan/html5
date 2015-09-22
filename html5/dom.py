from .constant import void_tag


__all__ = ['Dom']


class Dom:
    def __init__(self, tag_name: (str, None)) -> 'Dom':
        self._tag_name = tag_name
        # html5 sub children, str or Dom
        self.children = list()
        # html5 tag attributes
        # {str : str}
        self.attributes = dict()

    def name(self) -> str:
        return self._tag_name

    def __len__(self) -> int:
        return len(self.children)

    def __repr__(self) -> str:
        return self.build_html()

    def __str__(self) -> str:
        return self.build_html()

    def get_text(self, recursion: bool=True) -> str:
        text = ''
        for children in self.children:
            if isinstance(children, str) and self._tag_name not in ('script', 'style'):
                text += children
            elif isinstance(children, Dom) and recursion is True:
                text += children.get_text(recursion)
        return text

    def build_html(self) -> str:
        if self._tag_name in void_tag:
            return self._build_void_tag_html()

        if self._tag_name == '!--':
            return '<!--' + self.children[0] + '-->'

        body = self._build_children_html()

        if self._tag_name is None:
            html = '{body}'
            return html.format(body=body)
        else:
            attr = self._build_attribute()
            if attr:
                html = '<{tag_name} {tag_attributes}>{body}</{tag_name}>'
                return html.format(tag_name=self._tag_name, tag_attributes=attr, body=body)
            else:
                html = '<{tag_name}>{body}</{tag_name}>'
                return html.format(tag_name=self._tag_name, body=body)

    def find_tag(self, tag_name: str, include_self: bool=True) -> (None, 'Dom'):
        if self._tag_name == tag_name and include_self:
            return self

        for children in self.children:
            if isinstance(children, Dom):
                result = children.find_tag(tag_name, include_self=True)
                if result is not None:
                    return result
                    #else isinstance(children str) need not to process
        return None

    def find_children_tag(self, tag_name: str) -> (None, 'Dom'):
        return self.find_tag(tag_name, include_self=False)

    def xpath(self, path: str) -> (None, 'Dom'):
        parts = path.split('->')
        dom = self
        for part in parts:
            dom = dom.find_children_tag(part)
            if dom is None:
                return None
        return dom

    def find_all_tags(self, tag_name: str) -> ['Dom']:
        result = []
        if self._tag_name == tag_name:
            result.append(self)

        for children in self.children:
            if isinstance(children, Dom):
                result += children.find_all_tags(tag_name)

        return result

    def _build_attribute(self) -> str:
        attribute_list = list()
        for key in self.attributes:
            if self.attributes[key] is None:
                attribute_list.append(key)
            else:
                attribute_list.append("{key}={value}".format(key=key, value=self.attributes[key]))
        return ' '.join(attribute_list)

    def _build_void_tag_html(self) -> str:
        attr = self._build_attribute()
        if attr:
            html = '<{tag_name} {tag_attributes}>'
            return html.format(tag_name=self._tag_name, tag_attributes=attr)
        else:
            html = '<{tag_name}>'
            return html.format(tag_name=self._tag_name)

    def _build_children_html(self) -> str:
        html = ''
        for children in self.children:
            if isinstance(children, str):
                html += children
            elif isinstance(children, Dom):
                html += children.build_html()
            else:
                raise RuntimeError("unknown type")
        return html
