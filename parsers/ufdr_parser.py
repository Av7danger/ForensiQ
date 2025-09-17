"""
UFDR Parser — Phase 1: Ingest & Parser
Author: Parser Engineer (Member2)
Python 3.11+

Parses Cellebrite UFDR (zip or folder) and emits canonical JSONL for messages, contacts, calls, and blobs manifest.
"""
import argparse
import hashlib
import json
import logging
import os
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from xml.etree import ElementTree as ET
from datetime import datetime, timezone

# Optional: tqdm for progress bars (install via pip if desired)
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

def safe_text(node: Optional[ET.Element]) -> str:
    """Extracts text from an XML node, handling None and stripping whitespace."""
    if node is None:
        return ""
    if node.text:
        return node.text.strip()
    return ""

def strip_ns(tag: str) -> str:
    """Strips XML namespace from tag name."""
    if '}' in tag:
        return tag.split('}', 1)[1].lower()
    return tag.lower()

def find_main_xml(root: Path) -> Path:
    """Locates main XML report file (report.xml or first .xml)."""
    report = root / "report.xml"
    if report.exists():
        return report
    xmls = list(root.glob("*.xml"))
    if xmls:
        logging.warning(f"report.xml not found, using {xmls[0].name}")
        return xmls[0]
    raise FileNotFoundError("No XML report found in UFDR root.")

def unpack_ufdr(input_path: Path, outdir: Path, case_id: str) -> Path:
    """Unpacks UFDR zip to <outdir>/<case_id>/raw/. Returns raw dir path."""
    raw_dir = outdir / case_id / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    if input_path.is_dir():
        # Already unpacked
        for item in input_path.iterdir():
            dest = raw_dir / item.name
            if item.is_file():
                shutil.copy2(item, dest)
            elif item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
        return raw_dir
    # Zip file
    with zipfile.ZipFile(input_path, 'r') as z:
        z.extractall(raw_dir)
    return raw_dir

def parse_timestamp(ts: str) -> str:
    """Converts timestamp to ISO8601 UTC if possible."""
    try:
        if ts.isdigit():
            val = int(ts)
            if val > 1e12:
                # ms epoch
                dt = datetime.fromtimestamp(val / 1000, tz=timezone.utc)
                return dt.isoformat().replace('+00:00', 'Z')
            elif val > 1e9:
                # s epoch
                dt = datetime.fromtimestamp(val, tz=timezone.utc)
                return dt.isoformat().replace('+00:00', 'Z')
        # Try parsing as ISO
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
    except Exception:
        return ts

def sha256_file(path: Path, chunk_size: int = 65536) -> Tuple[str, int]:
    """Computes SHA256 and size for a file, reading in chunks."""
    h = hashlib.sha256()
    size = 0
    with path.open('rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size

def copy_blob(src: Path, dest_dir: Path, sha: str, orig_ext: str) -> Path:
    """Copies blob to dest_dir/<sha256><orig_ext> if not exists."""
    dest = dest_dir / f"{sha}{orig_ext}"
    if not dest.exists():
        with src.open('rb') as fsrc, dest.open('wb') as fdst:
            while True:
                chunk = fsrc.read(65536)
                if not chunk:
                    break
                fdst.write(chunk)
    return dest

def find_media_files(root: Path) -> List[Path]:
    """Finds files in common media folders."""
    media_dirs = ["attachments", "media", "files", "images", "videos"]
    found = []
    for d in media_dirs:
        dirpath = root / d
        if dirpath.exists() and dirpath.is_dir():
            found.extend(dirpath.rglob("*"))
    return [f for f in found if f.is_file()]

def extract_entities(text: str) -> Dict[str, List[str]]:
    """Extracts phone numbers, crypto addresses, and URLs from text."""
    import re
    phones = re.findall(r"\+?\d{10,15}", text)
    cryptos = re.findall(r"0x[a-fA-F0-9]{6,}", text)
    urls = re.findall(r"https?://\S+", text)
    return {
        "phone_numbers": phones,
        "crypto_addresses": cryptos,
        "urls": urls,
    }

def parse_messages(
    xml_root: ET.Element,
    case_id: str,
    device_id: str,
    raw_dir: Path,
    blobs_dir: Path,
    messages_path: Path,
    blobs_manifest_path: Path,
) -> Tuple[int, int]:
    """Parses messages, copies blobs, writes JSONL. Returns (msg_count, blob_count)."""
    msg_count = 0
    blob_count = 0
    manifest_entries: Dict[str, Dict[str, Any]] = {}
    with messages_path.open('w', encoding='utf-8') as msg_out, blobs_manifest_path.open('w', encoding='utf-8') as manifest_out:
        # Find message nodes
        for parent in xml_root.iter():
            tag = strip_ns(parent.tag)
            if any(x in tag for x in ["messages", "msgs", "sms", "chats"]):
                for node in parent:
                    ntag = strip_ns(node.tag)
                    if any(x in ntag for x in ["message", "msg", "sms", "chat"]):
                        # Defensive: extract fields
                        msg_id = node.attrib.get("id") or f"msg-{msg_count+1:04d}"
                        ts = safe_text(node.find("timestamp")) or safe_text(node.find("time"))
                        ts_iso = parse_timestamp(ts) if ts else ""
                        sender = safe_text(node.find("sender")) or safe_text(node.find("from"))
                        recipient = safe_text(node.find("recipient")) or safe_text(node.find("to"))
                        body = safe_text(node.find("body")) or safe_text(node.find("text"))
                        direction = "inbound" if sender and not recipient else "outbound"
                        participants = [p for p in [sender, recipient] if p]
                        attachments = []
                        related_blob_ids = []
                        # Find attachments
                        for att in node.findall("attachment"):
                            att_path = safe_text(att)
                            if att_path:
                                abs_path = (raw_dir / att_path).resolve()
                                if abs_path.exists():
                                    sha, size = sha256_file(abs_path)
                                    ext = abs_path.suffix
                                    blob_file = copy_blob(abs_path, blobs_dir, sha, ext)
                                    attachments.append(f"{sha}{ext}")
                                    related_blob_ids.append(sha)
                                    mtime = datetime.utcfromtimestamp(abs_path.stat().st_mtime).isoformat().replace('+00:00', 'Z')
                                    # Manifest entry
                                    manifest_entries[sha] = {
                                        "blob_id": sha,
                                        "case_id": case_id,
                                        "orig_path": att_path.replace('\\', '/'),
                                        "blob_path": str(blob_file.relative_to(blobs_dir.parent)),
                                        "sha256": sha,
                                        "size_bytes": size,
                                        "mtime_utc": mtime,
                                        "related_message_ids": [msg_id],
                                    }
                                else:
                                    logging.warning(f"Attachment {att_path} not found for message {msg_id}")
                        # Message hash
                        msg_hash = hashlib.sha256(body.encode('utf-8')).hexdigest() if body else ""
                        # Entities
                        entities = extract_entities(body)
                        # Raw source
                        raw_source = f"{xml_root.tag}:{ntag}[{msg_count}]"
                        msg_obj = {
                            "id": msg_id,
                            "case_id": case_id,
                            "device_id": device_id,
                            "timestamp_utc": ts_iso,
                            "direction": direction,
                            "participants": participants,
                            "body": body,
                            "attachments": attachments,
                            "entities": entities,
                            "raw_source": raw_source,
                            "hash": f"sha256:{msg_hash}",
                        }
                        msg_out.write(json.dumps(msg_obj, ensure_ascii=False) + "\n")
                        msg_count += 1
        # Also scan media folders for orphan blobs
        media_files = find_media_files(raw_dir)
        for mf in media_files:
            sha, size = sha256_file(mf)
            ext = mf.suffix
            blob_file = copy_blob(mf, blobs_dir, sha, ext)
            mtime = datetime.utcfromtimestamp(mf.stat().st_mtime).isoformat().replace('+00:00', 'Z')
            manifest_entries.setdefault(sha, {
                "blob_id": sha,
                "case_id": case_id,
                "orig_path": str(mf.relative_to(raw_dir)).replace('\\', '/'),
                "blob_path": str(blob_file.relative_to(blobs_dir.parent)),
                "sha256": sha,
                "size_bytes": size,
                "mtime_utc": mtime,
                "related_message_ids": [],
            })
        # Write manifest
        for entry in manifest_entries.values():
            manifest_out.write(json.dumps(entry, ensure_ascii=False) + "\n")
            blob_count += 1
    return msg_count, blob_count

def parse_contacts(xml_root: ET.Element, case_id: str, contacts_path: Path) -> int:
    """Parses contacts and writes JSONL. Returns count."""
    count = 0
    with contacts_path.open('w', encoding='utf-8') as out:
        for parent in xml_root.iter():
            tag = strip_ns(parent.tag)
            if "contacts" in tag:
                for node in parent:
                    ntag = strip_ns(node.tag)
                    if "contact" in ntag:
                        name = safe_text(node.find("name"))
                        phone = safe_text(node.find("phone"))
                        contact_obj = {
                            "id": f"contact-{count+1:04d}",
                            "case_id": case_id,
                            "name": name,
                            "phone": phone,
                            "raw_source": f"{xml_root.tag}:{ntag}[{count}]",
                        }
                        out.write(json.dumps(contact_obj, ensure_ascii=False) + "\n")
                        count += 1
    return count

def parse_calls(xml_root: ET.Element, case_id: str, calls_path: Path) -> int:
    """Parses calls and writes JSONL. Returns count."""
    count = 0
    with calls_path.open('w', encoding='utf-8') as out:
        for parent in xml_root.iter():
            tag = strip_ns(parent.tag)
            if "calls" in tag:
                for node in parent:
                    ntag = strip_ns(node.tag)
                    if "call" in ntag:
                        ts = safe_text(node.find("timestamp"))
                        ts_iso = parse_timestamp(ts) if ts else ""
                        caller = safe_text(node.find("caller"))
                        callee = safe_text(node.find("callee"))
                        duration = safe_text(node.find("duration"))
                        call_obj = {
                            "id": f"call-{count+1:04d}",
                            "case_id": case_id,
                            "timestamp_utc": ts_iso,
                            "caller": caller,
                            "callee": callee,
                            "duration": duration,
                            "raw_source": f"{xml_root.tag}:{ntag}[{count}]",
                        }
                        out.write(json.dumps(call_obj, ensure_ascii=False) + "\n")
                        count += 1
    return count

def run_parser(input_path: Union[str, Path], outdir: Union[str, Path], case_id: str) -> Dict[str, Any]:
    """Main entry: runs UFDR parser and returns summary dict."""
    input_path = Path(input_path)
    outdir = Path(outdir)
    parsed_dir = outdir / case_id / "parsed"
    blobs_dir = outdir / case_id / "blobs"
    parsed_dir.mkdir(parents=True, exist_ok=True)
    blobs_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = unpack_ufdr(input_path, outdir, case_id)
    xml_path = find_main_xml(raw_dir)
    tree = ET.parse(xml_path)
    root = tree.getroot()
    device_id = "device-unknown"
    # Output files
    messages_path = parsed_dir / "messages.jsonl"
    contacts_path = parsed_dir / "contacts.jsonl"
    calls_path = parsed_dir / "calls.jsonl"
    blobs_manifest_path = parsed_dir / "blobs_manifest.jsonl"
    msg_count, blob_count = parse_messages(root, case_id, device_id, raw_dir, blobs_dir, messages_path, blobs_manifest_path)
    contact_count = parse_contacts(root, case_id, contacts_path)
    call_count = parse_calls(root, case_id, calls_path)
    summary = {
        "case_id": case_id,
        "messages": {"count": msg_count, "path": str(messages_path)},
        "contacts": {"count": contact_count, "path": str(contacts_path)},
        "calls": {"count": call_count, "path": str(calls_path)},
        "blobs": {"count": blob_count, "path": str(blobs_manifest_path)},
    }
    logging.info(f"UFDR parsing complete: {json.dumps(summary, indent=2)}")
    return summary

def main():
    parser = argparse.ArgumentParser(description="UFDR Parser — Phase 1: Ingest & Parser")
    parser.add_argument("input", help="Path to .ufdr file or unpacked folder")
    parser.add_argument("outdir", help="Output directory")
    parser.add_argument("case_id", help="Case ID")
    args = parser.parse_args()
    try:
        summary = run_parser(args.input, args.outdir, args.case_id)
        print(json.dumps(summary, indent=2))
        sys.exit(0)
    except Exception as e:
        logging.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
