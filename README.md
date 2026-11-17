# Storage Atlas

Scan a folder or drive and explore it as an interactive, offline storage galaxy. Each item is a cube: its volume is proportional to its logical size, so the largest objects stand out. The Python launcher opens a native folder picker; the generated HTML report opens automatically in your default browser. No data is uploaded.

## Run

Install Python 3.9 or newer, including Tkinter (on some Linux distributions, install the `python3-tk` system package). No third-party Python packages or web services are required.

```sh
python storage_atlas.py
```

Choose a drive or folder, then click **Scan and open map**. The report is saved as `StorageAtlas-report.html` in your home directory; subsequent scans overwrite it. Click a folder cube to enter it. Right-click or press Backspace to go back, and scroll or use Page Up/Page Down to see more objects. Arrow keys select objects and Enter opens a folder. Items are shown largest first, 40 per page. The tiny marker for an empty item is an exception to proportional sizing; very small cubes can be selected with the keyboard. Reduced-motion preferences disable the travel and star animations.

The dark launcher shows live file and inaccessible-item counts, elapsed time, and an activity indicator. The indicator does not estimate a percentage because the number of files is unknown until the scan finishes. It uses an available system font, so no font download is required.

For command-line use:

```sh
python storage_atlas.py /path/to/folder
python storage_atlas.py /path/to/folder -o /path/to/report.html --no-open
```

On Windows, for example, use `python storage_atlas.py C:\` to scan the C drive. Full-drive scans can take time and substantial memory. The report includes filenames and folder names, so treat it as private information when sharing it.

Sizes reflect logical file sizes, not necessarily the actual disk space allocated (for example, compressed or sparse files). Symbolic links and Windows junctions are skipped to avoid loops. Inaccessible items are counted and excluded, so totals can be lower than the drive's used space. System and application data should be reviewed carefully before deletion.
