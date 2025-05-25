import os
import shutil
import sys

# Path to extension directory
extension_dir = os.path.dirname(os.path.realpath(__file__))
scripts_dir = os.path.join(extension_dir, "scripts")
js_dir = os.path.join(extension_dir, "javascript")

# Make sure directories exist
os.makedirs(scripts_dir, exist_ok=True)
os.makedirs(js_dir, exist_ok=True)

# Ensure we're in a Forge/SD installation
forge_extensions_dir = None

# Try to find Forge extensions directory
potential_paths = [
    os.path.join(os.path.dirname(extension_dir), "extensions"),  # If installed in SD web UI
    os.path.join(os.path.dirname(os.path.dirname(extension_dir)), "extensions"),  # One level up
]

for path in potential_paths:
    if os.path.isdir(path):
        forge_extensions_dir = path
        break

if not forge_extensions_dir:
    print("Error: Could not find Forge extensions directory.")
    print("Please make sure this extension is installed in the correct location.")
    sys.exit(1)

print("StableQueue Forge Extension Installation")
print("---------------------------------------")
print(f"Extension directory: {extension_dir}")
print(f"Forge extensions directory: {forge_extensions_dir}")

# Check if we're already in the extensions directory
if os.path.dirname(extension_dir) == forge_extensions_dir:
    print("Extension is already installed in the correct location.")
else:
    # Move the extension to the extensions directory
    target_dir = os.path.join(forge_extensions_dir, "stablequeue")
    
    if os.path.exists(target_dir):
        print(f"Warning: {target_dir} already exists. Removing...")
        shutil.rmtree(target_dir)
    
    print(f"Moving extension to {target_dir}...")
    shutil.copytree(extension_dir, target_dir)
    print("Extension moved successfully.")

print("Installation complete!")
print("Please restart Forge to load the extension.") 