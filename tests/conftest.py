import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pytest


@pytest.fixture(scope="session")
def spark():
    from agri.spark_utils import get_spark
    return get_spark("tests")
