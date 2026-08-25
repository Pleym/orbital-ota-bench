import sys

def test_python_version():
    assert sys.version_info.major == 3
    assert sys.version_info.minor >= 11

def test_imports():
    import fastapi
    import uvicorn
    import skyfield
    import sgp4
    import cryptography
    import jinja2
    assert fastapi.__version__ is not None
