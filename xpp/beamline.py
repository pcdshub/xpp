from hutch_python.utils import safe_load


with safe_load('Robot'):
    from pcdsdevices import staubli_robot
    robot = staubli_robot.StaubliRobot('XPP:ROB', name='robot')

with safe_load('Robot calculation'):
    class Rob():
        def __init__(self):
            self.x = EpicsSignal('XPP:ROB:POS:X', name='robx')
            self.y = EpicsSignal('XPP:ROB:POS:Y', name='robz')
            self.z = EpicsSignal('XPP:ROB:POS:Z', name='robz')
            self.rx = EpicsSignal('XPP:ROB:POS:RX', name='robrx')
            self.ry = EpicsSignal('XPP:ROB:POS:RY', name='robrz')
            self.rz = EpicsSignal('XPP:ROB:POS:RZ', name='robrz')
            return
    rob = Rob()

    def rob_pixel_az_el(i, j, pix_size=0.075, origin=[0, 0, 100]):
        # get robot position and angles, buidl matrices and vectors
        x = rob.x.get()
        y = rob.y.get()
        z = rob.z.get()
        xyz_rob = np.array([[x,y,z]]).T
        origin = np.asarray([origin]).T
        print(f"Robot position: {xyz_rob.T}")
        print(f"Origin: {origin.T}\n")

        aa = rob.rx.get()
        ab = rob.ry.get()
        ac = rob.rz.get()
        Rx = np.array([ [1, 0, 0], [0, np.cos(aa), -np.sin(aa)], [0, np.sin(aa), np.cos(aa)] ])
        Ry = np.array([ [np.cos(ab), 0, np.sin(ab)], [0, 1, 0], [-np.sin(ab), 0, np.cos(ab)] ])
        Rz = np.array([ [np.cos(ac), -np.sin(ac), 0], [np.sin(ac), np.cos(ac), 0], [0, 0, 1]])

        # pos_xyz: in the robot frame
        pos_xyz = ( np.array([[-i, j, 0]]).T - origin ) * pix_size
        pos_xyz = Rx @ Ry @ Rz @ pos_xyz + xyz_rob - origin / pix_size

        print(f"pos_xyz: {pos_xyz.T}\n")

        el = np.rad2deg( -np.arctan(pos_xyz[2] / pos_xyz[1]) )[0]
        az = np.rad2deg( np.arctan(pos_xyz[0] / pos_xyz[1]) )[0]

        # calculate 2-theta
        u = np.cos(el) * np.sin(az)
        v = np.sin(el)
        tth  = np.arcsin( np.sqrt(u**2 + v**2) )
        tth = np.rad2deg(tth)
        print(f"2-theta = {tth}")
        return az, el, tth

