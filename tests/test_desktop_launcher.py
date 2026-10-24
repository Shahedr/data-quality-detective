from desktop_launcher import LocalApp


def test_desktop_stays_local_even_with_hosted_environment(monkeypatch):
    monkeypatch.setenv('VERCEL', '1')
    monkeypatch.setenv('DQD_PUBLIC_DEMO_ONLY', '1')
    local = LocalApp()
    assert local.server.config.host == '127.0.0.1'
    assert not local.server.config.proxy_headers
    from webapp.app import _public_demo_only
    assert not _public_demo_only()


def test_startup_failure_is_reported_to_launcher(monkeypatch):
    local = LocalApp()
    def fail():
        raise OSError('Test port unavailable')
    monkeypatch.setattr(local.server, 'run', fail)
    local.thread.start()
    assert local.stop()
    assert local.error == 'Test port unavailable'
