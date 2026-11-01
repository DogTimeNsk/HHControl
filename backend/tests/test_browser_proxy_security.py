from pathlib import Path


def test_novnc_proxy_requires_the_dashboard_session() -> None:
    config = (Path(__file__).parents[2] / "docker" / "nginx.conf").read_text()
    assert "location = /_internal/browser-access" in config
    assert "proxy_pass $api_upstream/api/browser/access;" in config
    assert "location ~ ^/browser/(.*)$ {\n    auth_request /_internal/browser-access;" in config
