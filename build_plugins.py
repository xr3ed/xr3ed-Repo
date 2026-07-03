import os
import sys
import shutil
import subprocess
import json
import hashlib
import glob


def get_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def main():
    # repo_root is the directory containing this script (the src/ checkout)
    repo_root = os.path.abspath(os.path.dirname(__file__))

    # builds_dir: passed as first argument (the builds branch checkout path)
    # If not given, fall back to a sibling "builds" folder (useful for local testing)
    if len(sys.argv) > 1:
        builds_dir = os.path.abspath(sys.argv[1])
    else:
        builds_dir = os.path.join(os.path.dirname(repo_root), "builds")

    print(f"repo_root  = {repo_root}")
    print(f"builds_dir = {builds_dir}")

    src_dir = repo_root

    # 1. Load the OLD plugins.json from the builds branch checkout
    old_plugins_json_path = os.path.join(builds_dir, "plugins.json")
    old_plugins = []
    if os.path.exists(old_plugins_json_path):
        try:
            with open(old_plugins_json_path, 'r', encoding='utf-8') as f:
                old_plugins = json.load(f)
            print(f"Loaded {len(old_plugins)} old plugins from builds branch.")
        except Exception as e:
            print(f"Warning: Failed to load old plugins.json: {e}")
    else:
        print(f"Warning: old plugins.json not found at {old_plugins_json_path}")

    # 2. Run gradlew make --continue (compile all plugins, ignore failures)
    gradlew = os.path.join(src_dir, "gradlew")
    if os.name == 'nt':
        gradlew = gradlew + ".bat"

    print("\n=== Running: gradlew make --continue ===")
    subprocess.run([gradlew, "make", "--continue"], cwd=src_dir)

    # 3. Detect which plugins compiled successfully and which failed
    ignored_folders = {
        ".git", ".github", ".vscode", "gradle", "temp_repos",
        "buildSrc", "Miro-Temp", "Phisher-Temp", "_patches", "builds",
        "build"  # top-level build/ dir
    }
    plugins_in_src = []
    for item in sorted(os.listdir(src_dir)):
        item_path = os.path.join(src_dir, item)
        if os.path.isdir(item_path) and item not in ignored_folders and not item.startswith('.'):
            if os.path.exists(os.path.join(item_path, "build.gradle.kts")):
                plugins_in_src.append(item)

    successful_cs3 = {}   # plugin_name -> cs3_path
    failed_plugins = []

    for plugin in plugins_in_src:
        build_dir = os.path.join(src_dir, plugin, "build")
        cs3_file = None
        if os.path.isdir(build_dir):
            for fname in os.listdir(build_dir):
                if fname.endswith(".cs3"):
                    cs3_file = os.path.join(build_dir, fname)
                    break
        if cs3_file:
            successful_cs3[plugin] = cs3_file
        else:
            failed_plugins.append(plugin)

    print(f"\nSuccessful plugins: {len(successful_cs3)}")
    print(f"Failed plugins   : {failed_plugins}")

    # 4. Disable failed plugins temporarily so makePluginsJson ignores them
    disabled_files = []
    for plugin in failed_plugins:
        gradle_file = os.path.join(src_dir, plugin, "build.gradle.kts")
        if os.path.exists(gradle_file):
            disabled_file = gradle_file + ".disabled"
            os.rename(gradle_file, disabled_file)
            disabled_files.append((gradle_file, disabled_file))

    # 5. Generate plugins.json for successful plugins only
    print("\n=== Running: gradlew makePluginsJson ===")
    subprocess.run([gradlew, "makePluginsJson"], cwd=src_dir)

    # 6. Restore disabled build.gradle.kts files
    for original, disabled in disabled_files:
        if os.path.exists(disabled):
            os.rename(disabled, original)

    # 7. Load the freshly generated plugins.json
    new_plugins_json_path = os.path.join(src_dir, "build", "plugins.json")
    if not os.path.exists(new_plugins_json_path):
        print(f"ERROR: Gradle did not generate {new_plugins_json_path}")
        sys.exit(1)

    try:
        with open(new_plugins_json_path, 'r', encoding='utf-8') as f:
            new_plugins = json.load(f)
        print(f"Gradle generated {len(new_plugins)} plugin entries.")
    except Exception as e:
        print(f"ERROR loading new plugins.json: {e}")
        sys.exit(1)

    # 8. Copy all successful CS3 files to builds_dir
    os.makedirs(builds_dir, exist_ok=True)
    for plugin, cs3_path in successful_cs3.items():
        dest = os.path.join(builds_dir, os.path.basename(cs3_path))
        shutil.copy2(cs3_path, dest)
        print(f"Copied: {os.path.basename(cs3_path)}")

    # 9. Update fileSize and fileHash in new_plugins to match the ACTUAL files in builds_dir
    #    (Gradle sometimes encodes a relative URL hash; recalculate from the actual file)
    new_plugins_map = {p["internalName"]: p for p in new_plugins}
    for p in new_plugins:
        cs3_dest = os.path.join(builds_dir, f"{p['internalName']}.cs3")
        if os.path.exists(cs3_dest):
            p["fileSize"] = os.path.getsize(cs3_dest)
            p["fileHash"] = f"sha256-{get_sha256(cs3_dest)}"
        else:
            print(f"WARNING: {p['internalName']}.cs3 not found in builds_dir after copy!")

    # 10. Merge old entries for failed plugins back in
    for plugin in failed_plugins:
        # Find matching old entry (by internalName OR name)
        old_entry = None
        for p in old_plugins:
            if p.get("internalName") == plugin or p.get("name") == plugin:
                old_entry = p
                break

        if not old_entry:
            print(f"No old entry found for failed plugin: {plugin} — skipping.")
            continue

        # Refresh size/hash if the CS3 still exists in builds_dir
        cs3_dest = os.path.join(builds_dir, f"{old_entry['internalName']}.cs3")
        if os.path.exists(cs3_dest):
            old_entry["fileSize"] = os.path.getsize(cs3_dest)
            old_entry["fileHash"] = f"sha256-{get_sha256(cs3_dest)}"
            print(f"Refreshed hash for failed plugin kept from old builds: {plugin}")
        else:
            print(f"WARNING: CS3 for failed plugin '{plugin}' not found in builds_dir — entry kept with old hash.")

        if old_entry["internalName"] not in new_plugins_map:
            new_plugins.append(old_entry)
            new_plugins_map[old_entry["internalName"]] = old_entry
            print(f"Merged old entry: {plugin}")

    # 11. Write final plugins.json to builds_dir directly
    final_plugins_json = os.path.join(builds_dir, "plugins.json")
    with open(final_plugins_json, 'w', encoding='utf-8') as f:
        json.dump(new_plugins, f, indent=4, ensure_ascii=False)
    print(f"\nFinal plugins.json written with {len(new_plugins)} entries to: {final_plugins_json}")


if __name__ == "__main__":
    main()
