"""
This module holds the class for interacting with an Aerotech XYZ.
Author R.Cole
"""
import socket
import time

"""
I have modified the original class to be compatible with my current situation
1. One x axis is used.
2. Did not save log info

Author Haoyuan Li. 2020-10-21
"""

EOS_CHAR = '\n'  # End of string character
ACK_CHAR = '%'  # indicate success.
NAK_CHAR = '!'  # command error.
FAULT_CHAR = '#'  # task error.
TIMEOUT_CHAR = '$'

#################################
# Quantities specific to lv 18 experiment
#################################
ip_lv18 = "172.21.46.191"
port_lv18 = 8000

count_per_unit = 200000.


class Ensemble:
    """Class providing control over a single Aerotech XYZ stage."""

    def __init__(self, ip=ip_lv18, port=port_lv18):
        """
        Parameters
        ----------
        ip : str
            The ip of the Ensemble, e.g. 'localhost'
        port : int
            The port, default 8000
        """
        self._ip = ip
        self._port = port
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        print("Try to connect with ip={}  and port={}".format(self._ip, self._port))
        self.connect()

    #########################################################
    #   Fundamental functions
    #########################################################
    def connect(self):
        """Open the connection."""
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.connect((self._ip, self._port))
            print("Connected")
        except ConnectionRefusedError:
            print("Unble to connect.")

    def close(self):
        """Close the connection."""
        self._socket.close()
        print("Connection closed")

    def run(self, command):
        """This method writes a command and returns the response,
        checking for an error code.

        Parameters
        ----------
        command : str
            The command to be sent, e.g. HOME X

        Returns
        ----------
        response : str
            The response to a command
        """
        if EOS_CHAR not in command:
            command = ''.join((command, EOS_CHAR))

        self._socket.send(command.encode())
        read = self._socket.recv(4096).decode().strip()
        code, response = read[0], read[1:]
        if code != ACK_CHAR:
            print("Error from write_read(). The code is {}".format(code))
        return response

    #########################################################
    #   Utility functions
    #########################################################
    def enable(self):
        """This method homes the stage."""
        self.run('Enable X')
        print('Enable X')

    def disable(self):
        """This method homes the stage."""
        self.run('Disable X')
        print('Disable X')

    def home(self):
        """This method homes the stage."""
        self.run('HOME X')
        print('Homed')

    def move(self, x_pos, x_speed=1.0):
        """Move x axis to the specified position

        Parameters
        ----------
        x_pos : double
            The x position required
        x_speed: double
        """
        command = "MOVEABS X{:f} XF{:f}".format(x_pos, x_speed)
        self.run(command)
        print('Command written: {}'.format(command))

    def mover(self, x_pos, x_speed=1.0):
        """Move the position relatively

        Parameters
        ----------
        x_pos : double
            The x position required
        x_speed: double
        """
        # Move
        command = "MOVEINC X{:f} XF{:f}".format(x_pos, x_speed)
        self.run(command)
        print('Command written: {}'.format(command))

    def linear(self, displace, speed):
        """
        This seems to be similar to mover.

        :param displace:
        :param speed:
        :return:
        """
        # Move
        command = "LINEAR  X {:f} F {:f}".format(displace, speed)
        self.run(command)
        print('Command written: {}'.format(command))

    def get_positions(self):
        """Method to get the latest positions.

        Returns
        ----------
        positions : float
            The X positions.
        """
        x_pos = float(self.run('PFBK X'))
        return x_pos

    def clear_error(self):
        print("Try to clear all axis error of the aerotech stage.")
        self.run("ACKNOWLEDGEALL")
        print('Command written: ACKNOWLEDGEALL')

    #########################################################
    #   Delay scan
    #########################################################
    def constant_delay_scan(self, start, end, speed=1.0):
        """
        Perform a cycle motion between start and end.

        :param start:
        :param end:
        :param speed:
        :return:
        """
        # First move the stage to the start position
        self.move(x_pos=start, x_speed=speed)
        print("Move the stage to the start position:{}".format(start))

        forward_displace = end - start
        backward_displace = start - end

        # Begin the loop of motion
        print("Begin the delay scan cycle.")
        while True:
            # Move from start to end
            self.linear(displace=forward_displace, speed=speed)

            # Move the stage back
            self.linear(displace=backward_displace, speed=speed)


