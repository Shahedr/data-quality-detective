"""Read-only OOXML overview: stream worksheet XML, never load or save a workbook."""
import hashlib
import posixpath
import re
# ContentHandler stores no parser; parsing is exclusively defusedxml.sax below.
from xml.sax.handler import ContentHandler  # nosec B406
from zipfile import ZipFile

from defusedxml import ElementTree as ET
from defusedxml.sax import make_parser
from webapp.zipguard import check_directory

MAX_EXPANDED = 8 * 1024 ** 3
MAX_TEXT = 1024 ** 2
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


class CheckedReader:
    def __init__(self, source, check):
        self.source, self.check = source, check
        self.markup = False
        self.quote = None
        self.token_bytes = 0

    def read(self, size=-1):
        self.check()
        data = self.source.read(min(size, 65536) if size >= 0 else 65536)
        # Expat buffers a whole attribute before invoking handlers; bound it first.
        previous = 0
        for match in re.finditer(br'[<>\x22\x27]', data):
            char = match[0]
            if self.markup:
                self.token_bytes += match.end() - previous
                if self.token_bytes > MAX_TEXT:
                    raise ValueError('XML markup token exceeds safety limit')
                if self.quote:
                    if char == self.quote:
                        self.quote = None
                elif char in {b'"', b"'"}:
                    self.quote = char
                elif char == b'>':
                    self.markup = False
            elif char == b'<':
                self.markup, self.token_bytes = True, 1
            previous = match.end()
        if self.markup:
            self.token_bytes += len(data) - previous
            if self.token_bytes > MAX_TEXT:
                raise ValueError('XML markup token exceeds safety limit')
        return data

    def close(self):
        self.source.close()


class SheetOverview(ContentHandler):
    def __init__(self, row_limit=1048576, column_limit=16384, row_sink=None):
        super().__init__()
        self.rows = self.cells = self.formulas = self.errors = self.columns = 0
        self.depth = self.text = 0
        self.row_limit, self.column_limit, self.max_row = row_limit, column_limit, 0
        self.last_row = 0
        self.preview = {'columns': [], 'rows': []}
        self.preview_cells = {}
        self.preview_cell = None
        self.preview_tag = None
        self.row_sink = row_sink
        self.row_values, self.row_refs = {}, {}

    def coordinate(self, coordinate):
        match = re.fullmatch(r'([A-Z]{1,3})([1-9][0-9]{0,6})', coordinate)
        if not match or int(match[2]) > self.row_limit:
            raise ValueError('Worksheet exceeds row limit or has an invalid reference')
        column = 0
        for char in match[1]:
            column = column*26+ord(char)-64
        if column > self.column_limit:
            raise ValueError('Worksheet exceeds column limit')
        self.max_row = max(self.max_row, int(match[2]))
        return column

    def startElement(self, name, attrs):
        self.depth += 1
        if self.depth > 64:
            raise ValueError('XML nesting exceeds safety limit')
        tag = name.split(':')[-1]
        if len(name) > 104:
            raise ValueError('XML name exceeds safety limit')
        if tag == 'dimension':
            for coordinate in attrs.get('ref', 'A1').split(':'):
                self.coordinate(coordinate)
        elif tag == 'row':
            self.row_values, self.row_refs = {}, {}
            number = attrs.get('r', str(self.last_row+1))
            if not re.fullmatch('[1-9][0-9]{0,6}', number):
                raise ValueError('Invalid worksheet row index')
            number = int(number)
            if number > self.row_limit or number <= self.last_row:
                raise ValueError('Worksheet row indices exceed limits or repeat')
            self.last_row = number
            self.max_row = max(self.max_row, number)
            self.rows += 1
            if len(self.preview['rows']) < 20:
                self.preview['rows'].append({'row_number': number, 'values': []})
            if self.rows > self.row_limit:
                raise ValueError('Worksheet exceeds Excel row limit')
        elif tag == 'c':
            self.text = 0
            coordinate = attrs.get('r', '')
            column = self.coordinate(coordinate)
            self.columns = max(self.columns, column)
            self.cells += 1
            self.errors += attrs.get('t') == 'e'
            self.preview_cell = None
            if self.row_sink or (self.rows <= 20 and column <= 20 and self.preview['rows']):
                values = self.preview['rows'][-1]['values'] if self.rows <= 20 and column <= 20 and self.preview['rows'] else None
                if values is not None:
                    values.extend([''] * (column-len(values)))
                self.preview_cell = {'values': values, 'column': column-1, 'kind': attrs.get('t'), 'v': '', 't': '', 'f': ''}
                if values is not None:
                    self.preview['columns'] = [chr(65+i) for i in range(max(len(self.preview['columns']), column))]
        elif tag == 'f':
            self.formulas += 1
        if tag in {'v', 't', 'f'}:
            self.preview_tag = tag

    def characters(self, content):
        self.text += len(content)
        if self.text > MAX_TEXT:
            raise ValueError('Worksheet XML text exceeds safety limit')
        if self.preview_cell is not None and self.preview_tag:
            key = self.preview_tag
            self.preview_cell[key] += content[:max(0, 500-len(self.preview_cell[key]))]

    def endElement(self, name):
        self.depth -= 1
        tag = name.split(':')[-1]
        if tag in {'v', 't', 'f'}:
            self.preview_tag = None
        if tag == 'c' and self.preview_cell is not None:
            cell = self.preview_cell
            value = ('='+cell['f']) if cell['f'] else cell['t'] if cell['kind'] == 'inlineStr' else cell['v']
            value = value[:500]
            if cell['values'] is not None:
                cell['values'][cell['column']] = value
            if self.row_sink:
                self.row_values[cell['column']] = value
            if cell['kind'] == 's' and not cell['f']:
                identifier = int(cell['v'])
                if cell['values'] is not None:
                    self.preview_cells[(len(self.preview['rows'])-1, cell['column'])] = identifier
                if self.row_sink:
                    self.row_refs[cell['column']] = identifier
            self.preview_cell = None
        if tag == 'row' and self.row_sink:
            self.row_sink(self.last_row, self.row_values, self.row_refs)

    def resolve_preview(self, lookup):
        for (row, column), identifier in self.preview_cells.items():
            self.preview['rows'][row]['values'][column] = lookup(identifier)[:500]
        return self.preview


class PreviewComplete(Exception):
    pass


class PreviewStrings(ContentHandler):
    """Resolve only the shared strings referenced by the bounded worksheet previews."""
    def __init__(self, needed, sink=None):
        self.needed, self.values = needed, {}
        self.index, self.depth, self.length = -1, 0, 0
        self.in_text, self.value = False, ''
        self.sink = sink

    def startElement(self, name, attrs):
        self.depth += 1
        if self.depth > 64:
            raise ValueError('Shared-string XML nesting exceeds safety limit')
        tag = name.split(':')[-1]
        if tag == 'si':
            self.index += 1
            self.value, self.length = '', 0
        self.in_text = tag == 't'

    def characters(self, content):
        if self.in_text:
            self.length += len(content)
            if self.length > 32767:
                raise ValueError('Shared string exceeds Excel cell limit')
            if self.sink or self.index in self.needed:
                self.value += content[:max(0, 500-len(self.value))]

    def endElement(self, name):
        self.depth -= 1
        self.in_text = False
        if name.split(':')[-1] == 'si':
            if self.sink:
                self.sink(self.index, self.value)
            if self.index in self.needed:
                self.values[self.index] = self.value
            if not self.sink and len(self.values) == len(self.needed):
                raise PreviewComplete()


def stream_workbook(path, check=lambda: None, row_sink=None, string_sink=None):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(4 * 1024 ** 2), b''):
            check()
            digest.update(chunk)
    with path.open('rb') as source:
        check_directory(source, 10000, 8*1024**2)
    with ZipFile(path) as archive:
        entries = archive.infolist()
        names = archive.namelist()
        if (len(entries) > 10000 or len(set(names)) != len(names) or
                sum(e.file_size for e in entries) > MAX_EXPANDED or
                any(e.flag_bits & 1 or '\\' in e.filename or
                    e.filename.startswith('/') or '..' in e.filename.split('/') for e in entries)):
            raise ValueError('Unsafe or oversized workbook package')
        def metadata(name):
            if archive.getinfo(name).file_size > MAX_TEXT:
                raise ValueError('Workbook metadata exceeds safety limit')
            return ET.fromstring(archive.read(name))
        workbook = metadata('xl/workbook.xml')
        relations = metadata('xl/_rels/workbook.xml.rels')
        sheets = workbook.findall('m:sheets/m:sheet', NS)
        if not sheets or len(sheets) > 40:
            raise ValueError('Expected 1 to 40 worksheets')
        results, overviews = [], []
        for sheet in sheets:
            check()
            identifier = sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
            relation = next(r for r in relations if r.attrib['Id'] == identifier)
            target = relation.attrib['Target']
            part = posixpath.normpath(target.lstrip('/') if target.startswith('/') else 'xl/' + target)
            if relation.attrib.get('TargetMode') == 'External' or not part.startswith('xl/worksheets/'):
                raise ValueError('Unsupported worksheet relationship')
            overview = SheetOverview(row_sink=(lambda number, cells, refs: row_sink(sheet.attrib['name'], number, cells, refs)) if row_sink else None)
            parser = make_parser()
            parser.setContentHandler(overview)
            with archive.open(part) as source:
                parser.parse(CheckedReader(source, check))
            overviews.append(overview)
            results.append({'name': sheet.attrib['name'], 'state': sheet.attrib.get('state', 'visible'),
                            'stored_rows': overview.rows, 'columns': overview.columns,
                            'max_row': overview.max_row,
                            'stored_cells': overview.cells, 'formulas': overview.formulas,
                            'cached_errors': overview.errors, 'preview': overview.preview})
        needed = {identifier for overview in overviews for identifier in overview.preview_cells.values()}
        strings = PreviewStrings(needed, string_sink)
        if needed or (string_sink and 'xl/sharedStrings.xml' in names):
            parser = make_parser()
            parser.setContentHandler(strings)
            with archive.open('xl/sharedStrings.xml') as source:
                try:
                    parser.parse(CheckedReader(source, check))
                except PreviewComplete:
                    pass
            if set(strings.values) != needed:
                raise ValueError('Missing shared string in worksheet preview')
        for overview in overviews:
            overview.resolve_preview(strings.values.__getitem__)
        return {'kind': 'Excel', 'bytes': path.stat().st_size, 'sha256': digest.hexdigest(),
                'sheets': results, 'vba_present': any(n.lower().endswith('/vbaproject.bin') for n in names),
                'external_links_present': any(n.startswith('xl/externalLinks/') for n in names),
                'notice': 'Complete worksheet scan. Counts include stored headers, blank/styled cells and hidden sheets; cached errors may be stale. Inspection never executes or rewrites formulas, VBA or links. Preview full-file cleaning for a separate preserved copy. Browse the spreadsheet in blocks of rows; charts and audit templates use the smaller-file workspace.'}
