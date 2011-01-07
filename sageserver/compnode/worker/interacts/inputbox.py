from control import *

class InputBox(Control):
    """
    An input box.
    """
    __slots__ = ('default', 'label', 'type', 'width')
    js_class = "InputBox"

    def __init__(self, default=None, label=None, type=None, width=80):
        self.default = default
        self.label = label
        if type is None:
            type = eval
        self.type = type
        self.width = width

    def set_argname(self, argname):
        if self.label is None:
            self.label = argname

    def json_dict(self):
        return {
            'js_class': self.js_class,
            'default': repr(self.default),
            'label': self.label,
            'type': repr(self.type),
            'width': self.width,
        }

    def eval(self, json_obj):
        return self.type(json_obj.value)
