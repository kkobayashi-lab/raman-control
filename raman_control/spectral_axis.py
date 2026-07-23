"""Utilities for calibrated Raman spectral axes."""

from __future__ import annotations

import numpy as np


def wavelengths_to_raman_shift(
    wavelengths_nm,
    laser_wavelength_nm: float,
) -> np.ndarray:
    """Convert scattered-light wavelengths to relative wavenumbers.

    Parameters
    ----------
    wavelengths_nm : array-like
        Calibrated detector-column wavelengths in nanometers.
    laser_wavelength_nm : float
        Excitation laser wavelength in nanometers.

    Returns
    -------
    numpy.ndarray
        Raman shifts in inverse centimeters.
    """
    wavelengths = np.asarray(wavelengths_nm, dtype=float)
    laser_wavelength = float(laser_wavelength_nm)

    if wavelengths.ndim != 1 or wavelengths.size == 0:
        raise ValueError("LightField wavelength calibration must be a 1D array")
    if not np.all(np.isfinite(wavelengths)) or np.any(wavelengths <= 0):
        raise ValueError(
            "LightField wavelength calibration contains invalid values"
        )
    if not np.isfinite(laser_wavelength) or laser_wavelength <= 0:
        raise ValueError("LightField laser wavelength must be positive")

    return 1e7 * (1.0 / laser_wavelength - 1.0 / wavelengths)
