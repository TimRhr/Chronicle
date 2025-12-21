#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Entry:
    msgid: str
    msgstr: str


def _unquote_po_string(line: str) -> str:
    line = line.strip()
    if not (line.startswith('"') and line.endswith('"')):
        return ''
    return line[1:-1]


def parse_po(path: str | Path) -> dict[str, Entry]:
    text = Path(path).read_text(encoding='utf-8')

    entries: dict[str, Entry] = {}
    msgid_parts: list[str] = []
    msgstr_parts: list[str] = []
    mode: str | None = None

    def flush():
        nonlocal msgid_parts, msgstr_parts, mode
        if not msgid_parts:
            return
        msgid = ''.join(msgid_parts)
        msgstr = ''.join(msgstr_parts)
        if msgid:
            entries[msgid] = Entry(msgid=msgid, msgstr=msgstr)
        msgid_parts = []
        msgstr_parts = []
        mode = None

    for raw in text.splitlines():
        line = raw.rstrip('\n')
        if not line.strip():
            flush()
            continue
        if line.startswith('#'):
            continue

        if line.startswith('msgid '):
            flush()
            mode = 'msgid'
            rest = line[len('msgid '):]
            msgid_parts = [_unquote_po_string(rest)]
            continue

        if line.startswith('msgstr '):
            mode = 'msgstr'
            rest = line[len('msgstr '):]
            msgstr_parts = [_unquote_po_string(rest)]
            continue

        if line.startswith('"'):
            if mode == 'msgid':
                msgid_parts.append(_unquote_po_string(line))
            elif mode == 'msgstr':
                msgstr_parts.append(_unquote_po_string(line))
            continue

        # ignore other directives for this project (no plurals currently)

    flush()

    # Drop header entry
    entries.pop('', None)
    return entries


def main() -> None:
    de = parse_po('src/translations/de/LC_MESSAGES/messages.po')
    es = parse_po('src/translations/es/LC_MESSAGES/messages.po')

    de_filled = {k for k, v in de.items() if v.msgstr.strip()}
    es_filled = {k for k, v in es.items() if v.msgstr.strip()}

    missing_in_es = sorted(de_filled - es_filled)

    print(f'de entries: {len(de)}')
    print(f'es entries: {len(es)}')
    print(f'de filled: {len(de_filled)}')
    print(f'es filled: {len(es_filled)}')
    print(f'missing in es (where de is filled): {len(missing_in_es)}')

    for m in missing_in_es[:200]:
        print(m)


if __name__ == '__main__':
    main()
