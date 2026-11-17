#!/usr/bin/env python3
"""Scan a folder and create an offline, interactive storage map."""
import argparse
import datetime
import json
import os
from pathlib import Path
import sys
import threading
import time
import webbrowser

HERE = Path(__file__).resolve().parent


def scan(root, progress=lambda *_: None, excluded=None):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError(f"Not a directory: {root}")
    excluded = Path(excluded).resolve() if excluded else None
    errors = count = 0
    tree = {"name": root.name or str(root), "size": 0, "children": []}
    stack = [(root, tree, False)]
    while stack:
        path, node, visited = stack.pop()
        if visited:
            node["size"] = sum(item["size"] for item in node["children"])
            node["children"].sort(key=lambda item: item["size"], reverse=True)
            continue
        stack.append((path, node, True))
        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    try:
                        info = entry.stat(follow_symlinks=False)
                        if entry.is_symlink() or (os.name == "nt" and info.st_file_attributes & 1024):
                            continue
                        if excluded and Path(entry.path).absolute() == excluded:
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            child = {"name": entry.name, "size": 0, "children": []}
                            node["children"].append(child)
                            stack.append((Path(entry.path), child, False))
                        elif entry.is_file(follow_symlinks=False):
                            node["children"].append({"name": entry.name, "size": info.st_size})
                            count += 1
                            if count % 1000 == 0:
                                progress(count, errors, str(path))
                    except OSError:
                        errors += 1
        except OSError:
            errors += 1
    return tree, count, errors


def generate(root, output, progress=lambda *_: None):
    output = Path(output).expanduser().resolve()
    tree, count, errors = scan(root, progress, output)
    data = {"tree": tree, "root": str(Path(root).resolve()), "files": count,
            "errors": errors, "generated": datetime.datetime.now().astimezone().isoformat(timespec="seconds")}
    payload = json.dumps(data, ensure_ascii=True, separators=(",", ":")).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    template = (HERE / "viewer.html").read_text(encoding="utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(template.replace("/* STORAGE_ATLAS_DATA */", payload), encoding="utf-8")
    return output, count, errors


def gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    app = tk.Tk()
    app.title("Storage Atlas")
    app.geometry("620x310")
    app.minsize(540, 290)
    frame = ttk.Frame(app, padding=24)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="Storage Atlas", font=("Segoe UI", 20, "bold")).pack(anchor="w")
    ttk.Label(frame, text="Explore your disk as an interactive 3D storage map.").pack(anchor="w", pady=(4, 20))
    path = tk.StringVar(value=str(Path.home()))
    row = ttk.Frame(frame); row.pack(fill="x")
    ttk.Entry(row, textvariable=path).pack(side="left", fill="x", expand=True)
    ttk.Button(row, text="Choose folder…", command=lambda: path.set(filedialog.askdirectory(initialdir=path.get()) or path.get())).pack(side="left", padx=(8, 0))
    status = tk.StringVar(value="Choose a drive or folder, then start the scan.")
    ttk.Label(frame, textvariable=status, wraplength=550).pack(anchor="w", pady=18)
    ttk.Label(frame, text="The report is saved to your home folder and opens in your browser.").pack(anchor="w")
    def start():
        target = path.get().strip()
        button.configure(state="disabled")
        status.set("Scanning… this may take a while for a whole drive.")
        def worker():
            try:
                out = Path.home() / "StorageAtlas-report.html"
                last = [0.0]
                def update(count, errors, current):
                    if time.monotonic() - last[0] > 0.5:
                        last[0] = time.monotonic()
                        app.after(0, lambda: status.set(f"Scanned {count:,} files · {errors:,} inaccessible items\n{current}"))
                result, count, errors = generate(target, out, update)
                def done():
                    button.configure(state="normal")
                    status.set(f"Done: {count:,} files, {errors:,} inaccessible items. Saved to {result}")
                    webbrowser.open(result.as_uri())
                app.after(0, done)
            except Exception as exc:
                message = str(exc)
                def failed():
                    button.configure(state="normal"); status.set("Scan failed."); messagebox.showerror("Storage Atlas", message)
                app.after(0, failed)
        threading.Thread(target=worker, daemon=True).start()
    button = ttk.Button(frame, text="Scan and open map", command=start); button.pack(anchor="w", pady=(16, 0))
    app.mainloop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", help="Folder or drive to scan; omit to use the graphical launcher")
    parser.add_argument("-o", "--output", default=str(Path.home() / "StorageAtlas-report.html"))
    parser.add_argument("--no-open", action="store_true", help="Do not open the report in a browser")
    args = parser.parse_args()
    if not args.path:
        gui(); return
    try:
        output, count, errors = generate(args.path, args.output, lambda n, e, p: print(f"\r{n:,} files; {e:,} inaccessible", end="", flush=True))
        print(f"\nSaved {output} ({count:,} files, {errors:,} inaccessible)")
        if not args.no_open: webbrowser.open(output.as_uri())
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr); sys.exit(1)


if __name__ == "__main__":
    main()
