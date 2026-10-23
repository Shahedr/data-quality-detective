"""Inventory only the current app runtime, excluding build/test/scanner packages."""
from importlib.metadata import distribution, PackageNotFoundError
from pathlib import Path
import tomllib

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

project = tomllib.loads(Path("pyproject.toml").read_text())["project"]
requirements = list(project['dependencies'])
for group in ['database', 'excel-native', 'macro-audit']:
    for item in project['optional-dependencies'][group]:
        try:
            distribution(Requirement(item).name)
        except PackageNotFoundError:
            continue
        requirements.append(item)
versions = {}
pending = [Requirement(r) for r in requirements]
while pending:
    requirement = pending.pop()
    if requirement.marker and not requirement.marker.evaluate({"extra": ""}):
        continue
    name = canonicalize_name(requirement.name)
    if name in versions:
        continue
    installed = distribution(name)
    versions[name] = installed.version
    pending.extend(Requirement(r) for r in installed.requires or [])
Path("runtime-audit-requirements.txt").write_text("\n".join(f"{name}=={version}" for name, version in sorted(versions.items())) + "\n")
print(f"Inventoried {len(versions)} installed runtime distributions")
