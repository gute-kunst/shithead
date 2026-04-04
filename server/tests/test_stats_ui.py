from fastapi.testclient import TestClient

from pyshithead.main import app


def test_stats_ui_page_and_assets_are_served_separately():
    with TestClient(app, base_url="http://localhost") as client:
        page = client.get("/stats-ui")
        assert page.status_code == 200
        assert "Shithead Stats" in page.text
        assert "/stats-ui/styles.css" in page.text
        assert "/stats-ui/stats.js" in page.text
        assert "/static/app.js" not in page.text

        script = client.get("/stats-ui/stats.js")
        assert script.status_code == 200
        assert "/stats?days=${days}" in script.text

        styles = client.get("/stats-ui/styles.css")
        assert styles.status_code == 200
