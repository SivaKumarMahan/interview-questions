"""MkDocs build hooks for the docs site. Source files are not changed.

1. Answers sit inside <details> blocks. GitHub renders the Markdown inside them, but
   Python-Markdown only does so when the tag has markdown="1", so it is added at build time.
2. Most folders have no README.md, so a simple index page listing the folder's files
   is generated for each of them. That makes links such as "kubernetes/" work on the site.
"""
import os
import re

from mkdocs.structure.files import File

FENCE = re.compile(r"^\s*(```|~~~)")


def on_page_markdown(markdown, page, config, files):
    out, in_fence = [], False
    for line in markdown.split("\n"):
        if FENCE.match(line):
            in_fence = not in_fence
        if not in_fence and line.startswith("<details>"):
            line = '<details markdown="1">' + line[len("<details>"):]
        out.append(line)
    return "\n".join(out)


def _title(abs_path, fallback):
    try:
        with open(abs_path, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("# "):
                    return line[2:].strip()
    except OSError:
        pass
    return fallback


def on_files(files, config):
    pages = [f for f in files if f.src_uri.endswith(".md")]
    folders = {}
    for f in pages:
        parts = f.src_uri.split("/")
        for depth in range(1, len(parts)):
            folders.setdefault("/".join(parts[:depth]), set())
        if len(parts) > 1:
            folders["/".join(parts[:-1])].add(f)

    for folder, members in sorted(folders.items()):
        names = {os.path.basename(m.src_uri).lower() for m in members}
        if "readme.md" in names or "index.md" in names:
            continue
        name = folder.split("/")[-1]
        lines = [f"# {name}", "", "Files in this folder:", ""]
        for m in sorted(members, key=lambda m: m.src_uri):
            base = os.path.basename(m.src_uri)
            lines.append(f"- [{_title(m.abs_src_path, base)}]({base})")
        subs = sorted(k for k in folders if k.startswith(folder + "/") and k.count("/") == folder.count("/") + 1)
        if subs:
            lines += ["", "Subfolders:", ""] + [f"- [{s.split('/')[-1]}]({s.split('/')[-1]}/)" for s in subs]
        files.append(File.generated(config, f"{folder}/index.md", content="\n".join(lines) + "\n"))
    return files
