from pcdsdaq.ami import AmiDet

ami_ipm2 = AmiDet("XPP-SB2-BMMON:SUM", name="ipm2_sum")
ami_ipm3 = AmiDet("XPP-SB3-BMMON:SUM", name="ipm3_sum")

from types import SimpleNamespace
ami_ipm_usr = SimpleNamespace()
ami_ipm_usr.ch0 = AmiDet("XppEnds_Ipm0:FEX:CH0", name="ipm_usr_ch0")
ami_ipm_usr.ch1 = AmiDet("XppEnds_Ipm0:FEX:CH1", name="ipm_usr_ch1")
ami_ipm_usr.ch2 = AmiDet("XppEnds_Ipm0:FEX:CH2", name="ipm_usr_ch2")
ami_ipm_usr.ch3 = AmiDet("XppEnds_Ipm0:FEX:CH3", name="ipm_usr_ch3")

ami_ipm_mon = SimpleNamespace()
ami_ipm_mon.ch0 = AmiDet("XppMon_Pim0:FEX:CH0", name="ipm_mon_ch0")
ami_ipm_mon.ch1 = AmiDet("XppMon_Pim0:FEX:CH1", name="ipm_mon_ch1")
ami_ipm_mon.ch2 = AmiDet("XppMon_Pim0:FEX:CH2", name="ipm_mon_ch2")
ami_ipm_mon.ch3 = AmiDet("XppMon_Pim0:FEX:CH3", name="ipm_mon_ch3")


ami_ipm_sb3 = SimpleNamespace()
ami_ipm_sb3.ch0 = AmiDet("XppSb3_Pim:FEX:CH0", name="ipm_sb3_ch0")
ami_ipm_sb3.ch1 = AmiDet("XppSb3_Pim:FEX:CH1", name="ipm_sb3_ch1")
ami_ipm_sb3.ch2 = AmiDet("XppSb3_Pim:FEX:CH2", name="ipm_sb3_ch2")
ami_ipm_sb3.ch3 = AmiDet("XppSb3_Pim:FEX:CH3", name="ipm_sb3_ch3")

#from ophyd import Device, Component as Cpt
#class AmiIpm(Device):
#    ch0 = Cpt(AmiDet, ':CH0', name='ch0')
#    ch1 = Cpt(AmiDet, ':CH1', name='ch1')
#    ch2 = Cpt(AmiDet, ':CH2', name='ch2')
#    ch3 = Cpt(AmiDet, ':CH3', name='ch3')
#    sum = Cpt(AmiDet, ':SUM', name='sum')

#ami_ipm_sb3_02 = AmiIpm('XppSb3_Pim:FEX', name='ipm_sb3_02')
