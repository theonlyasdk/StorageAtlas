#!/usr/bin/env python3
"""Scan a folder and create an offline, interactive storage map."""
import argparse
import datetime
import json
import os
import queue
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
    from tkinter import filedialog, font, messagebox, ttk

    app = tk.Tk()
    app.title("Storage Atlas")
    app.geometry("720x660")
    app.minsize(620, 600)
    app.configure(bg="#090e1c")
    app.option_add("*tearOff", False)
    families = set(font.families())
    family = next((name for name in ("Inter", "Segoe UI", "Avenir Next", "DejaVu Sans") if name in families), "TkDefaultFont")
    bg, panel, ink, muted, accent = "#090e1c", "#121c30", "#eff6ff", "#92a7c5", "#75dfec"
    style = ttk.Style(app)
    style.theme_use("clam")
    style.configure("Galaxy.Horizontal.TProgressbar", troughcolor="#202f48", background=accent,
                    bordercolor="#202f48", lightcolor=accent, darkcolor=accent, thickness=6)
    events = queue.Queue()
    path = tk.StringVar(value=str(Path.home()))
    headline = tk.StringVar(value="Ready to explore")
    detail = tk.StringVar(value="Choose a folder or drive to begin your scan.")
    files = tk.StringVar(value="?")
    skipped = tk.StringVar(value="?")
    elapsed = tk.StringVar(value="?")
    started = None
    scanning = False

    def label(parent, text=None, variable=None, size=10, color=ink, bold=False, background=None, **kwargs):
        return tk.Label(parent, text=text, textvariable=variable, bg=background or parent.cget("bg"), fg=color,
                        font=(family, size, "bold" if bold else "normal"), anchor="w", **kwargs)

    def button(parent, text, command, primary=False):
        normal = accent if primary else "#243550"
        active = "#a1f0f5" if primary else "#344967"
        return tk.Button(parent, text=text, command=command, bg=normal, fg="#07131d" if primary else ink,
                         activebackground=active, activeforeground="#07131d" if primary else ink,
                         disabledforeground="#66768b", relief="flat", bd=0, padx=20, pady=10,
                         cursor="hand2", font=(family, 10, "bold"), highlightthickness=0)

    outer = tk.Frame(app, bg=bg, padx=34, pady=24)
    outer.pack(fill="both", expand=True)
    brand = tk.Frame(outer, bg=bg)
    brand.pack(fill="x")
    label(brand, "?", size=24, color=accent).pack(side="left", padx=(0, 12))
    label(brand, "STORAGE ATLAS", size=10, bold=True).pack(side="left")
    label(brand, "YOUR FILES, IN PERSPECTIVE", size=8, color=muted).pack(side="right")
    label(outer, "Explore your space.", size=25, bold=True).pack(anchor="w", pady=(26, 4))
    label(outer, "Turn your files into a galaxy you can navigate.", size=10, color=muted).pack(anchor="w")

    card = tk.Frame(outer, bg=panel, padx=22, pady=20, highlightbackground="#263650", highlightthickness=1)
    card.pack(fill="both", expand=True, pady=(24, 14))
    label(card, "SCAN LOCATION", size=9, color=accent, bold=True).pack(anchor="w")
    label(card, "Where should we look?", size=14, bold=True).pack(anchor="w", pady=(6, 12))
    row = tk.Frame(card, bg=panel)
    row.pack(fill="x")
    entry = tk.Entry(row, textvariable=path, bg="#0b1424", fg=ink, insertbackground=ink,
                     relief="flat", font=(family, 10), highlightthickness=1,
                     highlightbackground="#344560", highlightcolor=accent)
    entry.pack(side="left", fill="x", expand=True, ipady=11)
    def choose():
        selected = filedialog.askdirectory(parent=app, initialdir=path.get() if os.path.isdir(path.get()) else str(Path.home()))
        if selected:
            path.set(selected)
    browse = button(row, "Browse", choose)
    browse.pack(side="left", padx=(9, 0))
    label(card, "Your scan stays on this device.", size=9, color=muted).pack(anchor="w", pady=(9, 0))
    tk.Frame(card, bg="#283952", height=1).pack(fill="x", pady=20)
    label(card, variable=headline, size=13, bold=True).pack(anchor="w")
    detail_label = label(card, variable=detail, size=9, color=muted, wraplength=550, justify="left")
    detail_label.pack(anchor="w", fill="x", pady=(5, 14))
    progress = ttk.Progressbar(card, style="Galaxy.Horizontal.TProgressbar", mode="indeterminate")
    progress.pack(fill="x")
    label(card, "Progress is activity-based; the total number of files is not known in advance.",
          size=8, color=muted, wraplength=550, justify="left").pack(anchor="w", pady=(8, 0))
    stats = tk.Frame(card, bg=panel)
    stats.pack(fill="x", pady=(20, 0))
    for col, (caption, value) in enumerate((("FILES SCANNED", files), ("INACCESSIBLE", skipped), ("ELAPSED", elapsed))):
        cell = tk.Frame(stats, bg=panel)
        cell.grid(row=0, column=col, sticky="w")
        stats.grid_columnconfigure(col, weight=1)
        label(cell, caption, size=8, color=muted, bold=True).pack(anchor="w")
        label(cell, variable=value, size=15, bold=True).pack(anchor="w", pady=(4, 0))
    footer = tk.Frame(outer, bg=bg)
    footer.pack(fill="x")
    label(footer, "The report opens in your browser when ready.", size=9, color=muted,
          wraplength=330, justify="left").pack(side="left", fill="x", expand=True)

    def set_busy(value):
        state = "disabled" if value else "normal"
        run.configure(state=state)
        browse.configure(state=state)
        entry.configure(state=state)
        if value:
            progress.start(12)
        else:
            progress.stop()

    def start():
        nonlocal started, scanning
        target = path.get().strip()
        if not os.path.isdir(target):
            messagebox.showerror("Invalid location", "Choose an existing folder or drive to scan.", parent=app)
            return
        scanning = True
        started = time.monotonic()
        files.set("0"); skipped.set("0"); elapsed.set("0s")
        headline.set("Scanning your space?")
        detail.set("Finding files and calculating folder sizes.")
        set_busy(True)
        def worker():
            try:
                last = [0.0]
                def update(count, errors, current):
                    now = time.monotonic()
                    if now - last[0] >= 0.3:
                        last[0] = now
                        events.put(("progress", count, errors, current))
                result = generate(target, Path.home() / "StorageAtlas-report.html", update)
                events.put(("done", *result))
            except Exception as exc:
                events.put(("error", str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    run = button(footer, "Start scanning  ?", start, primary=True)
    run.pack(side="right", padx=(12, 0))

    def poll():
        nonlocal scanning
        if scanning and started is not None:
            seconds = int(time.monotonic() - started)
            elapsed.set(f"{seconds // 60}m {seconds % 60}s" if seconds >= 60 else f"{seconds}s")
        try:
            while True:
                event = events.get_nowait()
                if event[0] == "progress":
                    _, count, errors, current = event
                    files.set(f"{count:,}"); skipped.set(f"{errors:,}")
                    detail.set("Scanning: " + current)
                elif event[0] == "done":
                    _, output, count, errors = event
                    scanning = False
                    set_busy(False)
                    files.set(f"{count:,}"); skipped.set(f"{errors:,}")
                    headline.set("Your galaxy is ready")
                    detail.set("Report saved to " + str(output))
                    if not webbrowser.open(output.as_uri()):
                        detail.set("Report saved to " + str(output) + ". Open it in your browser.")
                else:
                    scanning = False
                    set_busy(False)
                    headline.set("Scan could not be completed")
                    detail.set(event[1])
                    messagebox.showerror("Storage Atlas", event[1], parent=app)
        except queue.Empty:
            pass
        app.after(100, poll)

    app.after(100, poll)
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
