import pytest
import tempfile
import zipfile
import shutil
import json
from pathlib import Path
from parsers.ufdr_parser import run_parser, sha256_file

def build_synthetic_ufdr(tmp_path: Path) -> Path:
    """Creates a minimal UFDR zip with report.xml and a sample image."""
    ufdr_dir = tmp_path / "ufdr"
    ufdr_dir.mkdir()
    # Create report.xml
    xml = '''<report>
  <messages>
    <message id="m1">
      <timestamp>1694505300000</timestamp>
      <sender>+919812345678</sender>
      <recipient>+447700900000</recipient>
      <body>Payment to 0xAbC123... successful</body>
      <attachment>media/IMG_001.jpg</attachment>
    </message>
  </messages>
  <contacts>
    <contact>
      <name>John Doe</name>
      <phone>+919876543210</phone>
    </contact>
  </contacts>
  <calls>
    <call>
      <timestamp>1694505400</timestamp>
      <caller>+919876543210</caller>
      <callee>+919812345678</callee>
      <duration>42</duration>
    </call>
  </calls>
</report>'''
    (ufdr_dir / "report.xml").write_text(xml, encoding="utf-8")
    # Create media folder and sample image
    media_dir = ufdr_dir / "media"
    media_dir.mkdir()
    img_path = media_dir / "IMG_001.jpg"
    img_bytes = b"\xff\xd8\xff\xe0" + b"testimage"  # JPEG header + dummy
    img_path.write_bytes(img_bytes)
    # Zip it
    ufdr_zip = tmp_path / "test.ufdr"
    with zipfile.ZipFile(ufdr_zip, 'w') as z:
        for file in ufdr_dir.rglob("*"):
            z.write(file, file.relative_to(ufdr_dir))
    return ufdr_zip

def test_parser_creates_outputs(tmp_path):
    ufdr_zip = build_synthetic_ufdr(tmp_path)
    outdir = tmp_path / "output"
    case_id = "CASE-TEST"
    summary = run_parser(ufdr_zip, outdir, case_id)
    parsed = Path(summary['messages']['path']).parent
    blobs_dir = outdir / case_id / "blobs"
    # Check output files
    assert (parsed / "messages.jsonl").exists()
    assert (parsed / "blobs_manifest.jsonl").exists()
    # Check manifest SHA256 matches blob
    manifest_lines = list((parsed / "blobs_manifest.jsonl").open())
    assert manifest_lines, "Manifest should not be empty"
    for line in manifest_lines:
        obj = json.loads(line)
        blob_file = blobs_dir / f"{obj['sha256']}{Path(obj['blob_path']).suffix}"
        assert blob_file.exists(), f"Blob file missing: {blob_file}"
        sha, size = sha256_file(blob_file)
        assert sha == obj['sha256'], f"SHA256 mismatch for {blob_file}"
        assert size == obj['size_bytes'], f"Size mismatch for {blob_file}"
    # Check messages.jsonl contains raw_source and hash
    msg_lines = list((parsed / "messages.jsonl").open())
    assert msg_lines, "Messages should not be empty"
    for line in msg_lines:
        msg = json.loads(line)
        assert 'raw_source' in msg
        assert 'hash' in msg

def test_idempotency(tmp_path):
    ufdr_zip = build_synthetic_ufdr(tmp_path)
    outdir = tmp_path / "output"
    case_id = "CASE-TEST"
    # First run
    run_parser(ufdr_zip, outdir, case_id)
    # Second run
    run_parser(ufdr_zip, outdir, case_id)
    blobs_dir = outdir / case_id / "blobs"
    # Should be no duplicate blobs
    files = list(blobs_dir.glob("*"))
    shas = set(f.stem for f in files)
    assert len(files) == len(shas), "Duplicate blobs detected"
