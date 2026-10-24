"""Build a platform-specific portable package; run on its target OS."""
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
from importlib.metadata import distributions
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAME = 'DataQualityDetective'


def check_mac_install(folder, temporary):
    """Test moving the bundle and opening it through macOS Launch Services."""
    moved = Path(temporary) / 'Applications copy with spaces' / folder.name
    shutil.copytree(folder, moved, symlinks=True)
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(moved)], check=True)
    report = Path(temporary) / 'launch-services.json'
    subprocess.run(['open', '-W', '-n', str(moved), '--args', '--self-test', '--self-test-report', str(report)], check=True, timeout=120)
    assert report.exists() and json.loads(report.read_text())['passed'], 'Launch Services self-test did not complete successfully'
    # Add quarantine to a disposable copy; never remove it or weaken system policy.
    subprocess.run(['xattr', '-w', 'com.apple.quarantine', f'0081;{int(time.time()):08x};DQDPackageTest;{uuid.uuid4()}', str(moved)], check=True)
    results = {'launch_services': True, 'moved_bundle_integrity': True, 'quarantine_simulation': True}
    for name, command in [
        ('gatekeeper', ['spctl', '--assess', '--type', 'execute', '--verbose=4', str(moved)]),
        ('stapled_notarization_ticket', ['xcrun', 'stapler', 'validate', str(moved)]),
    ]:
        try:
            assessment = subprocess.run(command, capture_output=True, text=True, timeout=60)
            results[name] = {'exit_code': assessment.returncode, 'accepted': assessment.returncode == 0,
                             'output': (assessment.stdout+assessment.stderr).replace(str(moved), '<app>')[-3000:]}
        except subprocess.TimeoutExpired:
            results[name] = {'accepted': None, 'output': 'Assessment timed out; inconclusive.'}
    print('Mac bundle move and Launch Services checks passed. Security-policy assessment: '+json.dumps(results), flush=True)
    return results


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
    if system == 'Darwin':
        # Adding notices changes bundle resources, so renew its ad-hoc seal.
        subprocess.run(['codesign', '--force', '--deep', '--sign', '-', str(folder)], check=True)
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(folder)], check=True)
    subprocess.run([str(executable), '--self-test'], check=True, timeout=120)
    output = ROOT / 'desktop-dist'
    output.mkdir(exist_ok=True)
    archive = output / f'data-quality-detective-{label}.zip'
    verification = {'platform': platform.platform(), 'architecture': platform.machine(),
                    'binary_launch': True, 'extracted_full_gib_csv': False,
                    'excel_sheets_cleaning_formulas': True}
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
        if system == 'Darwin':
            subprocess.run(['codesign', '--verify', '--deep', '--strict', str(Path(temporary) / folder.name)], check=True)
        subprocess.run([str(extracted), '--self-test', '--large-file-test'], check=True, timeout=600)
        verification['extracted_full_gib_csv'] = True
        if system == 'Darwin':
            verification['mac_install'] = check_mac_install(Path(temporary) / folder.name, temporary)
        print('Extracted package passed Excel worksheet/cleaned-download checks and actual 1 GiB CSV browsing.', flush=True)
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.zip.sha256').write_text(f'{checksum}  {archive.name}\n', encoding='utf-8')
    verification['archive_sha256'] = checksum
    verification['limitations'] = 'Automated runner checks, not a human security assessment or a personal-device installation test. Gatekeeper rejection is expected without Developer ID/notarization; no security policies were disabled.'
    archive.with_suffix('.verification.json').write_text(json.dumps(verification, indent=2)+'\n', encoding='utf-8')
    print(f'Built and smoke-tested: {archive.name}')


if __name__ == '__main__':
    main()
