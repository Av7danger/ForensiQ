# UFDR Parser — README

## Requirements
- Python 3.11+
- Standard library only (optional: `tqdm` for progress bars)

## Usage
Run the parser from the command line:

```
python parsers/ufdr_parser.py <input.ufdr_or_folder> <outdir> <case_id>
```

- `<input.ufdr_or_folder>`: Path to Cellebrite UFDR file (.ufdr/.zip) or already-unpacked folder
- `<outdir>`: Output directory for parsed data
- `<case_id>`: Unique case identifier

## Output Structure
```
<outdir>/<case_id>/raw/           # Unpacked UFDR contents
<outdir>/<case_id>/parsed/
    messages.jsonl                # One JSON object per message
    contacts.jsonl                # One JSON object per contact
    calls.jsonl                   # One JSON object per call
    blobs_manifest.jsonl          # Manifest of all extracted blobs
<outdir>/<case_id>/blobs/         # All extracted blobs, named by SHA256
```

## Example
```
python parsers/ufdr_parser.py sample.ufdr output_dir CASE-001
```

## Verifying Blobs
You can verify blob integrity using the manifest:

```
python parsers/verify_manifest.py <outdir>/<case_id>/parsed/blobs_manifest.jsonl <outdir>/<case_id>/blobs/
```

## Example verify_manifest.py pseudocode
```python
import sys, json, hashlib, pathlib
manifest = pathlib.Path(sys.argv[1])
blobs_dir = pathlib.Path(sys.argv[2])
for line in manifest.open():
    obj = json.loads(line)
    blob_path = blobs_dir / f"{obj['sha256']}{pathlib.Path(obj['blob_path']).suffix}"
    h = hashlib.sha256()
    with blob_path.open('rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    assert h.hexdigest() == obj['sha256'], f"Mismatch: {blob_path}"
print("All blobs verified.")
```

## Notes
- If `report.xml` is missing, the parser will use the first `.xml` file and log a warning.
- Re-running the parser is idempotent: no duplicate blobs, manifest is rewritten cleanly.
- Logging is provided at INFO/WARNING/ERROR levels.

---
Parser Engineer (Member2)
