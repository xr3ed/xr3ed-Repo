import os
import shutil
import re
import subprocess
import stat

def run_cmd(args, cwd=None):
    print(f"Running command: {' '.join(args)} in {cwd or '.'}")
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    return result

def safe_rmtree(path):
    if not os.path.exists(path):
        return
    try:
        os.chmod(path, 0o777)
    except Exception:
        pass
    for root, dirs, files in os.walk(path, topdown=False):
        for f in files:
            try:
                os.chmod(os.path.join(root, f), 0o777)
            except Exception:
                pass
        for d in dirs:
            try:
                os.chmod(os.path.join(root, d), 0o777)
            except Exception:
                pass
    try:
        shutil.rmtree(path)
    except Exception as e:
        print(f"shutil.rmtree failed on {path}: {e}")
        if os.name == 'nt':
            res = subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', path], capture_output=True, text=True)
            print(f"rmdir exit: {res.returncode}, stderr: {res.stderr}")
        else:
            res = subprocess.run(['rm', '-rf', path], capture_output=True, text=True)
            print(f"rm -rf exit: {res.returncode}, stderr: {res.stderr}")

def main():
    try:
        _main()
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print("CRITICAL ERROR IN SYNC SCRIPT:")
        print(tb)
        with open("sync_error.txt", "w", encoding="utf-8") as f:
            f.write(tb)
        run_cmd(["git", "config", "--local", "user.email", "actions@github.com"])
        run_cmd(["git", "config", "--local", "user.name", "GitHub Actions"])
        run_cmd(["git", "add", "sync_error.txt"])
        run_cmd(["git", "commit", "-m", "Log sync error [skip ci]"])
        run_cmd(["git", "push", "origin", "main"])
        import sys
        sys.exit(1)

def _main():
    repo_root = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.join(repo_root, "temp_repos")
    
    # Ensure temp dir exists
    os.makedirs(temp_dir, exist_ok=True)
    
    miro_dir = os.path.join(temp_dir, "Miro")
    phisher_dir = os.path.join(temp_dir, "Phisher")
    
    # 1. Clone or pull Miro (master branch)
    miro_success = False
    if not os.path.exists(miro_dir):
        res = run_cmd(["git", "clone", "-b", "master", "https://github.com/sad25kag/BetbetMiro-Extension.git", "Miro"], cwd=temp_dir)
        if res.returncode == 0:
            miro_success = True
    else:
        res = run_cmd(["git", "checkout", "master"], cwd=miro_dir)
        if res.returncode == 0:
            res_pull = run_cmd(["git", "pull"], cwd=miro_dir)
            if res_pull.returncode == 0:
                miro_success = True

    # 2. Clone or pull Phisher (builds branch)
    phisher_success = False
    if os.path.exists(phisher_dir):
        remote_res = run_cmd(["git", "config", "--get", "remote.origin.url"], cwd=phisher_dir)
        remote_url = remote_res.stdout.strip() if remote_res.returncode == 0 else ""
        if "phisher98" not in remote_url:
            print("Deleting old Phisher temp repo due to remote mismatch...")
            safe_rmtree(phisher_dir)

    if not os.path.exists(phisher_dir):
        res = run_cmd(["git", "clone", "-b", "builds", "https://github.com/phisher98/cloudstream-extensions-phisher.git", "Phisher"], cwd=temp_dir)
        if res.returncode == 0:
            phisher_success = True
    else:
        run_cmd(["git", "fetch", "--all"], cwd=phisher_dir)
        res = run_cmd(["git", "checkout", "-B", "builds", "origin/builds"], cwd=phisher_dir)
        if res.returncode == 0:
            res_pull = run_cmd(["git", "reset", "--hard", "origin/builds"], cwd=phisher_dir)
            if res_pull.returncode == 0:
                phisher_success = True

    ignored_folders = {".git", ".github", ".vscode", "gradle", "temp_repos", "buildSrc", "Miro-Temp", "Phisher-Temp", "_patches", "builds"}

    # Define get_plugins
    def get_plugins(src_dir):
        plugins = []
        if not os.path.exists(src_dir):
            return plugins
        for item in os.listdir(src_dir):
            item_path = os.path.join(src_dir, item)
            if os.path.isdir(item_path) and item not in ignored_folders:
                if os.path.exists(os.path.join(item_path, "build.gradle.kts")):
                    plugins.append(item)
        return plugins

    # Get Miro plugins list
    miro_plugins = get_plugins(miro_dir) if miro_success else []

    # Get Phisher precompiled plugin names from builds branch
    phisher_built_plugins = []
    if phisher_success and os.path.exists(phisher_dir):
        for item in os.listdir(phisher_dir):
            if item.endswith(".cs3"):
                phisher_built_plugins.append(item[:-4]) # strip .cs3

    print(f"Miro plugins found: {len(miro_plugins)}")
    print(f"Phisher precompiled plugins found: {len(phisher_built_plugins)}")

    # 3. Clean up existing plugin folders in repo root (ALL of them, since we will rebuild Miro only)
    for item in os.listdir(repo_root):
        item_path = os.path.join(repo_root, item)
        if os.path.isdir(item_path) and item not in ignored_folders:
            if os.path.exists(os.path.join(item_path, "build.gradle.kts")):
                print(f"Cleaning up old plugin folder: {item}")
                safe_rmtree(item_path)

    # 4. Copy gradle files from Miro
    if miro_success:
        gradle_files = ["build.gradle.kts", "gradle.properties", "gradlew", "gradlew.bat"]
        for f in gradle_files:
            src = os.path.join(miro_dir, f)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(repo_root, f))
                
        # Copy gradle folder
        gradle_folder = os.path.join(repo_root, "gradle")
        if os.path.exists(gradle_folder):
            safe_rmtree(gradle_folder)
        shutil.copytree(os.path.join(miro_dir, "gradle"), gradle_folder, dirs_exist_ok=True)
        
        # Update build.gradle.kts repository fallback URL, namespace dynamic check, and opt-in compiler option
        build_gradle_path = os.path.join(repo_root, "build.gradle.kts")
        if os.path.exists(build_gradle_path):
            with open(build_gradle_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace default setRepo fallback URL
            content = content.replace("https://github.com/duro92/ExtCloud", "https://github.com/xr3ed/xr3ed-Repo")
            
            # Replace the plugin group ID with the correct Jitpack coordinates
            content = content.replace("com.github.recloudstream:gradle", "com.github.recloudstream.gradle:gradle")
            
            # Since Miro is always com.sad25kag, we keep the namespace check but it evaluates to com.sad25kag
            old_namespace = 'namespace = "com.sad25kag"'
            new_namespace = """val phisherPluginsFile = project.rootProject.file("phisher_plugins.txt")
            val isPhisher = if (phisherPluginsFile.exists()) {
                phisherPluginsFile.readLines().contains(project.name)
            } else {
                false
            }
            namespace = if (isPhisher) "com.phisher98" else "com.sad25kag" """
            content = content.replace(old_namespace, new_namespace)
            
            # Add optIn compiler options
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

        # Update gradle.properties
        gradle_properties_path = os.path.join(repo_root, "gradle.properties")
        if os.path.exists(gradle_properties_path):
            with open(gradle_properties_path, 'r', encoding='utf-8') as f:
                prop_content = f.read()
            
            import re
            prop_content = re.sub(
                r'cloudstream\.gradle\.plugin\.version\s*=\s*\S+',
                'cloudstream.gradle.plugin.version=32895aedb6',
                prop_content
            )
            
            with open(gradle_properties_path, 'w', encoding='utf-8') as f:
                f.write(prop_content)

    # 5. Copy Miro plugins, rename to Backup if they conflict with Phisher precompiled files
    miro_copied = []
    if miro_success:
        for p in miro_plugins:
            src = os.path.join(miro_dir, p)
            if p in phisher_built_plugins:
                # Conflict! Rename Miro to Backup
                dst_name = f"{p}Backup"
                dst = os.path.join(repo_root, dst_name)
                shutil.copytree(src, dst, dirs_exist_ok=True)
                miro_copied.append(dst_name)
                print(f"Conflict: Copied Miro plugin {p} as {dst_name}")
                
                # Modify Kotlin files to append [Backup] to MainAPI names
                modify_kotlin_files(dst)
            else:
                dst = os.path.join(repo_root, p)
                shutil.copytree(src, dst, dirs_exist_ok=True)
                miro_copied.append(p)
                print(f"Copied Miro plugin (no conflict): {p}")

    # Write empty phisher_plugins.txt since we don't compile Phisher from source
    with open(os.path.join(repo_root, "phisher_plugins.txt"), "w", encoding="utf-8") as f:
        f.write("")

    # 6. Apply local patches on top of upstream-copied plugins
    apply_patches(repo_root)


    # Rename Ultima display name to 🏠HomePage
    rename_ultima_to_homepage(repo_root)

    # Rename FreeReels and DracinSI to #Dracin prefix
    rename_to_dracin(repo_root)

    # Rename DonghuaFilm and Donghuastream to #Donghua prefix (and remove backup from Donghuastream name)
    rename_to_donghua(repo_root)

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
            backup_dir = os.path.join(repo_root, f"{plugin_name}Backup")
            if os.path.exists(backup_dir):
                plugin_dst_dir = backup_dir
                print(f"[PATCH] Target plugin '{plugin_name}' renamed to '{plugin_name}Backup', applying patch there.")
        
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

def rename_ultima_to_homepage(repo_root):
    # Find Ultima plugin directory
    for item in ["Ultima", "UltimaBackup"]:
        ultima_dir = os.path.join(repo_root, item)
        if not os.path.exists(ultima_dir):
            continue
        
        # 1. Modify Ultima.kt
        ultima_kt = os.path.join(ultima_dir, "src", "main", "kotlin", "com", "phisher98", "Ultima.kt")
        if os.path.exists(ultima_kt):
            try:
                with open(ultima_kt, "r", encoding="utf-8") as f:
                    code = f.read()
                
                code = code.replace('override var name = "Ultima"', 'override var name = "🏠HomePage"')
                code = code.replace('override var name = "Ultima [Backup]"', 'override var name = "🏠HomePage [Backup]"')
                
                with open(ultima_kt, "w", encoding="utf-8") as f:
                    f.write(code)
                print(f"[RENAME] Updated name in {item}/Ultima.kt to Homepage")
            except Exception as e:
                print(f"Error renaming name in {item}/Ultima.kt: {e}")
            
        # 2. Modify StorageManager.kt
        storage_mgr = os.path.join(ultima_dir, "src", "main", "kotlin", "com", "phisher98", "Utils", "StorageManager.kt")
        if os.path.exists(storage_mgr):
            try:
                with open(storage_mgr, "r", encoding="utf-8") as f:
                    code = f.read()
                
                code = code.replace(
                    'val filtered = providers.filter { it.name != "Ultima" }',
                    'val filtered = providers.filter { it.name != "Ultima" && it.name != "🏠HomePage" && it.name != "🏠HomePage [Backup]" }'
                )
                
                with open(storage_mgr, "w", encoding="utf-8") as f:
                    f.write(code)
                print(f"[RENAME] Updated filter in {item}/StorageManager.kt")
            except Exception as e:
                print(f"Error renaming filter in {item}/StorageManager.kt: {e}")

def rename_to_dracin(repo_root):
    # FreeReels
    for item in ["FreeReels", "FreeReelsBackup"]:
        freereels_dir = os.path.join(repo_root, item)
        if not os.path.exists(freereels_dir):
            continue
        
        # Modify FreeReels.kt
        freereels_kt = os.path.join(freereels_dir, "src", "main", "kotlin", "com", "sad25kag", "FreeReels", "FreeReels.kt")
        if os.path.exists(freereels_kt):
            try:
                with open(freereels_kt, "r", encoding="utf-8") as f:
                    code = f.read()
                
                # Menggunakan regex untuk mengganti nama secara tangguh (baik dengan kutip tunggal/ganda atau spasi)
                name_pattern = re.compile(r'(override\s+(?:var|val)\s+name\s*(?::\s*String)?\s*=\s*)(["\'])(FreeReels.*?)\2')
                code = name_pattern.sub(r'\1\2#Dracin \3\2', code)
                
                with open(freereels_kt, "w", encoding="utf-8") as f:
                    f.write(code)
                print(f"[RENAME] Updated name in {item}/FreeReels.kt to #Dracin FreeReels")
            except Exception as e:
                print(f"Error renaming name in {item}/FreeReels.kt: {e}")

    # DracinSI
    for item in ["DracinSI", "DracinSIBackup"]:
        dracinsi_dir = os.path.join(repo_root, item)
        if not os.path.exists(dracinsi_dir):
            continue
        
        # Modify DracinSI.kt
        dracinsi_kt = os.path.join(dracinsi_dir, "src", "main", "kotlin", "com", "sad25kag", "dracinsi", "DracinSI.kt")
        if os.path.exists(dracinsi_kt):
            try:
                with open(dracinsi_kt, "r", encoding="utf-8") as f:
                    code = f.read()
                
                # Menggunakan regex untuk mengganti nama secara tangguh (baik dengan kutip tunggal/ganda atau spasi)
                name_pattern = re.compile(r'(override\s+(?:var|val)\s+name\s*(?::\s*String)?\s*=\s*)(["\'])(DracinSI.*?)\2')
                code = name_pattern.sub(r'\1\2#Dracin \3\2', code)
                
                with open(dracinsi_kt, "w", encoding="utf-8") as f:
                    f.write(code)
                print(f"[RENAME] Updated name in {item}/DracinSI.kt to #Dracin DracinSI")
            except Exception as e:
                print(f"Error renaming name in {item}/DracinSI.kt: {e}")

def rename_to_donghua(repo_root):
    # DonghuaFilm
    for item in ["DonghuaFilm", "DonghuaFilmBackup"]:
        df_dir = os.path.join(repo_root, item)
        if not os.path.exists(df_dir):
            continue
        
        # Modify DonghuaFilm.kt and DonghuaFilmCosmetic.kt
        for filename in ["DonghuaFilm.kt", "DonghuaFilmCosmetic.kt"]:
            df_kt = os.path.join(df_dir, "src", "main", "kotlin", "com", "sad25kag", "donghuafilm", filename)
            if os.path.exists(df_kt):
                try:
                    with open(df_kt, "r", encoding="utf-8") as f:
                        code = f.read()
                    
                    # Regex matching DonghuaFilm with optional [Backup]
                    name_pattern = re.compile(r'(override\s+(?:var|val)\s+name\s*(?::\s*String)?\s*=\s*)(["\'])(DonghuaFilm)(?:\s*\[Backup\])?\2')
                    code = name_pattern.sub(r'\1\2#Donghua \3\2', code)
                    
                    with open(df_kt, "w", encoding="utf-8") as f:
                        f.write(code)
                    print(f"[RENAME] Updated name in {item}/{filename} to #Donghua DonghuaFilm")
                except Exception as e:
                    print(f"Error renaming name in {item}/{filename}: {e}")

    # Donghuastream
    for item in ["Donghuastream", "DonghuastreamBackup"]:
        ds_dir = os.path.join(repo_root, item)
        if not os.path.exists(ds_dir):
            continue
        
        # Modify Donghuastream.kt
        ds_kt = os.path.join(ds_dir, "src", "main", "kotlin", "com", "sad25kag", "Donghuastream", "Donghuastream.kt")
        if os.path.exists(ds_kt):
            try:
                with open(ds_kt, "r", encoding="utf-8") as f:
                    code = f.read()
                
                # Regex matching Donghuastream with optional [Backup]
                name_pattern = re.compile(r'(override\s+(?:var|val)\s+name\s*(?::\s*String)?\s*=\s*)(["\'])(Donghuastream)(?:\s*\[Backup\])?\2')
                code = name_pattern.sub(r'\1\2#Donghua \3\2', code)
                
                with open(ds_kt, "w", encoding="utf-8") as f:
                    f.write(code)
                print(f"[RENAME] Updated name in {item}/Donghuastream.kt to #Donghua Donghuastream")
            except Exception as e:
                print(f"Error renaming name in {item}/Donghuastream.kt: {e}")

if __name__ == "__main__":
    main()
