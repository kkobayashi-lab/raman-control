from __future__ import annotations
from .spectra import SpectraCollector
from .calibration import CoordTransformer
from .daq import DaqController
from pyAndorSDK2 import atmcd, atmcd_codes, atmcd_errors
import time
import numpy as np
from pyAndorSpectrograph.spectrograph import ATSpectrograph


class AndorSpectraCollector(SpectraCollector):
    _instance = None

    @classmethod
    def instance(
        cls,
        laser_controller: DaqController = None,
        coord_transformer: CoordTransformer = None,
    ) -> AndorSpectraCollector:
        if cls._instance is None:
            cls._instance = cls(laser_controller, coord_transformer)
        return cls._instance

    def __init__(self, laser_controller: DaqController = None, coord_transformer: CoordTransformer = None,):
        super().__init__(laser_controller, coord_transformer)
        self._spc = ATSpectrograph()
        self._spc.Initialize("")
        print('Loaded spectrograph')
        self._sdk = atmcd()
        self._sdk.Initialize("")
        print('Loaded atmcd')
        self._exposure = 1000
        self.set_temp(-70)


    def set_temp(self, temp: float, block=False):
        ret = self._sdk.SetTemperature(temp)
        print("Function SetTemperature returned {} target temperature {}".format(ret, temp))
        ret = self._sdk.CoolerON()
        print("Function CoolerON returned {}".format(ret))
        if block:
            while ret != atmcd_errors.Error_Codes.DRV_TEMP_STABILIZED:
                time.sleep(1)
                (ret, temperature) = self._sdk.GetTemperature()
                print("Function GetTemperature returned {} current temperature = {} ".format(
                        ret, temperature), end='\r')
            print("")
            print("Temperature stabilized")

    def get_temp(self) -> float:
        (ret, temperature) = self._sdk.GetTemperature()
        return temperature

    def print_temp(self) -> None:
        (ret, temperature) = self._sdk.GetTemperature()
        print("Function GetTemperature returned {} current temperature = {} ".format(
                ret, temperature), end='\r')

    def get_wavelength(self, port: int = 0) -> float:
        """
        Get the current center wavelength of the spectrograph.

        Parameters
        ----------
        port : int, default 0
            Spectrograph port index

        Returns
        -------
        float
            Current center wavelength in nm
        """
        ret, wavelength = self._spc.GetWavelength(port)
        return wavelength

    def set_wavelength(self, wavelength: float, port: int = 0):
        """
        Set the center wavelength of the spectrograph.

        Parameters
        ----------
        wavelength : float
            Target center wavelength in nm
        port : int, default 0
            Spectrograph port index
        """
        ret = self._spc.SetWavelength(port, wavelength)
        print("SetWavelength returned {} target wavelength {} nm".format(ret, wavelength))


    def get_number_gratings(self, port: int = 0) -> int:
        """
        Get the number of gratings available on the turret.

        Parameters
        ----------
        port : int, default 0
            Spectrograph device index

        Returns
        -------
        int
            Number of gratings installed
        """
        ret, num_gratings = self._spc.GetNumberGratings(port)
        print("GetNumberGratings returned {} num gratings {}".format(ret, num_gratings))
        return num_gratings

    def get_grating(self, port: int = 0) -> int:
        """
        Get the currently selected grating.

        Parameters
        ----------
        port : int, default 0
            Spectrograph device index

        Returns
        -------
        int
            Current grating number (1-indexed)
        """
        ret, grating = self._spc.GetGrating(port)
        return grating

    def set_grating(self, grating: int, port: int = 0):
        """
        Set the active grating on the turret.

        Parameters
        ----------
        grating : int
            Target grating number (1-indexed, must be <= number of gratings)
        port : int, default 0
            Spectrograph device index
        """
        ret = self._spc.SetGrating(port, grating)
        print("SetGrating returned {} target grating {}".format(ret, grating))
        return ret

    def get_grating_info(self, grating: int, port: int = 0, max_blaze_len: int = 64):
        """
        Get information about a specific grating.

        Parameters
        ----------
        grating : int
            Grating number to query (1-indexed)
        port : int, default 0
            Spectrograph device index
        max_blaze_len : int, default 64
            Buffer length for the blaze string

        Returns
        -------
        tuple
            (lines_per_mm, blaze, home, offset)
        """
        ret, lines, blaze, home, offset = self._spc.GetGratingInfo(port, grating, max_blaze_len)
        print("GetGratingInfo returned {}".format(ret))
        print("\tGrating no {}".format(grating))
        print("\tLines/mm: {}".format(lines))
        print("\tBlaze: {}".format(blaze))
        print("\tHome: {}".format(home))
        print("\tOffset: {}".format(offset))
        return lines, blaze, home, offset

    def set_rm_exposure(self, exposure: float):
        self._sdk.SetExposureTime(exposure/1000)
        self._exposure = exposure

    def collect_spectra_volts(self, volts, exposure: float):
        exposure = exposure / 1000
        volts = np.ascontiguousarray(volts)
        self._daq_controller.prepare_for_collection(np.ascontiguousarray(volts.T))
        N = volts.shape[0]
        self._sdk.SetAcquisitionMode(atmcd_codes.Acquisition_Mode.KINETICS)
        ret = self._sdk.SetReadMode(atmcd_codes.Read_Mode.FULL_VERTICAL_BINNING)
        self._sdk.SetBaselineClamp(0)
        self._sdk.SetPreAmpGain(0)
        self._sdk.SetHSSpeed(0, 2)
        self._sdk.SetVSSpeed(0)
        self._sdk.SetExposureTime(exposure)
        self._sdk.SetNumberAccumulations(1)
        self._sdk.SetNumberKinetics(N)
        self._sdk.SetOutputAmplifier(0)
        self._sdk.SetEMGainMode(0)
        self._sdk.PrepareAcquisition()
        self._sdk.StartAcquisition()
        while self._sdk.GetStatus()[1] == atmcd_errors.Error_Codes.DRV_ACQUIRING:
            time.sleep(0.1)
            print(self._sdk.GetAcquisitionProgress(), end="\r")
        data_size = N * 2000
        ret, data = self._sdk.GetAcquiredData(data_size)
        data = data.reshape(N, 2000)
        return data

    def collect_spectra_pts(self, volts, exposure: float):
        exposure = exposure / 1000
        volts = np.ascontiguousarray(volts)
        self._daq_controller.prepare_for_collection(np.ascontiguousarray(volts.T))
        N = volts.shape[0]
        self._sdk.SetAcquisitionMode(atmcd_codes.Acquisition_Mode.KINETICS)
        ret = self._sdk.SetReadMode(atmcd_codes.Read_Mode.FULL_VERTICAL_BINNING)
        self._sdk.SetBaselineClamp(0)
        self._sdk.SetPreAmpGain(0)
        self._sdk.SetHSSpeed(0, 2)
        self._sdk.SetVSSpeed(0)
        self._sdk.SetExposureTime(exposure)
        self._sdk.SetNumberAccumulations(1)
        self._sdk.SetNumberKinetics(N)
        self._sdk.SetOutputAmplifier(0)
        self._sdk.SetEMGainMode(0)
        self._sdk.PrepareAcquisition()
        self._sdk.StartAcquisition()
        while self._sdk.GetStatus()[1] == atmcd_errors.Error_Codes.DRV_ACQUIRING:
            time.sleep(0.1)
            print(self._sdk.GetAcquisitionProgress(), end="\r")
        data_size = N * 2000
        ret, data = self._sdk.GetAcquiredData(data_size)
        data = data.reshape(N, 2000)
        return data

    def collect_spectra_pts_batch(self, volts, exposure: float):
        exposure = exposure / 1000
        volts = np.ascontiguousarray(volts)
        self._daq_controller.prepare_for_collection(np.ascontiguousarray(volts.T), batch=True, exposure=exposure)
        N = 1
        self._sdk.SetAcquisitionMode(atmcd_codes.Acquisition_Mode.KINETICS)
        ret = self._sdk.SetReadMode(atmcd_codes.Read_Mode.FULL_VERTICAL_BINNING)
        self._sdk.SetBaselineClamp(0)
        self._sdk.SetPreAmpGain(0)
        self._sdk.SetHSSpeed(0, 2)
        self._sdk.SetVSSpeed(0)
        self._sdk.SetExposureTime(exposure)
        self._sdk.SetNumberAccumulations(1)
        self._sdk.SetNumberKinetics(N)
        self._sdk.SetOutputAmplifier(0)
        self._sdk.SetEMGainMode(0)
        self._sdk.PrepareAcquisition()
        self._sdk.StartAcquisition()
        while self._sdk.GetStatus()[1] == atmcd_errors.Error_Codes.DRV_ACQUIRING:
            time.sleep(0.1)
            print(self._sdk.GetAcquisitionProgress(), end="\r")
        data_size = N * 2000
        ret, data = self._sdk.GetAcquiredData(data_size)
        data = data.reshape(N, 2000)
        return data

    def close(self):
        self._daq_controller.close()
        self._sdk.ShutDown()
        self._spc.Close()