#!/usr/bin/env python3
"""Check translation catalogs for missing msgstr entries.

Usage:
  python scripts/check_translations_complete.py
  python scripts/check_translations_complete.py --locales es --mode strict
  python scripts/check_translations_complete.py --mode parity --reference-locale de --exclude-locales en

Exit codes:
  0 = OK (no missing translations)
  1 = Missing translations found
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import sys


@dataclass
class Missing:
    locale: str
    msgid: str


def _safe_print(line: str) -> None:
    """Print without crashing on Windows code pages."""
    try:
        print(line)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((line + "\n").encode('utf-8', errors='replace'))


def _write_report(path: Path, missing: list[Missing]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='\n') as f:
        f.write(f"Missing translations: {len(missing)}\n")
        for m in missing:
            f.write(f"[{m.locale}] {m.msgid}\n")


def _unquote_po_string(line: str) -> str:
    s = line.strip()
    if not (s.startswith('"') and s.endswith('"')):
        return ''
    inner = s[1:-1]
    # Unescape PO sequences so comparisons are stable
    inner = inner.replace('\\\\', '\\')
    inner = inner.replace('\\"', '"')
    inner = inner.replace('\\n', '\n')
    inner = inner.replace('\\t', '\t')
    inner = inner.replace('\\r', '\r')
    return inner


def parse_po_entries(path: Path) -> dict[str, str]:
    """Return msgid->msgstr for non-header entries. Supports multiline blocks."""
    text = path.read_text(encoding='utf-8')

    entries: dict[str, str] = {}
    msgid_parts: list[str] = []
    msgstr_parts: list[str] = []
    mode: str | None = None

    def flush() -> None:
        nonlocal msgid_parts, msgstr_parts, mode
        if not msgid_parts:
            return
        msgid = ''.join(msgid_parts)
        msgstr = ''.join(msgstr_parts)
        if msgid != '':
            entries[msgid] = msgstr
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
            msgid_parts = [_unquote_po_string(line[len('msgid '):])]
            continue

        if line.startswith('msgstr '):
            mode = 'msgstr'
            msgstr_parts = [_unquote_po_string(line[len('msgstr '):])]
            continue

        if line.startswith('"'):
            if mode == 'msgid':
                msgid_parts.append(_unquote_po_string(line))
            elif mode == 'msgstr':
                msgstr_parts.append(_unquote_po_string(line))
            continue

    flush()
    entries.pop('', None)
    return entries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--translations-dir', default='src/translations')
    parser.add_argument('--locales', nargs='*', default=None)
    parser.add_argument('--exclude-locales', nargs='*', default=[])
    parser.add_argument('--mode', choices=['strict', 'parity'], default='strict')
    parser.add_argument('--reference-locale', default='de')
    parser.add_argument('--output', default=None, help='Write report to a UTF-8 file')
    args = parser.parse_args()

    translations_dir = Path(args.translations_dir)
    if not translations_dir.exists():
        print(f"Translations directory not found: {translations_dir}")
        return 1

    locales = args.locales
    if not locales:
        locales = sorted([p.name for p in translations_dir.iterdir() if p.is_dir()])

    exclude = set(args.exclude_locales or [])

    missing: list[Missing] = []

    if args.mode == 'strict':
        for locale in locales:
            if locale in exclude:
                continue
            po_path = translations_dir / locale / 'LC_MESSAGES' / 'messages.po'
            if not po_path.exists():
                continue
            entries = parse_po_entries(po_path)
            for msgid, msgstr in entries.items():
                if msgstr.strip() == '':
                    missing.append(Missing(locale=locale, msgid=msgid))
    else:
        ref_locale = args.reference_locale
        ref_path = translations_dir / ref_locale / 'LC_MESSAGES' / 'messages.po'
        if not ref_path.exists():
            print(f"Reference locale messages.po not found: {ref_path}")
            return 1

        ref_entries = parse_po_entries(ref_path)
        ref_required = {msgid for msgid, msgstr in ref_entries.items() if msgstr.strip() != ''}

        for locale in locales:
            if locale == ref_locale or locale in exclude:
                continue
            po_path = translations_dir / locale / 'LC_MESSAGES' / 'messages.po'
            if not po_path.exists():
                continue
            entries = parse_po_entries(po_path)
            for msgid in ref_required:
                if entries.get(msgid, '').strip() == '':
                    missing.append(Missing(locale=locale, msgid=msgid))

    if missing:
        if args.output:
            _write_report(Path(args.output), missing)
        _safe_print(f"Missing translations: {len(missing)}")
        for m in missing[:200]:
            _safe_print(f"[{m.locale}] {m.msgid}")
        if len(missing) > 200:
            _safe_print(f"... and {len(missing) - 200} more")
        return 1

    _safe_print("OK: no missing translations")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
