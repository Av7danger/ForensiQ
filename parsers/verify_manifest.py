"""
verify_manifest.py — Helper to verify SHA256 of blobs against manifest
"""
import sys
import json
import hashlib
from pathlib import Path

def verify_manifest(manifest_path: Path, blobs_dir: Path) -> None:
    """Verifies SHA256 of all blobs listed in manifest."""
    count = 0
    with manifest_path.open() as f:
        for line in f:
            obj = json.loads(line)
            sha = obj['sha256']
            ext = Path(obj['blob_path']).suffix
            blob_file = blobs_dir / f"{sha}{ext}"
            if not blob_file.exists():
                print(f"Missing blob: {blob_file}")
                continue
            h = hashlib.sha256()
            with blob_file.open('rb') as bf:
                for chunk in iter(lambda: bf.read(65536), b''):
                    h.update(chunk)
            if h.hexdigest() != sha:
                print(f"SHA256 mismatch: {blob_file}")
            else:
                count += 1
    print(f"Verified {count} blobs.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python verify_manifest.py <manifest.jsonl> <blobs_dir>")
        sys.exit(1)
    verify_manifest(Path(sys.argv[1]), Path(sys.argv[2]))
