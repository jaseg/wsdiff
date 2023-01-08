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
from pygments.lexers import get_lexer_by_name, guess_lexer_for_filename, get_all_lexers, LEXERS
from pygments import token

DIFF_STYLE_TOGGLE = r'''
    <div id="js-controls">
        <div class="single-control">
            <span class="control-label">Split view</span>
            <span class="three-way-toggle">
                <div class="field-group">
                    <div class="field"><input type="checkbox" id="toggle-split-auto" checked></input><label for="toggle-split-auto">Auto</label></div>
                    <div class="field"><input type="checkbox" id="toggle-split-force" disabled></input><label for="toggle-split-force">Split view</label></div>
                </div>
            </span>
        </div>
    </div>
'''

MAIN_CSS = r'''
@layer base-style {
    html, body {
        margin: 0;
        padding: 0;
        font-family: sans-serif;
    }

    #js-controls {
        display: none;
        background-color: #f8f8f8;
        padding: 5px 20px;
        font-size: 10pt;
        font-weight: bold;
        border: 1px solid #e0e0e0;
        position: sticky;
        top: 0;
        z-index: 1;
        flex-direction: row-reverse;
    }

    @media screen and (max-width: 40em) {
        #js-controls {
            position: initial;
        }

        .diff {
            border-top: none;
        }

        .file-title {
            background-color: #f8f8f8;
            border-bottom: solid 1px #e0e0e0;
        }
    }

    input[type="checkbox"] {
        width: 20px;
        height: 20px;
    }

    input, label, .control-label {
        vertical-align: middle;
    }

    .field-group {
        display: inline-block;
    }

    .field {
        white-space: nowrap;
        display: inline-block;
    }

    label {
        font-weight: normal;
        margin-right: .5em;
        margin-left: 5px;
    }

    .control-label {
        margin-right: .5em;
        margin-left: 5px;
        padding-bottom: 3px;
    }

    .file-container {
        font-family: monospace;
        font-size: 9pt;
        background-color: #f8f8f8;
        border: solid 1px #e0e0e0;
        margin: 15px;
    }

    .file-title {
        padding: 10px 20px;
        font-size: 10pt;
        font-weight: bold;
        position: sticky;
        top: 0;
        z-index: 1;
        display: flex;
    }
    
    .filename {
        max-width: 30em;
        text-overflow: ellipsis;
        overflow: hidden;
        white-space: nowrap;
        direction: rtl;
    }

    .diff {
        overflow-x: auto;
        display: grid;
        align-items: start;
        border-top: 1px solid #e0e0e0;
    }

    .line {
        padding-left: calc(4em + 5px);
        text-indent: -4em;
        padding-top: 2px;
    }

    /* Make individual syntax tokens wrap anywhere */
    .line > span {
        overflow-wrap: anywhere;
        white-space: pre-wrap;
    }

    .line { 
        min-width: 15em;
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
        padding-left: 30px;
        padding-right: 5px;
        overflow: clip;
        position: relative;
        text-align: right;
        color: #a0a0a0;
        background-color: #f8f8f8;
        border-right: 1px solid #e0e0e0;
        align-self: stretch;
    }

    .lineno.change, .lineno.insert {
        color: #000000;
    }

    .lineno::after {
        position: absolute;
        right: 0;
        content: "\a↳\a↳\a↳\a↳\a↳\a↳\a↳\a↳\a↳\a↳\a↳\a↳\a↳\a↳\a↳\a↳\a↳\a↳";
        white-space: pre;
        color: #a0a0a0;
    }

    /* Default rules for split diff for wide screens (laptops) */
    .diff {
        grid-template-columns: min-content 1fr min-content 1fr;
    }

    .empty {
        background-color: #f0f0f0;
        align-self: stretch;
    }

    /* line continuation arrows only in non-empty lines */
    .lineno.empty::after {
        content: "";
    }
}

@layer automatic-media-rule {
    /* Unified diff for narrow screens (phones) */
    @media screen and (max-width: 70em) {
        .diff {
            grid-auto-flow: dense;
            grid-template-columns: min-content min-content 1fr;
        }

        .lineno {
            padding-left: 1em;
        }

        .lineno.left {
            grid-column: 1;
        }

        .lineno.left.change, .lineno.right.change {
            grid-column: 1 / span 2;
            display: grid;
            grid-template-columns: 1fr 1fr;
            padding-left: 0;
            padding-right: 0;
            grid-auto-flow: dense;
            /* To make alignment of left line number work, since we loose margin and padding control using ::before. */
            column-gap: 10px;
        }

        .lineno.right.change::before {
            content: "";
            align-self: stretch;
            grid-column: 1;
            border-right: 1px solid #e0e0e0;
            margin-right: -6px; /* move border into column gap, and 1px over to align with other borders */
        }

        .lineno.left.change::before {
            content: "";
            align-self: stretch;
            grid-column: 2;
            border-left: 1px solid #e0c8c8; /* pick a darker border color inside the light red gutter */
            margin-left: -5px;
        }
        
        .lineno.left.insert {
            border-right: 1px solid #e0c8c8;
        }

        .lineno.right.change::after {
            grid-column: 2;
        }

        .lineno.left.insert {
            grid-column: 1 / span 2;
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-auto-flow: dense;
            column-gap: 10px;
            padding-left: 0;
            padding-right: 0;
        }

        .lineno.right {
            grid-column: 2;
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
            display: none;
        }

        .lineno.left.empty {
            background-color: #ddfbe6;
        }

        /* line continuation arrows only in right line number column */
        .lineno.left.insert::after {
        }

        .lineno.left.insert::before {
            content: "";
            grid-column: 2;
            border-left: 1px solid #e0c8c8; /* pick a darker border color inside the light red gutter */
            margin-left: -5px;
        }
    }
}
'''

DIFF_STYLE_SCRIPT = r'''
    const findStylesheet = (id => Array.from(document.styleSheets).find(element => element.ownerNode && element.ownerNode.id == id));
    const findRule = ((stylesheet, name) => Array.from(stylesheet.cssRules).find(
                    element => (element instanceof CSSLayerBlockRule && element.name == name)).cssRules[0]);

    const automaticMediaElement = findRule(findStylesheet('main-style'), 'automatic-media-rule');
    const automaticMediaRule = automaticMediaElement.media[0];
    const impossibleMediaRule = "screen and (max-width: 0px)";
    const tautologicalMediaRule = "screen and (min-width: 0px)";

    const toggleAuto = document.getElementById("toggle-split-auto");
    const toggleForce = document.getElementById("toggle-split-force");
    toggleAuto.checked = true;
    toggleForce.disabled = true;

    toggleAuto.addEventListener('change', (event) => {
        const automatic = toggleAuto.checked;
        toggleForce.disabled = automatic;
        if (automatic) {
            automaticMediaElement.media.deleteMedium(automaticMediaElement.media[0]);
            automaticMediaElement.media.appendMedium(automaticMediaRule);
        } else {
            automaticMediaElement.media.deleteMedium(automaticMediaRule);
            if (toggleForce.checked) {
                automaticMediaElement.media.appendMedium(impossibleMediaRule);
            } else {
                automaticMediaElement.media.appendMedium(tautologicalMediaRule);
            }
        }
    });

    toggleForce.addEventListener('change', (event) => {
        const automatic = toggleAuto.checked;
        if (!automatic) {
            automaticMediaElement.media.deleteMedium(automaticMediaElement.media[0]);
            if (toggleForce.checked) {
                automaticMediaElement.media.appendMedium(impossibleMediaRule);
            } else {
                automaticMediaElement.media.appendMedium(tautologicalMediaRule);
            }
        }
    });

    const mediaMatch = window.matchMedia(automaticMediaRule);
    mediaMatch.addEventListener('change', (event) => {
        const automatic = toggleAuto.checked;
        if (automatic) {
            toggleForce.checked = !event.matches;
        }
    });
    toggleForce.checked = !mediaMatch.matches;

    document.getElementById('js-controls').style = 'display: flex';
'''

HTML_TEMPLATE = r'''
<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8">
        <title>$title</title>
        <meta name="description" content="">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta name="mobile-web-app-capable" content="yes">
        <style id="main-style">
            $main_css
        </style>
        <style>
            $pygments_css
        </style>
    </head>
    <body>
        $diff_style_toggle
        <script>
            $diff_style_script
        </script>
        <div class="diff-files">
            $body
        </div>
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

from pygments.formatter import Formatter
from pygments.token import STANDARD_TYPES

from functools import lru_cache

@lru_cache(maxsize=256)
def get_token_class(ttype):
    while not (name := STANDARD_TYPES.get(ttype)): 
        if ttype is token.Token:
            return 'n'
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

def html_diff_content(old, new, lexer):
    diff = list(difflib._mdiff(old.splitlines(), new.splitlines()))

    fmt_l = RecordFormatter('left', diff)
    pygments.highlight(old, lexer, fmt_l)

    fmt_r = RecordFormatter('right', diff)
    pygments.highlight(new, lexer, fmt_r)

    return '\n'.join(chain.from_iterable(zip(fmt_l.lines, fmt_r.lines)))

def html_diff_block(old, new, filename, lexer, hide_filename=True):
    code = html_diff_content(old, new, lexer)
    filename = f'<div class="file-title"><div class="filename">&#x202D;{filename}</div></div>'
    if hide_filename:
        filename = ''
    return textwrap.dedent(f'''<div class="file-container">
            {filename}
            <div class="diff">
                {code}
            </div>
        </div>''')


def cli():
    parser = argparse.ArgumentParser(description="Given two source files or directories this application creates an html page that highlights the differences between the two.")
    parser.add_argument('-b', '--open', action='store_true', help='Open output file in a browser')
    parser.add_argument('-s', '--syntax-css', help='Path to custom Pygments CSS file for code syntax highlighting')
    parser.add_argument('-l', '--lexer', help='Manually select pygments lexer (default: guess from filename, use -L to list available lexers.)')
    parser.add_argument('-L', '--list-lexers', action='store_true', help='List available lexers for -l/--lexer')
    parser.add_argument('-t', '--pagetitle', help='Override page title of output HTML file')
    parser.add_argument('-o', '--output', default=sys.stdout, type=argparse.FileType('w'), help='Name of output file (default: stdout)')
    parser.add_argument('--header', action='store_true', help='Only output HTML header with stylesheets and stuff, and no diff')
    parser.add_argument('--content', action='store_true', help='Only output HTML content, without header')
    parser.add_argument('--nofilename', action='store_true', help='Do not output file name headers')
    parser.add_argument('old', nargs='?', help='source file or directory to compare ("before" file)')
    parser.add_argument('new', nargs='?', help='source file or directory to compare ("after" file)')
    args = parser.parse_args()

    if args.list_lexers:
        for longname, aliases, filename_patterns, _mimetypes in get_all_lexers():
            print(f'{longname:<20} alias {"/".join(aliases)} for {", ".join(filename_patterns)}')
        sys.exit(0)

    if args.pagetitle or (args.old and args.new):
        pagetitle = args.pagetitle or f'diff: {args.old} / {args.new}'
    else:
        pagetitle = 'diff'

    if args.syntax_css:
        syntax_css = Path(args.syntax_css).read_text()
    else:
        syntax_css = PYGMENTS_CSS

    if args.header:
        print(string.Template(HTML_TEMPLATE).substitute(
            title=pagetitle,
            pygments_css=syntax_css,
            main_css=MAIN_CSS,
            diff_style_toggle=DIFF_STYLE_TOGGLE,
            diff_style_script=DIFF_STYLE_SCRIPT,
            body='$body'), file=args.output)
        sys.exit(0)

    if not (args.old and args.new):
        print('Error: The command line arguments "old" and "new" are required.', file=sys.stderr)
        parser.print_usage()
        sys.exit(2)

    if args.open and args.output == sys.stdout:
        print('Error: --open requires --output to be given.', file=sys.stderr)
        parser.print_usage()
        sys.exit(2)

    old, new = Path(args.old), Path(args.new)
    if not old.exists():
        print(f'Error: Path "{old}" does not exist.', file=sys.stderr)
        sys.exit(1)

    if not new.exists():
        print(f'Error: Path "{new}" does not exist.', file=sys.stderr)
        sys.exit(1)

    if old.is_file() != new.is_file():
        print(f'Error: You must give either two files, or two paths to compare, not a mix of both.', file=sys.stderr)
        sys.exit(1)

    if old.is_file():
        found_files = {str(new): (old, new)}
    else:
        found_files = defaultdict(lambda: [None, None])
        for fn in old.glob('**/*'):
            found_files[str(fn.relative_to(old))][0] = fn
        for fn in new.glob('**/*'):
            found_files[str(fn.relative_to(new))][1] = fn

    diff_blocks = []
    for suffix, (old, new) in sorted(found_files.items()):
        old_text = '' if old is None else old.read_text()
        new_text = '' if new is None else new.read_text()

        if args.lexer:
            lexer = get_lexer_by_name(lexer)
        else:
            try:
                lexer = guess_lexer_for_filename(new, new_text)
            except:
                lexer = get_lexer_by_name('text')

        diff_blocks.append(html_diff_block(old_text, new_text, suffix, lexer, hide_filename=args.nofilename))
    body = '\n'.join(diff_blocks)

    if args.content:
        print(body, file=args.output)
    else:
        print(string.Template(HTML_TEMPLATE).substitute(
            title=pagetitle,
            pygments_css=syntax_css,
            main_css=MAIN_CSS,
            diff_style_toggle=DIFF_STYLE_TOGGLE,
            diff_style_script=DIFF_STYLE_SCRIPT,
            body=body), file=args.output)

    if args.open:
        webbrowser.open('file://' + str(Path(args.output.name).absolute()))

if __name__ == "__main__":
    cli()
