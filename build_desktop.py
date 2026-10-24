"""Build a platform-specific portable package; run on its target OS."""
import hashlib
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile
from importlib.metadata import distributions
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAME = 'DataQualityDetective'


def main():
    system = platform.system()
    if system not in {'Windows', 'Darwin'}:
        raise SystemExit('Build on Windows or macOS.')
    label = 'windows-x64' if system == 'Windows' else 'mac-' + ('apple-silicon' if platform.machine() == 'arm64' else 'intel')
    subprocess.run([
        sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', '--windowed',
        '--name', NAME, '--collect-submodules', 'uvicorn',
        '--add-data', 'webapp/static:webapp/static', '--add-data', 'webapp/sample.csv:webapp',
        '--hidden-import', 'webapp.app', '--hidden-import', 'openpyxl',
        'desktop_launcher.py',
    ], cwd=ROOT, check=True)
    folder = ROOT / 'dist' / (NAME + '.app' if system == 'Darwin' else NAME)
    executable = folder / ('Contents/MacOS/' + NAME if system == 'Darwin' else NAME + '.exe')
    notices = folder / ('Contents/Resources/licenses' if system == 'Darwin' else 'licenses')
    notices.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / 'LICENSE', notices / 'DataQualityDetective-LICENSE.txt')
    shutil.copy2(ROOT / 'licenses/Python-LICENSE.txt', notices / 'Python-LICENSE.txt')
    shutil.copy2(ROOT / 'DESKTOP_DOWNLOADS.md', notices.parent / 'READ_ME_FIRST.md')
    for package in distributions():
        for entry in package.files or []:
            if '.dist-info/licenses/' in str(entry).replace('\\', '/'):
                target = notices / str(entry)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(package.locate_file(entry), target)
    subprocess.run([str(executable), '--self-test'], check=True, timeout=120)
    output = ROOT / 'desktop-dist'
    output.mkdir(exist_ok=True)
    archive = output / f'data-quality-detective-{label}.zip'
    if system == 'Darwin':
        subprocess.run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', str(folder), str(archive)], check=True)
    else:
        shutil.make_archive(str(archive.with_suffix('')), 'zip', root_dir=folder.parent, base_dir=folder.name)
    with tempfile.TemporaryDirectory() as temporary:
        if system == 'Darwin':
            subprocess.run(['ditto', '-x', '-k', str(archive), temporary], check=True)
        else:
            with zipfile.ZipFile(archive) as zipped:
                zipped.extractall(temporary)
        extracted = Path(temporary) / folder.name / executable.relative_to(folder)
        subprocess.run([str(extracted), '--self-test'], check=True, timeout=120)
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.zip.sha256').write_text(f'{checksum}  {archive.name}\n', encoding='utf-8')
    print(f'Built and smoke-tested: {archive.name}')


if __name__ == '__main__':
    main()
