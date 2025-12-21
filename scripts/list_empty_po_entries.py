#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys


@dataclass
class Block:
    refs: list[str]
    msgid: str
    msgstr: str


def _unquote(line: str) -> str:
    line = line.strip()
    if line.startswith('"') and line.endswith('"'):
        return line[1:-1]
    return ''


def parse_blocks(po_path: str | Path) -> list[Block]:
    text = Path(po_path).read_text(encoding='utf-8')

    blocks: list[Block] = []
    refs: list[str] = []
    msgid_parts: list[str] = []
    msgstr_parts: list[str] = []
    mode: str | None = None

    def flush() -> None:
        nonlocal refs, msgid_parts, msgstr_parts, mode
        if not msgid_parts:
            refs = []
            return
        msgid = ''.join(msgid_parts)
        msgstr = ''.join(msgstr_parts)
        if msgid != '':
            blocks.append(Block(refs=refs, msgid=msgid, msgstr=msgstr))
        refs = []
        msgid_parts = []
        msgstr_parts = []
        mode = None

    for raw in text.splitlines():
        line = raw.rstrip('\n')
        if not line.strip():
            flush()
            continue
        if line.startswith('#:'):
            refs.append(line)
            continue
        if line.startswith('#'):
            continue
        if line.startswith('msgid '):
            flush()
            mode = 'msgid'
            msgid_parts = [_unquote(line[len('msgid '):])]
            continue
        if line.startswith('msgstr '):
            mode = 'msgstr'
            msgstr_parts = [_unquote(line[len('msgstr '):])]
            continue
        if line.startswith('"'):
            if mode == 'msgid':
                msgid_parts.append(_unquote(line))
            elif mode == 'msgstr':
                msgstr_parts.append(_unquote(line))
            continue

    flush()

    # remove header
    blocks = [b for b in blocks if b.msgid != '']
    return blocks


def main() -> None:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    po = Path('src/translations/es/LC_MESSAGES/messages.po')
    blocks = parse_blocks(po)
    empty = [b for b in blocks if b.msgstr.strip() == '']

    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open('w', encoding='utf-8', newline='\n') as f:
            f.write(f'total blocks: {len(blocks)}\n')
            f.write(f'empty msgstr: {len(empty)}\n')
            f.write('---\n')
            for b in empty:
                ref = b.refs[0] if b.refs else ''
                f.write(f'{ref}\n')
                f.write(f'{b.msgid}\n')
                f.write('---\n')
        return

    # Fallback: print counts only (avoid console encoding issues on Windows)
    print(f'total blocks: {len(blocks)}')
    print(f'empty msgstr: {len(empty)}')


if __name__ == '__main__':
    main()
