import os
import shutil
import re
import subprocess

def run_cmd(args, cwd=None):
    print(f"Running command: {' '.join(args)} in {cwd or '.'}")
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    return result

def main():
    repo_root = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.join(repo_root, "temp_repos")
    
    # Ensure temp dir exists
    os.makedirs(temp_dir, exist_ok=True)
    
    miro_dir = os.path.join(temp_dir, "Miro")
    phisher_dir = os.path.join(temp_dir, "Phisher")
    
    # 1. Clone or pull Miro (master branch)
    if not os.path.exists(miro_dir):
        run_cmd(["git", "clone", "-b", "master", "https://github.com/sad25kag/BetbetMiro-Extension.git", "Miro"], cwd=temp_dir)
    else:
        run_cmd(["git", "checkout", "master"], cwd=miro_dir)
        run_cmd(["git", "pull"], cwd=miro_dir)
        
    # 2. Clone or pull Phisher (master branch)
    if not os.path.exists(phisher_dir):
        run_cmd(["git", "clone", "-b", "master", "https://github.com/phisher98/cloudstream-extensions-phisher.git", "Phisher"], cwd=temp_dir)
    else:
        run_cmd(["git", "checkout", "master"], cwd=phisher_dir)
        run_cmd(["git", "pull"], cwd=phisher_dir)

    # 3. Clean up existing plugin folders in repo root
    # A plugin folder has build.gradle.kts and is not a known/ignored folder
    ignored_folders = {".git", ".github", ".vscode", "gradle", "temp_repos", "buildSrc", "Miro-Temp", "Phisher-Temp", "_patches"}
    for item in os.listdir(repo_root):
        item_path = os.path.join(repo_root, item)
        if os.path.isdir(item_path) and item not in ignored_folders:
            if os.path.exists(os.path.join(item_path, "build.gradle.kts")):
                print(f"Cleaning up old plugin folder: {item}")
                shutil.rmtree(item_path)

    # 4. Copy gradle files from Miro (it has the most updated setup)
    gradle_files = ["build.gradle.kts", "gradle.properties", "gradlew", "gradlew.bat"]
    for f in gradle_files:
        src = os.path.join(miro_dir, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(repo_root, f))
            
    # Copy gradle folder
    gradle_folder = os.path.join(repo_root, "gradle")
    if os.path.exists(gradle_folder):
        shutil.rmtree(gradle_folder)
    shutil.copytree(os.path.join(miro_dir, "gradle"), gradle_folder)
    
    # Update build.gradle.kts repository fallback URL, namespace dynamic check, and opt-in compiler option
    build_gradle_path = os.path.join(repo_root, "build.gradle.kts")
    if os.path.exists(build_gradle_path):
        with open(build_gradle_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace default setRepo fallback URL
        content = content.replace("https://github.com/duro92/ExtCloud", "https://github.com/xr3ed/xr3ed-Repo")
        
        # Replace hardcoded namespace with dynamic namespace check
        old_namespace = 'namespace = "com.sad25kag"'
        new_namespace = """val phisherPluginsFile = project.rootProject.file("phisher_plugins.txt")
        val isPhisher = if (phisherPluginsFile.exists()) {
            phisherPluginsFile.readLines().contains(project.name)
        } else {
            false
        }
        namespace = if (isPhisher) "com.phisher98" else "com.sad25kag" """
        
        content = content.replace(old_namespace, new_namespace)
        
        # Add optIn compiler options to bypass prerelease API compile check globally
        # Use regex to match freeCompilerArgs block flexibly (handles trailing commas, whitespace changes)
        import re
        if 'optIn.add("com.lagradost.cloudstream3.Prerelease")' not in content:
            pattern = r'(freeCompilerArgs\.addAll\([^)]*\))'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                original = match.group(0)
                replacement = original + '\n                optIn.add("com.lagradost.cloudstream3.Prerelease")'
                content = content.replace(original, replacement, 1)
        
        with open(build_gradle_path, 'w', encoding='utf-8') as f:
            f.write(content)

    # 5. List plugins
    def get_plugins(src_dir):
        plugins = []
        for item in os.listdir(src_dir):
            item_path = os.path.join(src_dir, item)
            if os.path.isdir(item_path) and item not in ignored_folders:
                if os.path.exists(os.path.join(item_path, "build.gradle.kts")):
                    plugins.append(item)
        return plugins

    miro_plugins = get_plugins(miro_dir)
    phisher_plugins = get_plugins(phisher_dir)
    
    print(f"Miro plugins: {len(miro_plugins)}")
    print(f"Phisher plugins: {len(phisher_plugins)}")
    
    # 6. Copy Miro plugins (Primary)
    for p in miro_plugins:
        src = os.path.join(miro_dir, p)
        dst = os.path.join(repo_root, p)
        shutil.copytree(src, dst)
        print(f"Copied Miro plugin: {p}")
        
    # 7. Copy Phisher plugins (Backup if conflict)
    phisher_copied = []
    for p in phisher_plugins:
        src = os.path.join(phisher_dir, p)
        if p in miro_plugins:
            # Conflict! Rename Phisher to Backup
            dst_name = f"{p}Backup"
            dst = os.path.join(repo_root, dst_name)
            shutil.copytree(src, dst)
            phisher_copied.append(dst_name)
            print(f"Conflict: Copied Phisher plugin {p} as {dst_name}")
            
            # Modify Kotlin files to append [Backup] to MainAPI names
            modify_kotlin_files(dst)
        else:
            dst = os.path.join(repo_root, p)
            shutil.copytree(src, dst)
            phisher_copied.append(p)
            print(f"Copied Phisher plugin (no conflict): {p}")

    # Write phisher_plugins.txt
    with open(os.path.join(repo_root, "phisher_plugins.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(phisher_copied))
    print("Generated phisher_plugins.txt")

    # 9. Apply local patches on top of upstream-copied plugins
    apply_patches(repo_root)

    # 8. Generate settings.gradle.kts
    # We dynamically include all folders with build.gradle.kts except ignored ones
    settings_content = """rootProject.name = "xr3ed"

val disabled = listOf("Miro-Temp", "Phisher-Temp", "temp_repos")

File(rootDir, ".").eachDir { dir ->
    if (!disabled.contains(dir.name) && File(dir, "build.gradle.kts").exists()) {
        include(dir.name)
    }
}

fun File.eachDir(block: (File) -> Unit) {
    listFiles()?.filter { it.isDirectory }?.forEach { block(it) }
}
"""
    with open(os.path.join(repo_root, "settings.gradle.kts"), "w", encoding="utf-8") as f:
        f.write(settings_content)
    print("Generated settings.gradle.kts")

def apply_patches(repo_root):
    """
    Apply local patches from the _patches/ folder on top of upstream-copied plugins.

    Struktur _patches/:
        _patches/
            PluginName/               <- nama HARUS sama dengan folder plugin di repo
                src/
                    main/
                        kotlin/
                            .../FixedFile.kt  <- file yang menimpa versi upstream
                build.gradle.kts      <- bisa juga patch build file

    Setiap file di _patches/PluginName/ akan menyalin & menimpa file
    yang sama di repo_root/PluginName/ dengan path relatif yang sama.
    Folder _patches/ sendiri TIDAK dihapus oleh proses cleanup.
    """
    patches_dir = os.path.join(repo_root, "_patches")
    if not os.path.exists(patches_dir):
        print("[PATCH] No _patches/ folder found, skipping patch step.")
        return

    patched_count = 0
    for plugin_name in sorted(os.listdir(patches_dir)):
        plugin_patch_dir = os.path.join(patches_dir, plugin_name)
        if not os.path.isdir(plugin_patch_dir):
            continue

        plugin_dst_dir = os.path.join(repo_root, plugin_name)
        if not os.path.exists(plugin_dst_dir):
            print(f"[PATCH] WARNING: Target plugin '{plugin_name}' not found in repo, skipping.")
            continue

        for root, dirs, files in os.walk(plugin_patch_dir):
            rel_root = os.path.relpath(root, plugin_patch_dir)
            for file in files:
                src_file = os.path.join(root, file)
                dst_file = os.path.join(plugin_dst_dir, rel_root, file)
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                shutil.copy2(src_file, dst_file)
                rel_display = os.path.join(rel_root, file).replace("\\", "/").lstrip("./")
                print(f"[PATCH] {plugin_name}/{rel_display}")
                patched_count += 1

    if patched_count == 0:
        print("[PATCH] _patches/ exists but no files were applied.")
    else:
        print(f"[PATCH] Done — {patched_count} file(s) patched.")


def modify_kotlin_files(plugin_dir):
    # Regex to find override var/val name = "..."
    name_pattern = re.compile(r'(override\s+(?:var|val)\s+name\s*(?::\s*String)?\s*=\s*)(["\'])(.*?)\2')
    
    for root, dirs, files in os.walk(plugin_dir):
        for file in files:
            if file.endswith(".kt"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        code = f.read()
                    
                    new_code, count = name_pattern.subn(r'\1\2\3 [Backup]\2', code)
                    if count > 0:
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(new_code)
                        print(f"Modified provider name in: {file_path} ({count} replacements)")
                except Exception as e:
                    print(f"Error modifying file {file_path}: {e}")

if __name__ == "__main__":
    main()
