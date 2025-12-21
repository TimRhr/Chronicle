#!/usr/bin/env python3
"""
Compile translation files (.po -> .mo) for Chronicle.

Usage:
    python scripts/compile_translations.py

This script compiles all .po files in src/translations/ to .mo files
which are used by Flask-Babel at runtime.
"""

import os
import subprocess
import sys

from pathlib import Path

def main():
    # Get the project root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    translations_dir = os.path.join(project_root, 'src', 'translations')
    
    if not os.path.exists(translations_dir):
        print(f"Error: Translations directory not found: {translations_dir}")
        sys.exit(1)

    # Guardrail: prevent compiling incomplete translations
    if os.environ.get('CHRONICLE_I18N_SKIP_CHECK') != '1':
        check_script = Path(script_dir) / 'check_translations_complete.py'
        if check_script.exists():
            mode = os.environ.get('CHRONICLE_I18N_MODE', 'parity')
            reference_locale = os.environ.get('CHRONICLE_I18N_REFERENCE_LOCALE', 'de')
            exclude_locales = os.environ.get('CHRONICLE_I18N_EXCLUDE_LOCALES', 'en')
            exclude_args = []
            if exclude_locales.strip():
                exclude_args = ['--exclude-locales', *[x.strip() for x in exclude_locales.split(',') if x.strip()]]

            result = subprocess.run(
                [
                    sys.executable,
                    str(check_script),
                    '--translations-dir',
                    translations_dir,
                    '--mode',
                    mode,
                    '--reference-locale',
                    reference_locale,
                    *exclude_args,
                ],
                cwd=project_root,
                text=True,
            )
            if result.returncode != 0:
                print("\nTranslation completeness check failed. Set CHRONICLE_I18N_SKIP_CHECK=1 to bypass.")
                sys.exit(result.returncode)
    
    # Find all .po files and compile them
    compiled = 0
    for lang in os.listdir(translations_dir):
        lang_dir = os.path.join(translations_dir, lang)
        if not os.path.isdir(lang_dir):
            continue
        
        po_file = os.path.join(lang_dir, 'LC_MESSAGES', 'messages.po')
        mo_file = os.path.join(lang_dir, 'LC_MESSAGES', 'messages.mo')
        
        if os.path.exists(po_file):
            print(f"Compiling {lang}...")
            try:
                # Use pybabel to compile
                result = subprocess.run(
                    ['pybabel', 'compile', '-d', translations_dir, '-l', lang],
                    capture_output=True,
                    text=True,
                    cwd=project_root
                )
                if result.returncode == 0:
                    print(f"  ✓ {lang} compiled successfully")
                    compiled += 1
                else:
                    print(f"  ✗ Error compiling {lang}: {result.stderr}")
            except FileNotFoundError:
                # pybabel not found, try msgfmt directly
                try:
                    result = subprocess.run(
                        ['msgfmt', '-o', mo_file, po_file],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        print(f"  ✓ {lang} compiled successfully (msgfmt)")
                        compiled += 1
                    else:
                        print(f"  ✗ Error compiling {lang}: {result.stderr}")
                except FileNotFoundError:
                    print(f"  ✗ Neither pybabel nor msgfmt found. Install Flask-Babel or gettext.")
                    sys.exit(1)
    
    print(f"\nCompiled {compiled} language(s)")
    
    if compiled == 0:
        print("No .po files found to compile.")
        sys.exit(1)

if __name__ == '__main__':
    main()
