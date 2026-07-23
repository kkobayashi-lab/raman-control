import numpy as np
import pytest

from raman_control.spectral_axis import wavelengths_to_raman_shift


def test_wavelengths_to_raman_shift():
    wavelengths = np.array([785.0, 881.923])

    shifts = wavelengths_to_raman_shift(wavelengths, 785.0)

    assert shifts[0] == pytest.approx(0.0)
    assert shifts[1] == pytest.approx(1400.0, abs=1.0)


@pytest.mark.parametrize(
    ("wavelengths", "laser"),
    [
        ([], 785.0),
        ([785.0, 0.0], 785.0),
        ([785.0], 0.0),
    ],
)
def test_invalid_calibration_is_rejected(wavelengths, laser):
    with pytest.raises(ValueError):
        wavelengths_to_raman_shift(wavelengths, laser)
