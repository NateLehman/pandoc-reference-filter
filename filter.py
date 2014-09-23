import pandocfilters as pf

latex_figure = """
\\begin{{figure}}[htbp]
\\label{{{label}}}
\\centering
\\includegraphics{{{filename}}}
\\caption{{{caption}}}
\\end{{figure}}"""

html_figure = """
<figure id="{id}">
<img src="{filename}" alt="{alt}" />
<figcaption>{caption}</figcaption>
</figure>"""

latex_link = '\\autoref{{{label}}}'
html_link = '<a href="{target}">{text}</a>'


def rawlatex(s):
    return pf.RawInline('latex', s)


def rawhtml(s):
    return pf.RawInline('html', s)


def isfigure(key, value):
    return (key == 'Para' and len(value) == 2 and value[0]['t'] == 'Image')


def isattrfigure(key, value):
    return (isfigure(key, value) and isattr(value[1]['c']))


def islinktofigure(key, value):
    return (key == 'Link' and (value[1][0]).startswith('#fig'))


def isattr(string):
    return string.startswith('{') and string.endswith('}')


class FigureCounter(object):
    figlist = []

figcount = FigureCounter()

# we need to create a list of all of the figures and then cross
# reference them with the references in the text. The problem is
# that we need the list of figures before we can replace the text of
# the references, which we can't do with a single filter (because we
# can have the in text references appearing before the figures in
# the ast, which leaves them not knowing what number their figure
# is).

# to solve this we need to alter toJSONFilter so that it can take a
# sequence of actions to apply to the tree. The first action will
# count the figures and replace with the right html. The second
# action will put numbers in all the in text references.


def figure_number(key, value, format, metadata):
    """We want to number figures in the text: prepending the caption
    with 'Figure x:', replacing the reference with 'Figure x',
    putting an id on the figure  and putting a href to the figure id
    into the reference.
    """
    # make the list of figures
    if isattrfigure(key, value):
        image = value[0]
        attr = value[1]['c']
        filename = image['c'][1][0]
        caption = pf.stringify(image['c'][0])
        label = attr.strip('{}')

        if format in ('html', 'html5'):
            if label not in figcount.figlist:
                figcount.figlist.append(label)

            nfig = len(figcount.figlist)
            caption = 'Figure {n}: {caption}'.format(n=nfig, caption=caption)

            return pf.Para([rawhtml(html_figure.format(id=label[1:],
                                                    filename=filename,
                                                    alt=caption,
                                                    caption=caption))])
        elif format == 'latex':
            return pf.Para([rawlatex(latex_figure.format(filename=filename,
                                                      caption=caption,
                                                      label=label[1:]))])


def convert_links(key, value, format, metadata):
    if islinktofigure(key, value) and format in ('html', 'html5'):
        target = value[1][0]
        try:
            fign = figcount.figlist.index(target) + 1
        except IndexError:
            return None
        text = 'Figure {}'.format(fign)
        return rawhtml(html_link.format(text=text, target=target))

    elif islinktofigure(key, value) and format == 'latex':
        # use autoref instead of hyperref
        label = value[1][0][1:]  # strip leading '#'
        return rawlatex(latex_link.format(label=label))


def toJSONFilter(actions):
    """Modified from pandocfilters to accept a list of actions (to
    apply in series) as well as a single action.

    Converts an action into a filter that reads a JSON-formatted
    pandoc document from stdin, transforms it by walking the tree
    with the action, and returns a new JSON-formatted pandoc document
    to stdout.

    The argument is a function action(key, value, format, meta),
    where key is the type of the pandoc object (e.g. 'Str', 'Para'),
    value is the contents of the object (e.g. a string for 'Str',
    a list of inline elements for 'Para'), format is the target
    output format (which will be taken for the first command line
    argument if present), and meta is the document's metadata.

    If the function returns None, the object to which it applies
    will remain unchanged.  If it returns an object, the object will
    be replaced.  If it returns a list, the list will be spliced in to
    the list to which the target object belongs.  (So, returning an
    empty list deletes the object.)
    """
    doc = pf.json.loads(pf.sys.stdin.read())
    if len(pf.sys.argv) > 1:
        format = pf.sys.argv[1]
    else:
        format = ""

    if type(actions) is type(toJSONFilter):
        altered = pf.walk(doc, actions, format, doc[0]['unMeta'])
    elif type(actions) is list:
        altered = doc
        for action in actions:
            altered = pf.walk(altered, action, format, doc[0]['unMeta'])

    pf.json.dump(altered, pf.sys.stdout)


if __name__ == '__main__':
    # toJSONFilter(figure_number)
    toJSONFilter([figure_number, convert_links])
