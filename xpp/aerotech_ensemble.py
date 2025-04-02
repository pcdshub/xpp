import socket
import sys
import time
import numpy as np

import logging

from typing import Optional, Union
from prettytable import PrettyTable

from enum import Enum

logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)



#HOST = "172.21.84.235"
HOST = "172.21.84.215"
PORT = 8000
TIMEOUT = 5

# status example: b'%-1675099646\n'
axis_status_bitmap = {
    'enabled': 0,
    'homed': 1,
    'in_position': 2,
    'move_active': 3,
    'CW': 22,
    'CCW': 23
}

class TaskState(Enum):
    Inactive = 0
    Idle = 1
    Ready = 2
    Running = 3
    Paused = 4
    Complete = 5
    Error_ = 6

class SentinelFct(Enum):
    cmdNOTHING = 0
    cmdABORT = 1
    cmdVELOCITY_ON = 2
    cmdVELOCITY_OFF = 3
    cmdANALOGTRACK = 4

class AnalogTrackMode(Enum):
    Off = 0
    PosCommand = 1
    PosFeedback = 2
    VelocityCommand = 3
    VelocityFeedback = 4
    CurrentCommand = 5
    CurrentFeedback = 6
    AccCommand = 7
    PosError = 8


class EnsembleCommunicator():
    def __init__(self, host, port):
        """
        Setup socket and standard pattern for communicaiton
        with the Aerotech Ensemble EPAQ controller.
        """
        #self.sock = socket.create_connection((host, port), timeout=TIMEOUT)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(TIMEOUT)
        self.sock.connect((host, port))
        return


    def send(self, cmd: Union[str, bytes], sleep: Optional[float] = None) -> str:
        if isinstance(cmd, str):
            if cmd[-1] != '\n':
                cmd += "\n"
            cmd = bytes(cmd, 'ascii')

        logger.debug(cmd)
        st = self.sock.send(cmd)
        if sleep:
            time.sleep(sleep)
        time.sleep(0.2)
        resp = self.sock.recv(1024)
        logger.debug(resp)
        resp = resp.decode('ascii')
        if not resp.startswith('%'):
            print('Command error:')
            print(f"Command: {cmd}")
            print(f"Response: {resp}")
        resp = resp[1:-1]
        return resp


    def send_no_resp(self, cmd) -> None:
        if isinstance(cmd, str):
            if cmd[-1] != '\n':
                cmd += "\n"
            cmd = bytes(cmd, 'ascii')

        logger.debug(cmd)
        st = self.sock.send(cmd)
        return


    def resp_all(self) -> None:
        cmd = 'PLANESTATUS(0)'
        resp = self.send(cmd)
        if resp == '':
            resp = self.resp_all()
        return




class EnsembleAxis(object):
    def __init__(self, idx, comm, name: Optional[str ]= None) -> None:
        self.idx = idx
        self.comm = comm
        self.name = name
        if name is None:
            self.name = str(idx)
        else:
            self.name = name

        self._ax = f"@{idx}" # Index-based Ensemble axis format

        self.velocity = 0.1
        self._accel = None

        # function alias
        self.mv = self.move_abs
        self.mvr = self.move_inc
        self.stop = self.abort
        return


    def __repr__(self):
        pos = self.get_pos()
        s = f'{self.name} current position: {pos}'
        return s


    def get_pos(self) -> float:
        """
        Get axis current position
        """
        cmd = f"CMDPOS({self._ax})"
        resp = self.comm.send(cmd)
        # if resp == '':
        #     resp = self.get_pos()
        pos = float(resp)
        return pos


    @property
    def accel(self):
        return self._accel


    @accel.setter
    def accel(self, value: float):
        cmd = f"RAMP RATE {self._ax} {value}"
        resp = self.comm.send(cmd)
        self._accel = value
        return


    def status(self):
        """
        Get status of axis from controller.
        """
        cmd = f"AXISSTATUS {self._ax}"
        resp = self.comm.send(cmd)
        status = self.format_axis_status(resp)
        return status


    @staticmethod
    def format_axis_status(status):
        status = status.split('-')[-1].split('\n')[0]
        status = bin(int(status))[2:]
        status = int(status,2)

        # check various status bits
        t = PrettyTable(header=False, align='l')
        for info, bit in axis_status_bitmap.items():
            st = bool(status & (0x1 << bit))
            t.add_row([info, st])
        print(t)
        return status


    def enable(self) -> None:
        """
        Enable one or all axis.
        """
        cmd = f"ENABLE {self._ax}"
        resp = self.comm.send(cmd)
        return


    def disable(self) -> None:
        """
        Disable one or all axis.
        """
        cmd = f"DISABLE {self._ax}"
        resp = self.comm.send(cmd)
        return resp


    def abort(self) -> None:
        cmd = f"ABORT {self._ax}"
        resp = self.comm.send(cmd)
        return


    def home(self) -> None:
        cmd = f"HOME {self._ax}"
        resp = self.comm.send(cmd)
        return resp


    def move_abs(
        self,
        pos: float, 
        velocity: float = None,
        enable: bool = False
        ) -> None:
        """
        Parameters
        ----------
        pos: float
            Target position
        enable: bool
            Whether to enable to axis before moving. False by default for safety.
        """
        if enable:
            self.enable() # enable ax
        if velocity is None:
            velocity = self.velocity
        cmd = f"MOVEABS {self._ax} {pos} F{velocity}"
        resp = self.comm.send(cmd)
        return resp


    def move_inc(
        self,
        pos: float, 
        velocity: float = None,
        enable: bool = False
        ) -> None:
        """
        Parameters
        ----------
        pos: float
            Target position
        enable: bool
            Whether to enable to axis before moving. False by default for safety.
        """
        if enable:
            self.enable() # enable ax
        if velocity is None:
            velocity = self.velocity
        cmd = f"MOVEINC {self._ax} {pos} F{velocity}"
        resp = self.comm.send(cmd)
        return resp


    def set_current_position(self, pos: float) -> None:
        """
        Set axis current position without moving anything
        """
        cmd = f"POSOFFSET SET {self._ax}, {pos}"
        resp = self.comm.send(cmd)
        return resp


    def clear_current_position(self) -> None:
        """
        Remove current position offset, if any
        """
        cmd = f"POSOFFSET CLEAR {self._ax}"
        resp = self.comm.send(cmd)
        return resp


class EnsembleSentinel():
    def __init__(self, comm):
        self.comm = comm

        # make sure no command will run by default
        self.write_register('int', 100, 0)
        return


    def run(self):
        cmd = 'PROGRAM RUN 1, "sentinel.bcx"'
        resp = self.comm.send(cmd)
        time.sleep(1)
        print(self.state)
        return


    def stop(self):
        cmd = "PROGRAM STOP 1"
        resp = self.comm.send(cmd)
        time.sleep(1)
        print(self.state)
        return


    @property
    def state(self):
        cmd = "TASKSTATE(1)"
        resp = int(self.comm.send(cmd))
        state = TaskState(resp)
        return state


    def write_register(self, reg_type: str, idx: int, val: Union[int, float]):
        if reg_type == 'int':
            cmd = f"IGLOBAL({idx})={val}"
        elif reg_type == 'double':
            cmd = f"DGLOBAL({idx})={val}"
        else:
            raise ValueError("Register type not recognized. 'int' or 'double' only.")
        resp = self.comm.send(cmd)
        time.sleep(0.1)
        val = self.read_register(reg_type, idx)
        logger.info(f'{reg_type} register at idx {idx} = {val}')
        return


    def read_register(self, reg_type: str, idx: int):
        if reg_type == 'int':
            cmd = f"IGLOBAL({idx})"
        elif reg_type == 'double':
            cmd = f"DGLOBAL({idx})"
        else:
            raise ValueError("Register type not recognized. 'int' or 'double' only.")
        val = self.comm.send(cmd)
        return val



class Ensemble(object):
    def __init__(
        self,
        host,
        port: int = 8000,
        ax_names: list[str] = ['x0', 'x1', 'x2', 'x3', 'x4', 'x5', 'x6', 'x7'],
        sentinel: bool = True
        ) -> None:

        self.comm = EnsembleCommunicator(host, port)
        self.sentinel = None
        if sentinel:
            self.sentinel = EnsembleSentinel(self.comm)

        for ii, name in enumerate(ax_names):
            axis = EnsembleAxis(ii, self.comm, name)
            setattr(self, f"m{ii}", axis)
            setattr(self, f"{name}", axis)

        self._scurve = None
        self._accel = None
        return


    def get_ax(self, ax: Union[str, int]) -> EnsembleAxis:
        """
        Returns the axis instance based on either idx or name input
        """
        if isinstance(ax, int): # idx case
            ax = getattr(self, f"m{ax}")
            return ax
        elif isinstance(ax, str): # name case
            gen = (getattr(self, _ax) for _ax in self.__dict__ if isinstance(getattr(self, _ax), EnsembleAxis))
            for _ax in gen:
                if _ax.name == ax:
                    return _ax
            print('Could not find a corresponding axis.')
        else:
            print('Could not find a corresponding axis.')
        return


    def ack_all(self) -> None:
        """
        Acknowledge all faults and move on.
        """
        cmd = "ACKNOWLEDGEALL"
        resp = self.comm.send(cmd)
        return

    def abort(self):
        gen = (getattr(self, _ax) for _ax in self.__dict__ \
                if isinstance(getattr(self, _ax), EnsembleAxis))
        for _ax in gen:
            print(f"Aborting axis {_ax.name}")
            _ax.abort()
        return


    def commit_parameters(self) -> None:
        cmd = "COMMITPARAMETERS"
        resp = self.comm.send(cmd)
        return


    def reset(self) -> None:
        cmd = "RESET"
        resp = self.comm.send(cmd)
        return


    def enable_all(self):
        for ii in range(8):
            ax = self.get_ax(ii)
            ax.enable()
        return


    def disable_all(self):
        for ii in range(8):
            ax = self.get_ax(ii)
            ax.disable()
        return


    @property
    def scurve(self):
        return self._scurve


    @scurve.setter
    def scurve(self, value: int) -> None:
        cmd = f"SCURVE {value}"
        resp = self.comm.send(cmd)
        self._scurve = value
        return


    @property
    def accel(self):
        return self._accel


    @accel.setter
    def accel(self, value: float):
        cmd = f"RAMP RATE {value}"
        resp = self.comm.send(cmd)
        self._accel = value
        return


    def linear(
        self,
        axs: list[str],
        positions: list[float],
        speed: float = None
        ) -> None:
        """
        Perform a linear move for a set of axis.

        Parameters
        ----------
        axis: List[str]
            List of axis to move
        pos: List[float]
            Corresponding position
        """
        cmd = "LINEAR "

        for ax, pos in zip(axs, positions):
            ax = self.get_ax(ax)
            cmd += f"{ax._ax} {pos} "
        if speed is not None:
            cmd += f"F {speed}"
        wait = max(np.abs(positions))/speed
        logger.info(f"Linear command: {cmd}")
        # resp = self.comm.send(cmd, sleep=wait)
        self.comm.send(cmd)
        return


    def _sentinel_running(self):
        """ Checks if the sentinel program is running """
        if self.sentinel.state is not TaskState.Running:
            error_msg = ("This functionality requires the sentinel program. "
                         "Please make sure the sentinel program is running.")
            raise RuntimeError(error_msg)
        return 1


    def velocity_mode(self, cmd: bool):
        """
        Sets the velocity profiling mode on/off.
        Is based on the sentinel.ab program that must be compiled
        and loaded on the controller.
        """
        if bool(cmd) is True:
            cmd = f"IGLOBAL(10)=1"
        elif bool(cmd) is False:
            cmd = f"IGLOBAL(10)=2"
        resp = self.comm.send(cmd)
        return


    def analog_track(
            self,
            ax: Union[str, int],
            ao_channel: int = 1,
            mode: int = 2,
            scale: float = 0.0001,
            offset: float = 0):
        """
        See AnalogTrackMode Enum for info on the modes.
        """

        self._sentinel_running()
        ax = self.get_ax(ax)
        ax_idx = ax._ax.split('@')[1]

        print((f"Setting up analog track with mode {AnalogTrackMode(mode)} "
               f"for axis {ax.name} on ao channel {ao_channel} with scale "
               f"{scale} and offset {offset}."))

        # Write the analog track argument to pre-allocated Ensemble registers
        # See the sentinel.ab program for info on the allocation
        self.sentinel.write_register('int', 1, ax_idx)
        self.sentinel.write_register('int', 2, ao_channel)
        self.sentinel.write_register('int', 3, mode)
        self.sentinel.write_register('double', 1, scale)
        self.sentinel.write_register('double', 2, offset)

        # Tell the program to run analog track
        self.sentinel.write_register('int', 100, SentinelFct.cmdANALOGTRACK.value)
        return


    def analog_track_stop(self, ax: Union[str, int], ao_channel: int = 1):
        """ Stop analog track on given axis """
        self._sentinel_running()
        ax = self.get_ax(ax)
        ax_idx = ax._ax.split('@')[1]

        # Turn off analog track
        self.sentinel.write_register('int', 1, ax_idx)
        self.sentinel.write_register('int', 2, ao_channel)
        self.sentinel.write_register('int', 3, 0)
        self.sentinel.write_register('double', 1, 0.0)
        self.sentinel.write_register('double', 2, 0.0)

        # Tell the program to do nothing
        self.sentinel.write_register('int', 100, SentinelFct.cmdNOTHING.value)

        # Write 0 to the voltage output
        cmd = f"AOUT {ax._ax}, {ao_channel}:0"
        self.comm.send(cmd)
        return






if __name__ == '__main__':
    host = HOST
    ens = Ensemble(host,
                   ax_names = ['x1', 'x2', 'x3', 'x4', 'x5', 'x6', 'x7', 'x8',],
                   sentinel = True)

