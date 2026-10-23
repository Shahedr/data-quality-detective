"""Disk-backed, preview-first cleaning; never overwrite an uploaded source."""
import csv
import hashlib
import json
import re
import shutil
import sqlite3
from copy import copy
from contextlib import closing
from datetime import datetime
from html import escape
from zipfile import ZipFile

from defusedxml import ElementTree as ET
from defusedxml.sax import make_parser

from webapp.largeworkbook import CheckedReader, ContentHandler, SheetOverview, NS
from webapp.workspace import validate_excel_value


def changed(value, options, stats):
    result = value.strip() if options.trim else value
    if options.case != 'keep':
        result = result.lower() if options.case == 'lower' else result.upper()
    if options.date_format and result:
        try:
            result = datetime.strptime(result, options.date_format).strftime('%Y-%m-%d')
        except ValueError:
            stats['invalid_dates_unchanged'] += 1
    return result


def stats_for():
    return {'cells_changed': 0, 'duplicates_removed': 0, 'invalid_dates_unchanged': 0, 'changes': []}


def record_change(stats, row, column, old, new):
    if new != old:
        stats['cells_changed'] += 1
        if len(stats['changes']) < 100:
            stats['changes'].append({'row': row, 'column': column, 'before': old[:500], 'after': new[:500]})


def clean_csv(source, output, options, rows, check):
    """rows yields a bounded header then records, reusing the upload parser."""
    stats = stats_for()
    columns = next(rows)
    if len(set(options.columns)) != len(options.columns) or any(c not in columns for c in options.columns):
        raise ValueError('Select unique existing CSV column names.')
    if (options.trim or options.case != 'keep' or options.date_format) and not options.columns:
        raise ValueError('Select columns to clean.')
    indexes = [columns.index(c) for c in options.columns]
    database = output.with_suffix('.sqlite')
    try:
        with closing(sqlite3.connect(database)) as db, output.open('w', encoding='utf-8', newline='') as target:
            db.execute('PRAGMA cache_size=-4096')
            db.execute('CREATE TABLE seen (value BLOB PRIMARY KEY) WITHOUT ROWID')
            writer = csv.writer(target)
            writer.writerow(columns)
            count = kept = 0
            for row in rows:
                check()
                count += 1
                for i in indexes:
                    new = changed(row[i], options, stats)
                    record_change(stats, count+1, columns[i], row[i], new)
                    row[i] = new
                if options.remove_duplicates:
                    key = json.dumps(row, ensure_ascii=False, separators=(',', ':')).encode()
                    inserted = db.execute('INSERT OR IGNORE INTO seen VALUES (?)', (key,)).rowcount
                    if not inserted:
                        stats['duplicates_removed'] += 1
                        continue
                writer.writerow(row)
                kept += 1
                if count % 10000 == 0:
                    db.commit()
                    if shutil.disk_usage(output.parent).free < 256*1024**2:
                        raise ValueError('Insufficient temporary disk space')
            db.commit()
            stats.update(rows_before=count, rows_after=kept)
    finally:
        database.unlink(missing_ok=True)
    stats['notice'] = 'Separate UTF-8 CSV copy. Quoting and line endings are normalized. IDs and literal strings remain strings; CSV spreadsheet software can interpret formula-like text when opened. The source is unchanged.'
    return stats


class SharedStrings(ContentHandler):
    def __init__(self, db):
        super().__init__()
        self.db, self.index = db, 0
        self.parts, self.length, self.rich, self.in_text = [], 0, False, False
        self.depth = 0

    def startElement(self, name, attrs):
        self.depth += 1
        if self.depth > 64:
            raise ValueError('Shared-string XML nesting exceeds safety limit')
        tag = name.split(':')[-1]
        if tag == 'si':
            self.parts, self.length, self.rich = [], 0, False
        elif tag not in {'sst', 't'}:
            self.rich = True
        self.in_text = tag == 't'

    def characters(self, value):
        if self.in_text:
            self.length += len(value)
            if self.length > 32767:
                raise ValueError('Shared string exceeds Excel cell limit')
            self.parts.append(value)

    def endElement(self, name):
        self.depth -= 1
        self.in_text = False
        if name.split(':')[-1] == 'si':
            self.db.execute('INSERT INTO strings VALUES (?,?,?)', (self.index, ''.join(self.parts), int(self.rich)))
            self.index += 1
            if self.index % 10000 == 0:
                self.db.commit()


CELL = re.compile(rb'<(?P<tag>(?:[A-Za-z_][\w.-]{0,99}:)?c)(?=[\s/>])')


def patch_cells(source, target, transform, check):
    buffer = b''
    while True:
        check()
        block = source.read(65536)
        buffer += block
        if b'<!--' in buffer or b'<![CDATA[' in buffer:
            raise ValueError('Comments/CDATA in worksheet XML cannot be cleaned safely.')
        while True:
            match = CELL.search(buffer)
            if not match:
                keep = 128 if block else 0
                if len(buffer) > keep:
                    target.write(buffer[:-keep] if keep else buffer)
                    buffer = buffer[-keep:] if keep else b''
                break
            target.write(buffer[:match.start()])
            buffer = buffer[match.start():]
            tag = match['tag']
            # Quoted attributes may contain >; let the XML parser validate the complete cell.
            end = re.search(rb'</'+re.escape(tag)+rb'\s*>', buffer)
            empty = re.match(rb'<'+re.escape(tag)+rb'(?=[\s/>])(?:[^\x22\x27<>]|\x22[^\x22]*\x22|\x27[^\x27]*\x27)*?/\s*>', buffer)
            length = empty.end() if empty else end.end() if end else None
            if length is None:
                if len(buffer) > 2*1024**2:
                    raise ValueError('Worksheet cell exceeds safe cleaning size')
                break
            target.write(transform(buffer[:length]))
            buffer = buffer[length:]
        if not block:
            if buffer:
                raise ValueError('Incomplete worksheet cell')
            return


def clean_excel(source, output, options, check):
    if options.remove_duplicates:
        raise ValueError('Excel row deletion can break references and VBA and is not supported.')
    if not options.columns or len(set(options.columns)) != len(options.columns) or any(not re.fullmatch('[A-Z]{1,3}', c) for c in options.columns):
        raise ValueError('Choose unique Excel column letters, such as A or BC.')
    def column_number(label):
        value = 0
        for char in label:
            value = value*26+ord(char)-64
        return value
    if any(column_number(c)>16384 for c in options.columns):
        raise ValueError('Column exceeds Excel limit')
    stats, hashes = stats_for(), {}
    database = output.with_suffix('.sqlite')
    try:
        with ZipFile(source) as src, closing(sqlite3.connect(database)) as db:
            names = src.namelist()
            if any(p.startswith('_xmlsignatures/') or 'vbaprojectsignature' in p.lower() for p in names):
                raise ValueError('Signed workbooks cannot be edited safely.')
            workbook = ET.fromstring(src.read('xl/workbook.xml'))
            sheets = workbook.findall('m:sheets/m:sheet', NS)
            selected = next((s for s in sheets if s.attrib['name'] == options.sheet), None)
            if selected is None:
                raise ValueError('Choose an existing worksheet.')
            relations = ET.fromstring(src.read('xl/_rels/workbook.xml.rels'))
            identifier = selected.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
            relation = next(r for r in relations if r.attrib['Id'] == identifier)
            import posixpath
            link = relation.attrib['Target']
            part = posixpath.normpath(link.lstrip('/') if link.startswith('/') else 'xl/'+link)
            db.execute('PRAGMA cache_size=-4096')
            db.execute('CREATE TABLE strings (id INTEGER PRIMARY KEY, value TEXT, rich INTEGER)')
            if 'xl/sharedStrings.xml' in names:
                parser = make_parser()
                parser.setContentHandler(SharedStrings(db))
                with src.open('xl/sharedStrings.xml') as strings:
                    parser.parse(CheckedReader(strings, check))
            db.commit()
            def transform(raw):
                # Wrap namespace-prefixed cells in their worksheet namespace.
                prefix = CELL.match(raw)['tag'][:-1].decode()
                declaration = f' xmlns:{prefix[:-1]}="{NS["m"]}"' if prefix else ''
                cell = ET.fromstring(('<root xmlns="'+NS['m']+'"'+declaration+'>').encode()+raw+b'</root>')[0]
                coordinate = cell.attrib.get('r', '')
                match = re.fullmatch(r'([A-Z]+)([1-9][0-9]*)', coordinate)
                if not match or match[1] not in options.columns or int(match[2]) == 1:
                    return raw
                if cell.find('m:f', NS) is not None:
                    return raw
                kind, rich = cell.attrib.get('t'), False
                if kind == 's':
                    found = db.execute('SELECT value,rich FROM strings WHERE id=?', (int(cell.find('m:v', NS).text),)).fetchone()
                    if found is None:
                        raise ValueError('Missing shared string')
                    value, rich = found
                elif kind == 'inlineStr':
                    text = cell.find('m:is', NS)
                    if text is None:
                        return raw
                    rich = any(child.tag != '{'+NS['m']+'}t' for child in text)
                    value = ''.join(child.text or '' for child in text if child.tag == '{'+NS['m']+'}t')
                elif kind == 'str':
                    value = cell.find('m:v', NS).text or ''
                else:
                    return raw
                new = changed(value, options, stats)
                if new == value:
                    return raw
                if rich or any(child.tag not in {'{'+NS['m']+'}v', '{'+NS['m']+'}is'} for child in cell):
                    raise ValueError('Selected rich text or cell features cannot be changed safely.')
                validate_excel_value(new)
                opening = re.match(rb'<(?:[^\x22\x27<>]|\x22[^\x22]*\x22|\x27[^\x27]*\x27)*>', raw)[0][:-1].decode()
                opening = re.sub(r'\s+t\s*=\s*([\x22\x27]).*?\1', '', opening).rstrip('/')
                result = (opening+' t="inlineStr"><'+prefix+'is><'+prefix+'t xml:space="preserve">'+escape(new, quote=False)+'</'+prefix+'t></'+prefix+'is></'+prefix+'c>').encode()
                record_change(stats, int(match[2]), match[1], value, new)
                return result
            with ZipFile(output, 'w') as dst:
                dst.comment = src.comment
                for item in src.infolist():
                    check()
                    digest = hashlib.sha256()
                    with src.open(item) as reader, dst.open(copy(item), 'w', force_zip64=True) as writer:
                        if item.filename == part:
                            patch_cells(reader, writer, transform, check)
                        else:
                            for block in iter(lambda: reader.read(4*1024**2), b''):
                                check()
                                digest.update(block)
                                writer.write(block)
                    if item.filename != part:
                        hashes[item.filename] = digest.hexdigest()
            with ZipFile(output) as verified:
                parser = make_parser()
                parser.setContentHandler(SheetOverview())
                with verified.open(part) as reader:
                    parser.parse(CheckedReader(reader, check))
                for name, expected in hashes.items():
                    digest = hashlib.sha256()
                    with verified.open(name) as reader:
                        for block in iter(lambda: reader.read(4*1024**2), b''):
                            check()
                            digest.update(block)
                    if digest.hexdigest() != expected:
                        raise ValueError('Workbook preservation check failed')
            if stats['cells_changed'] == 0:
                shutil.copyfile(source, output)
    finally:
        database.unlink(missing_ok=True)
    stats['sheet'] = options.sheet
    stats['notice'] = 'Separate preservation-aware workbook copy. Only selected literal text cells below row 1 change. Formula cells are skipped; other package parts, including VBA, are verified unchanged. Data changes can change formula results or macro behavior. Review in Excel.'
    return stats
