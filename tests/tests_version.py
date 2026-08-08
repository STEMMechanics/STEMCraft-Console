import re

from app.version import APP_VERSION


def test_version_format():

    assert re.fullmatch(
        r"\d+\.\d+\.\d+",
        APP_VERSION,
    )