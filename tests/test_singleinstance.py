import pytest

from ravan.platform.singleinstance import SingleInstance

pytestmark = pytest.mark.windows


def test_single_instance_acquisition_and_release():
    s1 = SingleInstance("TestRavanUnit")
    try:
        assert s1.acquired is True

        # Second instance must fail to acquire while first is held
        s2 = SingleInstance("TestRavanUnit")
        try:
            assert s2.acquired is False
        finally:
            s2.release()
    finally:
        s1.release()

    # After release, acquisition should succeed again
    s3 = SingleInstance("TestRavanUnit")
    try:
        assert s3.acquired is True
    finally:
        s3.release()
