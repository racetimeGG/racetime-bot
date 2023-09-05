"""
These classes help you build up actions to attach to chat messages.

An action button will give a user a quick way to send a particular message that
your bot can then act on. Think of it like a shortcut to using the text
commands.

Actions can optionally include a Survey, which allows you to customise what
message is sent by first giving the user a small form to fill in. The answers
will then be interpolated into the action message.
"""
class Action:
    """
    An action button.

    `label` (required) - this is what appears on the button
    `message` (required) - what message the user will send when they click this button.
                           Use interpolation to include survey answers, e.g. "!seed ${preset}"
    `submit` (optional) - when using a survey, this text appears on the submit button
    `survey` (optional) - should be a Survey instance
    `help_text` (optional) - title text that appears when user hovers on the button
    """
    def __init__(self, label, message, submit=None, survey=None, help_text=None):
        self.label = label
        self.data = {
            'message': message,
        }
        if submit:
            self.data['submit'] = submit
        if survey:
            self.data['survey'] = survey.data
        if help_text:
            self.data['help'] = help_text

class ActionLink:
    """
    An action link.

    `label` (required) - this is what appears on the button
    `url` (required) - where the button links to
    `help_text` (optional) - title text that appears when user hovers on the button

    Note that link actions cannot use surveys.
    """
    def __init__(self, label, url, help_text=None):
        self.label = label
        self.data = {
            'url': url,
        }
        if help_text:
            self.data['help'] = help_text


class Survey:
    """
    `questions` should be Question instances
    """
    def __init__(self, *questions):
        self.data = [
            question.data for question in questions
        ]


class Question:
    """
    Abstract Question class. Use one of the Input classes for actual surveys.

    All questions have the following parameters:

    `name` (required) - used to identify the value when sending the message
    `label` (required) - friendly name of the field the user sees
    `default` (optional) - Default value for the field
    `help_text` (optional) - Extra text that appears below the field
    """
    def __init__(self, name, label, help_text=None, default=None, **kwargs):
        self.data = {
            'name': name,
            'label': label,
            **kwargs,
        }
        if default:
            self.data['default'] = default
        if help_text:
            self.data['help'] = help_text


class TextInput(Question):
    """
    A free-text field.

    In addition to the parameters listed above, a TextInput also has:

    `placeholder` (optional) - Placeholder text for the field
    """
    def __init__(self, name, label, placeholder=None,
                 help_text=None, default=None):
        super().__init__(name, label, help_text, default, type='input', placeholder=placeholder)


class BoolInput(Question):
    """
    A checkbox button.

    BoolInput has no additional parameters.

    Note that `default`.
    """
    def __init__(self, name, label, help_text=None, default=None):
        super().__init__(name, label, help_text, default, type='bool')


class RadioInput(Question):
    """
    A set of radio buttons.

    In addition to the parameters listed above, a RadioInput also has:

    `options` (required) - A dict of {value: label} pairs

    Note that if `default` is used, its value should match a value from `options`, not a label.
    """
    def __init__(self, name, label, options,
                 help_text=None, default=None):
        super().__init__(name, label, help_text, default, options=options, type='radio')


class SelectInput(Question):
    """
    A drop-down select box.

    In addition to the parameters listed above, a SelectInput also has:

    `options` (required) - A dict of {value: label} pairs

    Note that if `default` is used, its value should match a value from `options`, not a label.
    """
    def __init__(self, name, label, options,
                 help_text=None, default=None):
        super().__init__(name, label, help_text, default, options=options, type='select')
