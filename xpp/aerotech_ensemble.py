import socket
import sys
import time
import numpy as np

import logging

from typing import Optional, Union
from prettytable import PrettyTable

logger = logging.getLogger()
# logger.setLevel(logging.DEBUG)

# handler = logging.StreamHandler(sys.stdout)
# handler.setLevel(logging.DEBUG)
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# handler.setFormatter(formatter)
# logger.addHandler(handler)



HOST = "172.21.84.235"
# HOST = "172.21.84.215"
PORT = 8000
TIMEOUT = 10

# status example: b'%-1675099646\n'
axis_status_bitmap = {
    'enabled': 0,
    'homed': 1,
    'in_position': 2,
    'move_active': 3,
    'CW': 22,
    'CCW': 23
}   

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
        #print(resp)
        if resp.startswith('!'):
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
        return str(pos)


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



class Ensemble(object):
    def __init__(
        self,
        host,
        port: int = 8000,
        ax_names: list[str] = ['0', '1', '2', '3', '4', '5', '6', '7']
        ) -> None:

        self.comm = EnsembleCommunicator(host, port)

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
        # resp = self.comm.send(cmd, sleep=wait)
        self.comm.send_no_resp(cmd)
        return
    

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




if __name__ == '__main__':
    host = HOST
    ens = Ensemble(host, ax_names=['r1', 't1', 'x1', 'x2', 'x3', 'x4', 'x5', 'x6',])
    
