# Storage Atlas

Scan a folder or drive and explore its largest files and folders in an interactive, offline storage map. The Python launcher opens a native folder picker; the generated HTML report opens automatically in your default browser. No data is uploaded.

## Run

Install Python 3.9 or newer, including Tkinter (on some Linux distributions, install the `python3-tk` system package). No third-party Python packages or web services are required.

```sh
python storage_atlas.py
```

Choose a drive or folder, then click **Scan and open map**. The report is saved as `StorageAtlas-report.html` in your home directory; subsequent scans overwrite it. Click folders in the map or list to explore, and use the filter to find an item in the current folder.

For command-line use:

```sh
python storage_atlas.py /path/to/folder
python storage_atlas.py /path/to/folder -o /path/to/report.html --no-open
```

On Windows, for example, use `python storage_atlas.py C:\` to scan the C drive. Full-drive scans can take time and substantial memory. The report includes filenames and folder names, so treat it as private information when sharing it.

Sizes reflect logical file sizes, not necessarily the actual disk space allocated (for example, compressed or sparse files). Symbolic links and Windows junctions are skipped to avoid loops. Inaccessible items are counted and excluded, so totals can be lower than the drive's used space. System and application data should be reviewed carefully before deletion.
