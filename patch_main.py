import os

file_path = "backend/main.py"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip = False
web_home_imported = False

for line in lines:
    if "from .routers import web_home" in line or "import web_home" in line:
        web_home_imported = True
    
    # Detect existing root route and skip it
    if '@app.get("/")' in line or "@app.get('/')" in line:
        skip = True
        # Add comment to indicate removal
        new_lines.append(f"# REMOVED OLD ROOT ROUTE: {line}")
        continue
    
    if skip:
        # Crude skip of the function body - assumes indentation
        if line.strip() and (line.startswith("def ") or line.startswith("@")):
            # End of skipped function?
            if line.startswith("@app"):
                skip = False
                new_lines.append(line)
            else:
                # Still inside function or decorator?
                # Actually, a new def stops the previous function if unindented
                # But we might be skipping a decorator stack.
                # Simplest: skip until we hit a line that starts with unindented text that is NOT the function def
                # But line.startswith("def ") is the function def we want to skip.
                if line.startswith("def "):
                    new_lines.append(f"# {line}") # Comment out the def
                    continue
                elif line.startswith(" "): # Indented body
                    new_lines.append(f"# {line}")
                    continue
                else:
                    # Unindented line, stop skipping
                    skip = False
                    new_lines.append(line)
        else:
            # Empty line or indented
            if skip:
                 new_lines.append(f"# {line}")
            else:
                 new_lines.append(line)
        continue

    new_lines.append(line)

# Add import if needed
if not web_home_imported:
    # Find a good place for import (after existing imports)
    # Just put it at the top?
    # backend/routers/web_home.py exists.
    # main.py is in backend/ and init is in backend/routers/
    # `from .routers import web_home` should work.
    new_lines.insert(0, "from .routers import web_home\n")

# Add include_router
# Check if already included
included = False
for line in new_lines:
    if "web_home.router" in line:
        included = True
        break

if not included:
    # Append at the end? Or find `app = ...` and append after?
    # Appending at the end is safest if app is global.
    new_lines.append("\n# Added by FourT Helper\napp.include_router(web_home.router)\n")

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Successfully patched backend/main.py")
