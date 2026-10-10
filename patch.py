"""Build "Volume Controller NEO" from your own copy of Elgato's Volume Controller plugin.

Usage:  python patch.py [--source PATH] [--out DIR] [--install]

  --source   the official plugin folder (default: the one Stream Deck installed,
             %APPDATA%\\Elgato\\StreamDeck\\Plugins\\com.elgato.volume-controller.sdPlugin)
  --out      where to write the patched plugin and the .streamDeckPlugin package (default: ./out)
  --install  open the package with Stream Deck when done

Needs Python 3.9+ and Node.js (for `npx js-beautify`). Nothing from Elgato is
redistributed: this repo only holds the changes; the plugin is built from your copy.
"""
import argparse
import base64
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
OLD_ID, NEW_ID = "com.elgato.volume-controller", "com.xenside.volumecontroller"
SUPPORTED_SHA256 = "d0edbf6ff556f038"  # bin/plugin.js of Volume Controller 2.0.4.196 (prefix)
BEAUTIFY = ["npx", "--yes", "js-beautify@1.15.1", "-s", "2"]
PATCHES = {
    "bin/plugin.js": "plugin.js.patch",
    "pi/application/auto-detection/inspector.js": "auto-detection-inspector.js.patch",
}
NEO_MODEL = "20GBJ9901"


def fail(msg):
    sys.exit("error: " + msg)


def default_source():
    return os.path.join(os.environ.get("APPDATA", ""), "Elgato", "StreamDeck", "Plugins", OLD_ID + ".sdPlugin")


def apply_unified_diff(text, diff_text, label):
    """Apply a unified diff by matching each hunk's old block exactly (line numbers may drift)."""
    lines = text.splitlines(True)
    hunks, cur = [], None
    for l in diff_text.splitlines(True):
        if l.startswith("@@"):
            cur = ([], [])
            hunks.append(cur)
        elif cur is not None and l[:1] in (" ", "-", "+"):
            body = l[1:]
            if l[0] in " -":
                cur[0].append(body)
            if l[0] in " +":
                cur[1].append(body)
    pos = 0
    for n, (old, new) in enumerate(hunks, 1):
        found = [i for i in range(pos, len(lines) - len(old) + 1) if lines[i:i + len(old)] == old]
        if len(found) != 1:
            fail(f"{label}: hunk {n} {'not found' if not found else 'is ambiguous'} - "
                 "is this Volume Controller 2.0.4.196?")
        i = found[0]
        lines[i:i + len(old)] = new
        pos = i + len(new)
    return "".join(lines)


def rename_ids_in_zip(path):
    src = zipfile.ZipFile(path)
    items = [(info, src.read(info.filename)) for info in src.infolist()]
    src.close()
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as out:
        for info, data in items:
            if info.filename.lower().endswith(".json"):
                data = data.decode("utf-8").replace(OLD_ID, NEW_ID).encode("utf-8")
            out.writestr(info, data)


def make_neo_profile(plugin_dir):
    """Auto Software Detection profile for the Neo (4x2, no dials): one app per row."""
    tpl = {}
    for name in ("Volume Controller (Auto).streamDeckProfile", "Volume Controller+ (Auto).streamDeckProfile"):
        with zipfile.ZipFile(os.path.join(plugin_dir, name)) as z:
            for n in z.namelist():
                if n.replace("\\", "/").endswith("manifest.json"):
                    for c in json.loads(z.read(n)).get("Controllers") or []:
                        for a in (c.get("Actions") or {}).values():
                            tpl.setdefault(a["UUID"], a)
    A = lambda s: copy.deepcopy(tpl[f"{NEW_ID}.{s}"])
    layout = {
        "0,0": A("back-to-profile"), "1,0": A("auto-detection.mute"),
        "2,0": A("auto-detection.volume-down"), "3,0": A("auto-detection.volume-up"),
        "0,1": A("auto-detection.next"), "1,1": A("auto-detection.mute"),
        "2,1": A("auto-detection.volume-down"), "3,1": A("auto-detection.volume-up"),
    }
    top, page = str(uuid.uuid4()).upper(), str(uuid.uuid4())
    pagedir = base64.b32hexencode(uuid.UUID(page).bytes).decode().rstrip("=") + "Z"
    root = f"{top}.sdProfile/"
    name = "Volume Controller Neo (Auto)"
    with zipfile.ZipFile(os.path.join(plugin_dir, name + ".streamDeckProfile"), "w", zipfile.ZIP_DEFLATED) as z:
        for d in (root, root + "Profiles/", root + f"Profiles/{pagedir}/", root + f"Profiles/{pagedir}/Images/"):
            z.writestr(d, b"")
        z.writestr(root + "manifest.json", json.dumps({
            "Device": {"Model": NEO_MODEL, "UUID": ""}, "InstalledByPluginUUID": NEW_ID, "Name": name,
            "Pages": {"Current": page, "Pages": [page]}, "PreconfiguredName": name, "Version": "2.0"}))
        z.writestr(root + f"Profiles/{pagedir}/manifest.json",
                   json.dumps({"Controllers": [{"Actions": layout, "Type": "Keypad"}]}))


def pack(plugin_dir, out_file):
    base = os.path.basename(plugin_dir)
    with zipfile.ZipFile(out_file, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(plugin_dir):
            dirs[:] = [d for d in dirs if d != "logs"]
            for f in files:
                full = os.path.join(root, f)
                z.write(full, base + "/" + os.path.relpath(full, plugin_dir).replace(os.sep, "/"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--source", default=default_source())
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--install", action="store_true")
    args = ap.parse_args()

    src = os.path.abspath(args.source)
    if not os.path.isfile(os.path.join(src, "bin", "plugin.js")):
        fail(f"official plugin not found at {src}\n"
             "Install 'Volume Controller' from the Elgato Marketplace (or pass --source).")
    digest = hashlib.sha256(open(os.path.join(src, "bin", "plugin.js"), "rb").read()).hexdigest()
    if not digest.startswith(SUPPORTED_SHA256):
        print(f"warning: bin/plugin.js is not the supported 2.0.4.196 build (sha256 {digest[:16]}); "
              "patches may not apply.")

    dst = os.path.join(os.path.abspath(args.out), NEW_ID + ".sdPlugin")
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("logs", "manifest.json", "*.orig-*"))
    print("copied", src)

    # 1. readable, patchable backend
    js = os.path.join(dst, "bin", "plugin.js")
    pretty = subprocess.run(BEAUTIFY + [js], capture_output=True, text=True, encoding="utf-8",
                            shell=(os.name == "nt"))
    if pretty.returncode != 0 or not pretty.stdout:
        fail("js-beautify failed (is Node.js installed?)\n" + pretty.stderr)
    open(js, "w", encoding="utf-8", newline="\n").write(pretty.stdout)

    # 2. own plugin identity (not the Marketplace one -> no integrity check)
    for root, dirs, files in os.walk(dst):
        dirs[:] = [d for d in dirs if d != "node_modules"]
        for f in files:
            p = os.path.join(root, f)
            if f.endswith((".js", ".json", ".html")):
                t = open(p, encoding="utf-8").read()
                if OLD_ID in t:
                    open(p, "w", encoding="utf-8", newline="\n").write(t.replace(OLD_ID, NEW_ID))
            elif f.endswith(".streamDeckProfile"):
                rename_ids_in_zip(p)

    # 3. the actual changes
    for rel, patch in PATCHES.items():
        p = os.path.join(dst, *rel.split("/"))
        text = open(p, encoding="utf-8").read()
        diff = open(os.path.join(HERE, "patches", patch), encoding="utf-8").read()
        open(p, "w", encoding="utf-8", newline="\n").write(apply_unified_diff(text, diff, rel))
        print("patched", rel)

    # 4. plain-text manifest + Neo auto profile
    shutil.copyfile(os.path.join(HERE, "template", "manifest.json"), os.path.join(dst, "manifest.json"))
    make_neo_profile(dst)

    # 5. sanity check + package
    node = shutil.which("node")
    if node and subprocess.run([node, "--check", js]).returncode != 0:
        fail("patched plugin.js does not parse")
    pkg = os.path.join(os.path.abspath(args.out), NEW_ID + ".streamDeckPlugin")
    pack(dst, pkg)
    print("built", pkg)
    if args.install:
        os.startfile(pkg)
        print("opened with Stream Deck - accept the install prompt")


if __name__ == "__main__":
    main()
