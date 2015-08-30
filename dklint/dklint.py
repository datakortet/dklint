# -*- coding: utf-8 -*-
"""Run pylint and produce a Botstrappified report.
"""
import sys
import os
import re
import json
from subprocess import Popen, PIPE
import textwrap
from dklint.pfind import pfind
from collections import defaultdict

RCFILE = os.path.join(os.path.dirname(__file__), 'dklint.rc')
if sys.platform == 'win32':
    PYLINT = os.path.join(sys.prefix, 'Scripts', 'pylint.exe')
else:
    PYLINT = os.path.join(sys.prefix, 'bin', 'pylint')


# substitutions
subst = r"""

<html>:
    <html>
    <head>
        <link href="http://netdna.bootstrapcdn.com/bootstrap/3.1.0/css/bootstrap.min.css" rel="stylesheet">
        <link href="http://netdna.bootstrapcdn.com/bootstrap/3.1.0/css/bootstrap-theme.min.css" rel="stylesheet">
        <style>
            td.pre { font: 10px/11px monospace; white-space: pre; }
            a.toplink { font: 11px/10px monospace; position:relative; right: -3ex; }
            table td,
            table th { text-align: center; }
            table td:first-child,
            table th:first-child  { text-align: right; font-weight: bold; }
            table th:first-child  { width: 20%; }
            #messages + table td { font: 11px/12px monospace; white-space: pre; text-align: left; }
        </style>
        <script src="http://static.datakortet.no/dk/dk.js"></script>
        <script>
        dk.ready(function () {
            var toc = $('#toc > ul');
            $(':header').each(function () {
                toc.append($('<li/>').append($('<a/>', {
                    href: '#' + $(this).prop('id')
                }).text($(this).text())));
                $(this).append('<a class="toplink" href="#top">[top]</a>');
            });
        });
        </script>
    </head>

<body>\s*<div>:
    <body>
    <div class="container">
    <div id="toc">
        <h1>Contents:</h1>
        <ul></ul>
    </div>

<h2>(.*?)</h2>:
    <h2 id="$dashify{\1}">\1</h2>

<table>:
    <table class="table table-bordered table-striped table-hover table-condensed">

<tr class="header">:
    <thead>
    <tr class="header">

</th>\s*</tr>\s*<tr class="even">:
    </th>
    </thead>
    <tbody>
    <tr>

</td>\s*<td>:
    </td><td>

</table>:
    </tbody>
    </table>

<td>Similar lines:
    <td class="pre">Similar lines

Your code has been rated at (\d+\.\d+):
    Your code has been rated at $reportgrade{\1}

graph has been written to ([-\w]*\.svg):
    $includesvg{\1}

<tr class="even">:
    <tr>

<tr class="odd">:
    <tr>
    
"""
#"  emacs got confused..


def parse_rule(r):
    """Parse the rule into match text/regex and result text.
    """
    src, dst = r.split(':\n')
    return src, textwrap.dedent(dst)


def parse_subst(subst):
    """Split `subst` on double newline, and parse the chunks into rules.
    """
    ruletxts = [rule.strip() for rule in subst.split('\n\n') if rule.strip()]
    return [parse_rule(r) for r in ruletxts]


def dklint(target):
    """Call pylint, return result as a string.
    """
    _args = [PYLINT, '--rcfile=' + RCFILE, '-fhtml', target]
    pipe = Popen(_args, stdout=PIPE)
    output = pipe.communicate()[0]
    return output.replace('\r\n', '\n')


def write_stats(*args):
    txt = ' '.join([str(a) for a in args])
    with open('pylint_stats.py', 'a') as fp:
        print >>fp, txt
    return txt
        

def reportgrade(gradestr):
    """Called from substitutions
    """
    return write_stats("rating =", gradestr)


def dashify(s):
    """Called from substitutions
    """
    clean = ''.join([c for c in s.lower() if c == ' ' or 'a' <= c <= 'z'])
    return clean.replace(' ', '-').strip('-').replace('--', '-')


def includesvg(fname):
    """Called from substitutions
    """
    return '<svg' + open(fname).read().split('<svg')[1]


def editfn(m):
    fn, arg = m.groups()
    return eval(fn)(arg)


def indent(txt):
    # magic  to get indentation to be more useful..
    isize = {
        'table': 1,
        'thead': 1,
        'tbody': 2,
        'tr': 2,
        'td': 3,
        'th': 3,
    }

    def _indent(n):
        return '    ' * n

    for item, i in isize.items():
        txt = txt.replace('\n<' + item, '\n' + _indent(i) + '<' + item)
        txt = txt.replace('\n</' + item, '\n' + _indent(i) + '</' + item)

    return txt


def replace(rules, txt):
    """Run the `rules` on `txt`.
    """
    open('original.html', 'w').write(txt)  # save the original report
    for src, dst in rules:
        txt = re.sub(src, dst, txt)
    txt = re.sub(r'\$(.*?){(.*?)}', editfn, txt)
    return indent(txt.replace('\r', '').replace('\n\n', '\n'))


def project_dir():
    """A project dir contains `setup.py`.
    """
    setup_py = pfind('.', 'setup.py')
    if setup_py is None:
        raise RuntimeError("You must start dklint from within a project.")
    projdir = os.path.split(setup_py)[0]
    return projdir


def make_build_lint(projdir):
    """We'll put our output in <proj-dir>/build/lint and the annotated,
       syntax-colored, and htmlified copies of the source files in
       <proj-dir>/build/lint/files
    """
    os.chdir(projdir)
    if not os.path.isdir('build/lint/files'):
        os.makedirs('build/lint/files')
    return os.path.normpath(os.path.join(projdir, 'build', 'lint'))


def cleandir(d):
    os.chdir(d)
    for fname in os.listdir(d):
        if os.path.isfile(fname):
            os.unlink(fname)
    os.chdir(os.path.join(d, 'files'))
    for fname in os.listdir('.'):
        if os.path.isfile(fname):
            os.unlink(fname)


def project_name(projdir):
    package_json = os.path.join(projdir, 'package.json')
    if os.path.exists(package_json):
        return json.loads(open(package_json, 'rb').read())['name']
    else:
        _, projdirname = os.path.split(projdir)
        if os.path.exists(os.path.join(projdir, projdirname)):
            return projdirname
    raise RuntimeError("You must create a package.json file with the project name.")


class File(object):
    fname = ''      # relative to projdir
    abspath = ''
    location = ''   # files/..
    
    def __init__(self, abspath, projname, args):
        self.abspath = abspath
        self.fname = abspath.split(projname, 1)[1].replace('\\', '/').strip('/')
        self.location = 'files/' + self.fname.replace('/', ',')
        self.html = self.location[:-3] + '.html'
        self.lines = defaultdict(list)
        self.update(args)
        

    def update(self, args):
        line = msg_id = symbol = obj = msg = ""
        if len(args) >= 1:
            line = int(args[0])
        if len(args) >= 2:
            msg_id = args[1]
        if len(args) >= 3:
            symbol = args[2]
        if len(args) >= 4:
            obj = args[3]
        if len(args) >= 5:
            msg = args[4]

        self.lines[line].append(dict(
            line=line, 
            msg_id=msg_id,
            symbol=symbol,
            obj=obj,
            msg=msg,
        ))

    def __repr__(self):
        self.lines = dict(self.lines)
        import pprint
        return pprint.pformat(self.__dict__)


class Files(dict):
    """Place to record info about the source files.
    """
    def add(self, abspath, projname, args):
        if abspath in self:
            f = self[abspath]
            f.update(args)
            return f
        f = File(abspath, projname, args)
        super(Files, self).__setitem__(abspath, f)
        return f


def write_fancy_report(html, projname, projdir, lintdir):
    """Make the html relative to the project directory.
    """
    files = Files()
    
    def regexquote(s):
        return s.replace('\\', '\\\\')

    # convert all backslashes to forward-slashes.
    def fwdslashify(m):
        return m.group(1).replace('\\', '/')

    def copy_python(f):
        src = f.abspath
        dst = f.html
        
        from pygments import highlight
        from pygments.lexers import PythonLexer
        from pygments.formatters import HtmlFormatter
        code = open(src).read()
        with open(dst, 'w') as fp:
            fp.write(textwrap.dedent("""
            <!doctype html>
            <html lang='nb-no'>
            <head>
            <style>
            %s
            </style>
            </head>
            <body>
            """) % get_css())
            fmt = HtmlFormatter(linenos='inline', anchorlinenos='dkl')
            ccode = highlight(code, PythonLexer(), fmt).encode('u8')
            for line, errlst in f.lines.items():
                errhtml = []
                for err in errlst:
                    errhtml.append(err['msg'].strip())
                errhtml = '<ul class="errdescr"><li>%s</ul>' % '<li>'.join(errhtml)
                ccode = re.sub(
                    r'<span class="lineno">(\s*%d)</span>' % line,
                    r'<span class="err hll"><span class="lineno">\1</span>',
                    ccode
                )
                ccode = re.sub(
                    r'<span class="lineno">(\s*%d)</span>' % (line + 1),
                    r'</span>%s<span class="lineno">\1</span>' % errhtml,
                    ccode
                )
            fp.write(ccode)
            fp.write(textwrap.dedent("""
            </body>
            </html>
            """))
        

    def cp_file(m):
        args =  m.group(2).replace('</td>', '').replace('</tr>', '').split('<td>')
        f = files.add(m.group(1), projname, args)
        return '<a href="%s">%s</a></td><td>%s</tr>' % (f.html, f.fname, m.group(2))
    
    html = re.sub(
        '(%s)</td><td>(.*?)</tr>' % (regexquote(projdir) + r'[/\\][^\s]*\.py'),
        cp_file,
        html,
        flags=re.DOTALL
    )

    with open('pylint_files.py', 'w') as fp:
        print >>fp, 'files = {'
        for f in files.values():
            print >>fp, '    %r: %r,' % (f.fname, f)
        print >>fp, '}'

    print 'copying files.. (this can take a while if you have lots of files)'
    for f in files.values():
        copy_python(f)

    return html


def get_css():
    return """
    .highlight .hll { background-color: #ffffcc }
    .highlight  { background: #f8f8f8; }
    .highlight .c { color: #408080; font-style: italic } /* Comment */
    .highlight .err { border: 1px solid #FF0000 } /* Error */
    .highlight .k { color: #008000; font-weight: bold } /* Keyword */
    .highlight .o { color: #666666 } /* Operator */
    .highlight .cm { color: #408080; font-style: italic } /* Comment.Multiline */
    .highlight .cp { color: #BC7A00 } /* Comment.Preproc */
    .highlight .c1 { color: #408080; font-style: italic } /* Comment.Single */
    .highlight .cs { color: #408080; font-style: italic } /* Comment.Special */
    .highlight .gd { color: #A00000 } /* Generic.Deleted */
    .highlight .ge { font-style: italic } /* Generic.Emph */
    .highlight .gr { color: #FF0000 } /* Generic.Error */
    .highlight .gh { color: #000080; font-weight: bold } /* Generic.Heading */
    .highlight .gi { color: #00A000 } /* Generic.Inserted */
    .highlight .go { color: #808080 } /* Generic.Output */
    .highlight .gp { color: #000080; font-weight: bold } /* Generic.Prompt */
    .highlight .gs { font-weight: bold } /* Generic.Strong */
    .highlight .gu { color: #800080; font-weight: bold } /* Generic.Subheading */
    .highlight .gt { color: #0040D0 } /* Generic.Traceback */
    .highlight .kc { color: #008000; font-weight: bold } /* Keyword.Constant */
    .highlight .kd { color: #008000; font-weight: bold } /* Keyword.Declaration */
    .highlight .kn { color: #008000; font-weight: bold } /* Keyword.Namespace */
    .highlight .kp { color: #008000 } /* Keyword.Pseudo */
    .highlight .kr { color: #008000; font-weight: bold } /* Keyword.Reserved */
    .highlight .kt { color: #B00040 } /* Keyword.Type */
    .highlight .m { color: #666666 } /* Literal.Number */
    .highlight .s { color: #BA2121 } /* Literal.String */
    .highlight .na { color: #7D9029 } /* Name.Attribute */
    .highlight .nb { color: #008000 } /* Name.Builtin */
    .highlight .nc { color: #0000FF; font-weight: bold } /* Name.Class */
    .highlight .no { color: #880000 } /* Name.Constant */
    .highlight .nd { color: #AA22FF } /* Name.Decorator */
    .highlight .ni { color: #999999; font-weight: bold } /* Name.Entity */
    .highlight .ne { color: #D2413A; font-weight: bold } /* Name.Exception */
    .highlight .nf { color: #0000FF } /* Name.Function */
    .highlight .nl { color: #A0A000 } /* Name.Label */
    .highlight .nn { color: #0000FF; font-weight: bold } /* Name.Namespace */
    .highlight .nt { color: #008000; font-weight: bold } /* Name.Tag */
    .highlight .nv { color: #19177C } /* Name.Variable */
    .highlight .ow { color: #AA22FF; font-weight: bold } /* Operator.Word */
    .highlight .w { color: #bbbbbb } /* Text.Whitespace */
    .highlight .mf { color: #666666 } /* Literal.Number.Float */
    .highlight .mh { color: #666666 } /* Literal.Number.Hex */
    .highlight .mi { color: #666666 } /* Literal.Number.Integer */
    .highlight .mo { color: #666666 } /* Literal.Number.Oct */
    .highlight .sb { color: #BA2121 } /* Literal.String.Backtick */
    .highlight .sc { color: #BA2121 } /* Literal.String.Char */
    .highlight .sd { color: #BA2121; font-style: italic } /* Literal.String.Doc */
    .highlight .s2 { color: #BA2121 } /* Literal.String.Double */
    .highlight .se { color: #BB6622; font-weight: bold } /* Literal.String.Escape */
    .highlight .sh { color: #BA2121 } /* Literal.String.Heredoc */
    .highlight .si { color: #BB6688; font-weight: bold } /* Literal.String.Interpol */
    .highlight .sx { color: #008000 } /* Literal.String.Other */
    .highlight .sr { color: #BB6688 } /* Literal.String.Regex */
    .highlight .s1 { color: #BA2121 } /* Literal.String.Single */
    .highlight .ss { color: #19177C } /* Literal.String.Symbol */
    .highlight .bp { color: #008000 } /* Name.Builtin.Pseudo */
    .highlight .vc { color: #19177C } /* Name.Variable.Class */
    .highlight .vg { color: #19177C } /* Name.Variable.Global */
    .highlight .vi { color: #19177C } /* Name.Variable.Instance */
    .highlight .il { color: #666666 } /* Literal.Number.Integer.Long */
    ul.errdescr {font-weight:bold; color:red; margin:0;padding:14px 3ex; white-space:normal;list-style-type:none;border:1px solid #666; border-radius:0 5px 5px;}
    """


def main():
    import time
    start = time.time()
    
    projdir = project_dir()
    lintdir = make_build_lint(projdir)
    cleandir(lintdir)
    projname = project_name(projdir)

    os.chdir(lintdir)
    target = '../../' + projname
    with open('index.html', 'w') as fp:
        report = replace(parse_subst(subst), dklint(target))
        html = write_fancy_report(report, projname, projdir, lintdir)
        fp.write(html)
    print 'done in %.2f secs.' % (time.time() - start)

    
if __name__ == "__main__":
    main()
