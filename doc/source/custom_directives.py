# -*- coding: utf-8 -*-
from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.parsers.rst import directives
import os
import re
from hashlib import sha1
from sphinx.ext.autodoc import AutodocReporter

try:
    from gen_example import render_snippet
except ImportError:
    render_snippet = None


VISUAL_EXAMPLES_DIR = "visual_examples"

# todo: maybe should be more generic from sphinx conf
SOURCE_DIR = os.path.join(os.path.dirname(__file__))


def flag(argument):
    """Reimplement directives.flag to return True instead of None
    Check for a valid flag option (no argument) and return ``None``.
    (Directive option conversion function.)

    Raise ``ValueError`` if an argument is found.
    """
    if argument and argument.strip():
        raise ValueError('no argument is allowed; "%s" supplied' % argument)
    else:
        return True


def nonnegative_int_list(argument):
    if ',' in argument:
        entries = argument.split(',')
    else:
        entries = argument.split()
    return [directives.nonnegative_int(entry) for entry in entries]


def click_list(argument):
    value = nonnegative_int_list(argument)

    if len(value) != 2:
        ValueError("argument must contain 3 non-negative values")

    return value


class WrapsDirective(Directive):
    has_content = True

    def run(self):
        head = nodes.paragraph()
        head.append(nodes.inline("Wraps API:", "Wraps API: "))

        source = '\n'.join(self.content.data)
        literal_node = nodes.literal_block(source, source)
        literal_node['laguage'] = 'C++'

        return [head, literal_node]


class VisualDirective(Directive):
    has_content = True

    final_argument_whitespace = True
    option_spec = {
        'title': directives.unchanged,
        'width': directives.positive_int,
        'height': directives.positive_int,
        'auto_window': flag,
        'auto_layout': flag,
        'animated': flag,
        'click': click_list,
    }

    def run(self):
        source = '\n'.join(self.content.data)
        literal = nodes.literal_block(source, source)
        literal['language'] = 'python'

        # docutils document model is insane!
        head1 = nodes.paragraph()
        head1.append(nodes.inline("Example:", "Example: "))

        head2 = nodes.paragraph()
        head2.append(
            nodes.section("foo", nodes.inline("Outputs:", "Outputs: "))
        )

        directive_nodes = [
            head1,
            literal,
            head2,
            self.get_image_node(source)
        ]

        return directive_nodes

    def name_source_snippet(self, source, animated=False):
        env = self.state.document.settings.env

        if (
            isinstance(self.state.reporter, AutodocReporter) and
            self.state.parent and self.state.parent.parent
        ):
            # If it is generated by autodoc then autogenerate title from
            # the function/method/class signature
            # note: hacky assumption that this is a signature node
            signature_node = self.state.parent.parent.children[0]
            signature = signature_node['names'][0]
            occurence = env.new_serialno(signature)

            name = signature + '_' + str(occurence)
        else:
            # If we could not quess then use explicit title or hexdigest
            name = self.options.get('title', sha1(source).hexdigest())

        return self.phrase_to_filename(name, animated)

    def phrase_to_filename(self, phrase, animated=False):
        """Convert phrase to normilized file name."""
        # remove non-word characters
        name = re.sub(r"[^\w\s\.]", '', phrase.strip().lower())
        # replace whitespace with underscores
        name = re.sub(r"\s+", '_', name)

        return name + ('.gif' if animated else '.png')

    def get_image_node(self, source):
        file_name = self.name_source_snippet(
            source, animated=self.check_flag('animated')
        )
        file_path = os.path.join(VISUAL_EXAMPLES_DIR, file_name)

        env = self.state.document.settings.env

        if render_snippet and env.config['render_examples']:
            try:
                render_snippet(
                    source, file_path,
                    output_dir=SOURCE_DIR, **self.options
                )
            except:
                print("problematic code:\n%s" % source)
                raise

        img = nodes.image()
        img['uri'] = "/" + file_path
        return img

    def check_flag(self, flag_name):
        if flag_name not in self.option_spec:
            raise TypeError('[{}] is not allowed as flag')

        return flag_name in self.options


def setup(app):
    app.add_config_value('render_examples', False, 'html')
    app.add_directive('wraps', WrapsDirective)
    app.add_directive('visual-example', VisualDirective)

    return {'version': '0.1'}
