with open("whitemagic/autonomous/__init__.py") as f:
    lines = f.readlines()

out_lines = []
skip = False
for line in lines:
    if line.startswith("from .diary import"):
        skip = True
    elif skip and line.strip() == ")":
        skip = False
        continue
    elif not skip:
        out_lines.append(line)

with open("whitemagic/autonomous/__init__.py", "w") as f:
    f.writelines(out_lines)
