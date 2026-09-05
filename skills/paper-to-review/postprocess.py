#!/usr/bin/env python3
"""
paper-to-review post-processor
Usage: python postprocess.py <output_dir> [file.md ...]
If no files given, processes all *.md in output_dir.
"""
import re, os, json, sys
from pathlib import Path

# --- Subscript pattern sets ---

# Set A: underscore notation  V_DD, I_t2  (translation files)
PATTERNS_UNDERSCORE = [
    (r'\bV_DD1\b', 'V<sub>DD1</sub>'),
    (r'\bV_DD2\b', 'V<sub>DD2</sub>'),
    (r'\bV_DD\b',  'V<sub>DD</sub>'),
    (r'\bV_SS\b',  'V<sub>SS</sub>'),
    (r'\bV_BD\b',  'V<sub>BD</sub>'),
    (r'\bV_t1\b',  'V<sub>t1</sub>'),
    (r'\bV_h\b',   'V<sub>h</sub>'),
    (r'\bV_clamp\b', 'V<sub>clamp</sub>'),
    (r'\bR_on\b',  'R<sub>on</sub>'),
    (r'\bI_t2\b',  'I<sub>t2</sub>'),
    (r'\bI_ESD\b', 'I<sub>ESD</sub>'),
    (r'\bC_ESD\b', 'C<sub>ESD</sub>'),
    (r'\bL_1\b',   'L<sub>1</sub>'),
    (r'\bL_2\b',   'L<sub>2</sub>'),
    (r'\bD_p\b',   'D<sub>p</sub>'),
    (r'\bD_n\b',   'D<sub>n</sub>'),
]

# Set B: no-underscore notation  VDD, Vt1  (notes files)
PATTERNS_NOUNDERSCORE = [
    (r'\bVDD1\b',   'V<sub>DD1</sub>'),
    (r'\bVDD2\b',   'V<sub>DD2</sub>'),
    (r'\bVDD\b',    'V<sub>DD</sub>'),
    (r'\bVSS\b',    'V<sub>SS</sub>'),
    (r'\bVBD\b',    'V<sub>BD</sub>'),
    (r'\bVt1\b',    'V<sub>t1</sub>'),
    (r'\bVh\b',     'V<sub>h</sub>'),
    (r'\bVclamp\b', 'V<sub>clamp</sub>'),
    (r'\bRon\b',    'R<sub>on</sub>'),
    (r'\bIt2\b',    'I<sub>t2</sub>'),
    (r'\bIESD\b',   'I<sub>ESD</sub>'),
]

# --- CSS content ---

VSCODE_CSS = """\
/* paper-to-md: VS Code Markdown Preview */
body, .markdown-body {
  background: #ffffff !important;
  color: #1a1a1a !important;
  max-width: 960px;
  margin: 0 auto;
  padding: 2rem;
  font-family: 'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', 'Segoe UI', sans-serif;
  line-height: 1.8;
}
h1 { border-bottom: 2px solid #333; padding-bottom: 0.3em; color: #111 !important; }
h2 { border-bottom: 1px solid #ccc; padding-bottom: 0.2em; color: #222 !important; }
h3, h4, h5 { color: #333 !important; }
blockquote {
  background: #f7f7f7 !important;
  color: #444 !important;
  border-left: 4px solid #888;
  padding: 0.6rem 1rem;
  margin: 1rem 0;
  border-radius: 0 4px 4px 0;
}
table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
th { background: #e8e8e8 !important; color: #111 !important; font-weight: 600; }
td, th { border: 1px solid #ccc; padding: 0.5rem 0.8rem; }
tr:nth-child(even) { background: #f9f9f9 !important; }
code {
  background: #f0f0f0 !important; color: #c7254e !important;
  padding: 0.15em 0.4em; border-radius: 3px; font-size: 0.9em;
}
pre {
  background: #f8f8f8 !important; padding: 1rem;
  overflow-x: auto; border: 1px solid #ddd; border-radius: 4px;
}
pre code { background: none !important; color: #333 !important; padding: 0; }
img {
  max-width: 100%; height: auto; display: inline-block; vertical-align: top;
  margin: 1rem 0.5%; border: 1px solid #eee; border-radius: 4px;
}
"""

OBSIDIAN_CSS = """\
/* paper-to-md: Obsidian CSS snippet
   Enable in: Settings -> Appearance -> CSS snippets */
.theme-light .markdown-reading-view .markdown-preview-section,
.theme-dark  .markdown-reading-view .markdown-preview-section {
  background: #ffffff;
  color: #1a1a1a;
  max-width: 960px;
}
.markdown-reading-view h1,
.markdown-reading-view h2,
.markdown-reading-view h3,
.markdown-reading-view h4 { color: #1a1a1a; }
.markdown-reading-view table { background: #ffffff; }
.markdown-reading-view th   { background: #e8e8e8; }
.markdown-reading-view tr:nth-child(even) { background: #f9f9f9; }
"""


# --- Core processing functions ---

def _protect_code_blocks(text):
    """Replace code blocks with placeholders; return (protected_text, map)."""
    placeholders = {}
    counter = [0]

    def save(m):
        key = f'\x00BLOCK{counter[0]}\x00'
        counter[0] += 1
        placeholders[key] = m.group(0)
        return key

    text = re.sub(r'(`{3,}|~{3,})[\s\S]*?\1', save, text)
    text = re.sub(r'`[^`\n]+`', save, text)
    return text, placeholders


def _restore_code_blocks(text, placeholders):
    for key, val in placeholders.items():
        text = text.replace(key, val)
    return text


def convert_subscripts(text, patterns):
    protected, pm = _protect_code_blocks(text)
    for pat, rep in patterns:
        protected = re.sub(pat, rep, protected)
    return _restore_code_blocks(protected, pm)


def remove_style_tags(text):
    return re.sub(r'<style>[\s\S]*?</style>\s*\n?', '', text)


def process_file(path):
    p = Path(path)
    if not p.exists():
        print(f'  [skip] not found: {p}')
        return

    text = p.read_text(encoding='utf-8')
    original = text

    text = remove_style_tags(text)

    # Auto-detect notation style and apply matching patterns
    if re.search(r'\bV_DD\b|\bI_t2\b|\bR_on\b', text):
        text = convert_subscripts(text, PATTERNS_UNDERSCORE)
    if re.search(r'\bVDD\b|\bVt1\b|\bIESD\b|\bRon\b', text):
        text = convert_subscripts(text, PATTERNS_NOUNDERSCORE)

    if text != original:
        p.write_text(text, encoding='utf-8')
        print(f'  [updated] {p.name}')
    else:
        print(f'  [no change] {p.name}')


def generate_css(output_dir):
    out = Path(output_dir)
    (out / 'vscode-markdown.css').write_text(VSCODE_CSS, encoding='utf-8')
    print(f'  [ok] vscode-markdown.css')
    (out / 'obsidian-snippet.css').write_text(OBSIDIAN_CSS, encoding='utf-8')
    print(f'  [ok] obsidian-snippet.css')


def update_vscode_settings(output_dir):
    vd = Path(output_dir) / '.vscode'
    vd.mkdir(exist_ok=True)
    sp = vd / 'settings.json'
    settings = {}
    if sp.exists():
        try:
            settings = json.loads(sp.read_text(encoding='utf-8'))
        except Exception:
            settings = {}
    settings['markdown.styles'] = ['../vscode-markdown.css']
    sp.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'  [ok] .vscode/settings.json')


def main():
    sys.stdout.reconfigure(encoding='utf-8')

    if len(sys.argv) < 2:
        print('Usage: postprocess.py <output_dir> [file.md ...]')
        print('  If no files specified, all *.md in output_dir are processed.')
        sys.exit(1)

    output_dir = sys.argv[1]
    files = sys.argv[2:] if len(sys.argv) > 2 else list(Path(output_dir).glob('*.md'))

    print('=== paper-to-review postprocess ===')
    for f in files:
        process_file(str(f))

    generate_css(output_dir)
    update_vscode_settings(output_dir)

    print('\n=== done ===')
    print('Obsidian white-bg setup (manual):')
    print('  Settings -> Appearance -> CSS snippets -> open folder')
    print('  Copy obsidian-snippet.css there, then toggle it ON.')


if __name__ == '__main__':
    main()
