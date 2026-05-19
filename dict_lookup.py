#!/usr/bin/env python3
"""
dict_lookup.py  —  Interactive MFA dictionary lookup

Type a word to see its ARPA/IPA pronunciation(s).
Press Ctrl+C to exit.

Usage:
    python3 dict_lookup.py english_mfa
"""

import argparse
import os
import re
import sys
import difflib
from collections import defaultdict

# Search inside these directories for main dictionaries
DEFAULT_DICT_DIRS = [
    os.path.expanduser("~/Documents/MFA/pretrained_models/dictionary"),
    os.path.expanduser("~/.local/share/montreal-forced-aligner/pretrained_models/dictionary"),
]

def get_available_dicts() -> dict:
    """Finds all .dict files in default MFA folders and returns a name -> path mapping."""
    available = {}
    for directory in DEFAULT_DICT_DIRS:
        if os.path.isdir(directory):
            for filename in os.listdir(directory):
                if filename.endswith(".dict"):
                    if filename not in available:
                        available[filename] = os.path.join(directory, filename)
    return available

def load_dictionary(dict_path: str, tag: str = None) -> defaultdict:
    """Return {word: [(pronunciation, tag), ...]} with all variants."""
    entries = defaultdict(list)
    with open(dict_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            word = parts[0].lower()
            word = re.sub(r"\(\d+\)$", "", word)
            pronunciation = " ".join(parts[1:])
            entries[word].append((pronunciation, tag))
    return entries

def main():
    parser = argparse.ArgumentParser(description="Interactive MFA dictionary lookup")
    parser.add_argument("dict_name", nargs="?", default=None,
        help="Name of the dictionary to load (e.g., english_mfa)")
    args = parser.parse_args()

    available_dicts = get_available_dicts()

    if not args.dict_name:
        print("Usage error: A dictionary name is required.\n")
        print("Available dictionaries in default locations:")
        if available_dicts:
            for name in sorted(available_dicts.keys()):
                print(f"  - {name.replace('.dict', '')}")
        else:
            print("  (No .dict files found in default MFA directories)")
        sys.exit(1)

    dict_input = args.dict_name
    dict_name = dict_input if dict_input.endswith(".dict") else f"{dict_input}.dict"

    if dict_name in available_dicts:
        dict_path = available_dicts[dict_name]
    elif os.path.isfile(dict_input):
        dict_path = dict_input
        dict_name = os.path.basename(dict_path)
    else:
        sys.exit(f"Error: Dictionary '{dict_name}' not found.")

    print(f"Loading dictionary from:\n  {dict_path}")
    entries = load_dictionary(dict_path)
    print(f"  {len(entries):,} words loaded.")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    custom_folder = os.path.join(script_dir, "dictionaries")
    if not os.path.isdir(custom_folder):
        os.makedirs(custom_folder, exist_ok=True)

    custom_dict_name = f"custom.{dict_name}"
    custom_path = os.path.join(custom_folder, custom_dict_name)
    
    if os.path.isfile(custom_path):
        print(f"\nLoading custom dictionary from:\n  {custom_path}")
        custom_entries = load_dictionary(custom_path, tag="custom")
        for word, pronunciations in custom_entries.items():
            entries[word] = pronunciations + [
                p for p in entries.get(word, []) if p not in pronunciations
            ]
        print(f"  {len(custom_entries):,} custom word(s) loaded.")

    print("\nType a word to look it up. Press Ctrl+C to exit.\n")

    while True:
        try:
            word = input("> ").strip().lower()
            if not word:
                continue
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        pronunciations = entries.get(word)
        if pronunciations:
            for pronunciation, tag in pronunciations:
                tag_str = f"  [custom]" if tag else ""
                print(f"  {word}  ->  {pronunciation}{tag_str}")
        else:
            print(f"  '{word}' not found.")
            suggestions = difflib.get_close_matches(word, entries.keys(), n=3, cutoff=0.6)
            if suggestions:
                print(f"  Did you mean: {', '.join(suggestions)}?")

if __name__ == "__main__":
    main()