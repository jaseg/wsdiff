# MIT License
#
# Copyright (c) 2016 Alex Goodman
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import io
import os
import string
import html
import textwrap
import sys
import difflib
import argparse
import webbrowser
from collections import defaultdict
from pathlib import Path
import re
from itertools import groupby, chain

import pygments
from pygments.formatters import HtmlFormatter
from pygments.lexer import RegexLexer
from pygments import token


HTML_TEMPLATE = r'''
<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8">
        <title>$title</title>
        <meta name="description" content="">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta name="mobile-web-app-capable" content="yes">
<style>
html, body {
    margin: 0;
    padding: 0;
}

.file-container {
    font-family: monospace;
    font-size: 9pt;
    border: solid 1px #e0e0e0;
    margin: 15px;
}

.file-title {
    background-color: #f8f8f8;
    padding: 10px 20px;
    font-size: 10pt;
    font-weight: bold;
    border-bottom: 1px solid #e0e0e0;
    position: sticky;
    top: 0;
    z-index: 1;
}

.diff {
    overflow-x: auto;
    display: grid;
}

.line {
    padding-left: calc(4em + 5px);
    text-indent: -4em;
    padding-top: 2px;
}

.line.left.change, .line.left.insert {
    background-color: #fbe9eb;
}

.line.right.change, .line.right.insert {
    background-color: #ecfdf0;
}

.lineno.left.change, .lineno.left.insert {
    background-color: #f9d7dc;
    color: #ae969a;
}

.lineno.right.change, .lineno.right.insert {
    background-color: #ddfbe6;
    color: #9bb0a1;
}

.right > .word_change {
    background-color: #c7f0d2;
    color: #004000;
}

.left > .word_change {
    background-color: #fac5cd;
    color: #400000;
}

.lineno {
    word-break: keep-all;
    margin: 0;
    padding-left: 1em;
    padding-right: 5px;
    overflow: clip;
    position: relative;
    text-align: right;
    color: #a0a0a0;
    background-color: #f8f8f8;
    border-right: 1px solid #e0e0e0;
}

.lineno.change, .lineno.insert {
    color: #000000;
}

.lineno::before {
    position: absolute;
    right: 0;
    content: "\a↳\a↳\a↳\a↳\a↳\a↳\a↳\a↳\a↳\a↳\a↳\a↳\a↳\a↳\a↳\a↳\a↳\a↳";
    white-space: pre;
    color: #a0a0a0;
}

/* Unified diff for narrow screens (phones) */
@media screen and (max-width: 70em) {
    .diff {
        grid-auto-flow: dense;
        grid-template-columns: min-content min-content 1fr;
    }

    .lineno.left {
        grid-column: 1;
    }

    .lineno.left.change {
        grid-column: 1 / span 2;
    }

    .lineno.left.insert {
        grid-column: 1;
    }

    .lineno.right {
        grid-column: 2;
    }

    .lineno.right.change {
        grid-column: 1 / span 2;
    }

    .lineno.right.insert {
        grid-column: 2;
    }

    .line.left, .line.right.empty {
        display: none;
    }

    .line {
        grid-column: 3;
    }

    .line.left.insert {
        display: block;
    }

    .line.left.change {
        display: block;
    }

    .lineno.right.empty {
        background-color: #f9d7dc;
    }

    .lineno.left.empty {
        background-color: #ddfbe6;
    }

    /* line continuation arrows only in right line number column */
    .lineno.left::before {
        content: "";
    }
}

/* Split diff for wide screens (laptops) */
@media screen and not (max-width: 70em) {
    .diff {
        grid-template-columns: min-content 1fr min-content 1fr;
    }

    .empty {
        background-color: #f0f0f0;
    }

    /* line continuation arrows only in non-empty lines */
    .lineno.empty::before {
        content: "";
    }

    .lineno {
        padding-left: 30px;
    }
}
</style>
<style>
$pygments_css
</style>
    </head>
    <body>
$body
    </body>
</html>
'''

PYGMENTS_CSS = '''
body .hll { background-color: #ffffcc }
body  { background: #ffffff; }
body .c { color: #177500 } /* Comment */
body .err { color: #000000 } /* Error */
body .k { color: #A90D91 } /* Keyword */
body .l { color: #1C01CE } /* Literal */
body .n { color: #000000 } /* Name */
body .o { color: #000000 } /* Operator */
body .cm { color: #177500 } /* Comment.Multiline */
body .cp { color: #633820 } /* Comment.Preproc */
body .c1 { color: #177500 } /* Comment.Single */
body .cs { color: #177500 } /* Comment.Special */
body .kc { color: #A90D91 } /* Keyword.Constant */
body .kd { color: #A90D91 } /* Keyword.Declaration */
body .kn { color: #A90D91 } /* Keyword.Namespace */
body .kp { color: #A90D91 } /* Keyword.Pseudo */
body .kr { color: #A90D91 } /* Keyword.Reserved */
body .kt { color: #A90D91 } /* Keyword.Type */
body .ld { color: #1C01CE } /* Literal.Date */
body .m { color: #1C01CE } /* Literal.Number */
body .s { color: #C41A16 } /* Literal.String */
body .na { color: #836C28 } /* Name.Attribute */
body .nb { color: #A90D91 } /* Name.Builtin */
body .nc { color: #3F6E75 } /* Name.Class */
body .no { color: #000000 } /* Name.Constant */
body .nd { color: #000000 } /* Name.Decorator */
body .ni { color: #000000 } /* Name.Entity */
body .ne { color: #000000 } /* Name.Exception */
body .nf { color: #000000 } /* Name.Function */
body .nl { color: #000000 } /* Name.Label */
body .nn { color: #000000 } /* Name.Namespace */
body .nx { color: #000000 } /* Name.Other */
body .py { color: #000000 } /* Name.Property */
body .nt { color: #000000 } /* Name.Tag */
body .nv { color: #000000 } /* Name.Variable */
body .ow { color: #000000 } /* Operator.Word */
body .mb { color: #1C01CE } /* Literal.Number.Bin */
body .mf { color: #1C01CE } /* Literal.Number.Float */
body .mh { color: #1C01CE } /* Literal.Number.Hex */
body .mi { color: #1C01CE } /* Literal.Number.Integer */
body .mo { color: #1C01CE } /* Literal.Number.Oct */
body .sb { color: #C41A16 } /* Literal.String.Backtick */
body .sc { color: #2300CE } /* Literal.String.Char */
body .sd { color: #C41A16 } /* Literal.String.Doc */
body .s2 { color: #C41A16 } /* Literal.String.Double */
body .se { color: #C41A16 } /* Literal.String.Escape */
body .sh { color: #C41A16 } /* Literal.String.Heredoc */
body .si { color: #C41A16 } /* Literal.String.Interpol */
body .sx { color: #C41A16 } /* Literal.String.Other */
body .sr { color: #C41A16 } /* Literal.String.Regex */
body .s1 { color: #C41A16 } /* Literal.String.Single */
body .ss { color: #C41A16 } /* Literal.String.Symbol */
body .bp { color: #5B269A } /* Name.Builtin.Pseudo */
body .vc { color: #000000 } /* Name.Variable.Class */
body .vg { color: #000000 } /* Name.Variable.Global */
body .vi { color: #000000 } /* Name.Variable.Instance */
body .il { color: #1C01CE } /* Literal.Number.Integer.Long */

/* 
These styles are used to highlight each diff line.
Note: for partial like highlight change to "display:block-inline" 
*/
span.left_diff_change {
  background-color: #FFE5B5;
  display: block
}
span.left_diff_add {
  background-color: #eeeeee;
  display: block
}
span.left_diff_del {
  background-color: #ffdddd;
  display: block
}
span.lineno_q {
  display: block;
}
span.right_diff_change {
  background-color: #FFE5B5;
  display: block
}
span.right_diff_add {
  background-color: #ddffdd;
  display: block
}
span.right_diff_del {
  background-color: #eeeeee;
  display: block
}
span.clearbg {
  background-color: transparent;
}
'''

class SexprLexer(RegexLexer):
    name = 'KiCad S-Expression'
    aliases = ['sexp']
    filenames = ['*.kicad_mod', '*.kicad_sym']

    tokens = {
        'root': [
            (r'\s+', token.Whitespace),
            (r'[()]', token.Punctuation),
            (r'([+-]?\d+\.\d+)(?=[)\s])', token.Number),
            (r'(-?\d+)(?=[)\s])', token.Number),
            (r'"((?:[^"]|\\")*)"(?=[)\s])', token.String),
            (r'([^()"\s]+)(?=[)\s])', token.Name),
        ]
    }

from pygments.formatter import Formatter
from pygments.token import STANDARD_TYPES

from functools import lru_cache

@lru_cache(maxsize=256)
def get_token_class(ttype):
    while not (name := STANDARD_TYPES.get(ttype)): 
        ttype = ttype.parent
    return name

def iter_token_lines(tokensource):
    lineno = 1
    for ttype, value in tokensource:
        left, newline, right = value.partition('\n')
        while newline:
            yield lineno, ttype, left
            lineno += 1
            left, newline, right = right.partition('\n')
        if left != '':
            yield lineno, ttype, left

class RecordFormatter(Formatter):
    def __init__(self, side, diff):
        self.side = side
        if side == 'right':
            diff = [(right, left, change) for left, right, change in diff]
        self.diff = diff

    def format(self, tokensource, outfile):
        diff = iter(self.diff)
        self.lines = []
        for lineno, tokens in groupby(iter_token_lines(tokensource), key=lambda arg: arg[0]):

            for (lineno_ours, diff_ours), (lineno_theirs, _diff_theirs), change in diff:
                if lineno_ours == lineno:
                    break
                else:
                    self.lines.append(f'<span class="lineno {self.side} empty"></span><span class="line {self.side} empty"></span>')
            assert lineno_ours == lineno

            if not change:
                change_class = '' 
            elif not lineno_ours or not lineno_theirs:
                change_class = ' insert'
            else:
                change_class = ' change' 

            line = f'<span class="lineno {self.side}{change_class}">{lineno}</span><span class="line {self.side}{change_class}">'

            parts = re.split(r'(\00.|\01|$)', diff_ours)
            source_pos = 0
            diff_markers = []
            if lineno_theirs: # Do not highlight word changes if the whole line got added or removed.
                for span, sep in zip(parts[0:-2:2], parts[1:-2:2]):
                    source_pos += len(span)
                    diff_markers.append((source_pos, sep))

            diff_class = ''
            source_pos = 0
            for _lineno, ttype, value in tokens:
                css_class = get_token_class(ttype)

                while diff_markers:
                    next_marker_pos, next_marker_type = diff_markers[0]
                    if source_pos <= next_marker_pos < source_pos + len(value):
                        split_pos = next_marker_pos - source_pos
                        left, value = value[:split_pos], value[split_pos:]
                        line += f'<span class="{css_class}{diff_class}">{html.escape(left)}</span>'
                        source_pos += len(left)
                        diff_class = ' word_change' if next_marker_type.startswith('\0') else ''
                        diff_markers = diff_markers[1:]
                    else:
                        break
                line += f'<span class="{css_class}{diff_class}">{html.escape(value)}</span>'
                source_pos += len(value)

            if css_class is not None:
                line += '</span>'

            line += '</span>'
            self.lines.append(line)

        for _ours_empty, (lineno_theirs, _diff_theirs), change in diff:
            self.lines.append(f'<span class="lineno {self.side} empty"></span><span class="line {self.side} empty"></span>')
            assert change and lineno_theirs

def html_diff_content(old, new):
    diff = list(difflib._mdiff(old.splitlines(), new.splitlines()))

    fmt_l = RecordFormatter('left', diff)
    pygments.highlight(old, SexprLexer(), fmt_l)

    fmt_r = RecordFormatter('right', diff)
    pygments.highlight(new, SexprLexer(), fmt_r)

    return '\n'.join(chain.from_iterable(zip(fmt_l.lines, fmt_r.lines)))

def html_diff_block(old, new, filename):
    code = html_diff_content(old, new)
    return textwrap.dedent(f'''<div class="file-container">
            <div class="file-title">{filename}</div>
            <div class="diff">
                {code}
            </div>
        </div>''')


if __name__ == "__main__":
    description = """Given two source files or directories this application\
creates an html page which highlights the differences between the two. """

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-b', '--open', action='store_true', help='Open output file in a browser')
    parser.add_argument('-s', '--syntax-css', help='Path to custom Pygments CSS file for code syntax highlighting')
    parser.add_argument('-t', '--pagetitle', help='Override page title of output HTML file')
    parser.add_argument('-o', '--output', default=sys.stdout, type=argparse.FileType('w'), help='Name of output file (default: stdout)')
    parser.add_argument('--header', action='store_true', help='Only output HTML header with stylesheets and stuff, and no diff')
    parser.add_argument('--content', action='store_true', help='Only output HTML content, without header')
    parser.add_argument('old', help='source file or directory to compare ("before" file)')
    parser.add_argument('new', help='source file or directory to compare ("after" file)')
    args = parser.parse_args()

    if args.open and args.output == sys.stdout:
        print('Error: --open requires --output to be given.')
        parser.print_usage()
        sys.exit(2)

    old, new = Path(args.old), Path(args.new)
    if not old.exists():
        print(f'Error: Path "{old}" does not exist.')
        sys.exit(1)

    if not new.exists():
        print(f'Error: Path "{new}" does not exist.')
        sys.exit(1)

    if old.is_file() != new.is_file():
        print(f'Error: You must give either two files, or two paths to compare, not a mix of both.')
        sys.exit(1)

    if old.is_file():
        found_files = {str(new): (old, new)}
    else:
        found_files = defaultdict(lambda: [None, None])
        for fn in old.glob('**/*'):
            found_files[str(fn.relative_to(old))][0] = fn
        for fn in new.glob('**/*'):
            found_files[str(fn.relative_to(new))][1] = fn

    pagetitle = args.pagetitle or f'diff: {old} / {new}'
    if args.syntax_css:
        syntax_css = Path(args.syntax_css).read_text()
    else:
        syntax_css = PYGMENTS_CSS

    diff_blocks = []
    for suffix, (old, new) in sorted(found_files.items()):
        old = '' if old is None else old.read_text()
        new = '' if new is None else new.read_text()

        diff_blocks.append(html_diff_block(old, new, suffix))

    print(string.Template(HTML_TEMPLATE).substitute(
        title=pagetitle,
        pygments_css=syntax_css,
        body='\n'.join(diff_blocks)), file=args.output)

    if args.open:
        webbrowser.open('file://' + str(Path(args.output.name).absolute()))

