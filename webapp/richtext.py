"""Retain Excel text runs while applying reviewed trim/case edits."""
from copy import deepcopy
from xml.etree import ElementTree

MAIN = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
NS = {'m': MAIN}


def string_value(element):
    # Phonetic annotations are not part of the displayed cell text.
    return ''.join(node.text or '' for child in element
                   for node in ([child] if child.tag == '{'+MAIN+'}t'
                                else child.findall('m:t', NS) if child.tag == '{'+MAIN+'}r' else []))


def preserve_runs(element, new, options):
    """Map trim/case changes to their original runs, including Unicode expansion."""
    element = deepcopy(element)
    old = string_value(element)
    trimmed = old.strip() if options.trim else old
    expected = trimmed.upper() if options.case == 'upper' else trimmed.lower() if options.case == 'lower' else trimmed
    start = len(old)-len(old.lstrip()) if options.trim else 0
    end = len(old.rstrip()) if options.trim else len(old)
    nodes = []
    for child in element:
        if child.tag == '{'+MAIN+'}t':
            nodes.append(child)
        elif child.tag == '{'+MAIN+'}r' and all(n.tag in {'{'+MAIN+'}rPr', '{'+MAIN+'}t'} for n in child):
            nodes.extend(child.findall('m:t', NS))
        else:
            raise ValueError('Selected text contains unsupported annotations. No formatting was removed; leave this cell unchanged.')
    if new != expected:
        raise ValueError('Date conversion of rich-text cells cannot preserve character formatting safely. Disable date conversion for this column.')
    offset = consumed = 0
    for node in nodes:
        text = node.text or ''
        kept = text[max(0, start-offset):max(0, min(len(text), end-offset))]
        size = sum(len(c.upper() if options.case == 'upper' else c.lower() if options.case == 'lower' else c) for c in kept)
        node.text = new[consumed:consumed+size]
        node.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        consumed += size
        offset += len(text)
    if consumed != len(new):
        raise ValueError('Text formatting could not be mapped safely. No changed workbook was generated.')
    element.tag = '{'+MAIN+'}is'
    return ElementTree.tostring(element, encoding='unicode')
