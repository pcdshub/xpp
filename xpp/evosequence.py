import logging

logger = logging.getLogger(__name__)

#####
# XPP event code
#####
# 94 PP      (MFX: 197)
# 95 DAQ     (MFX: 198)
# 193 EVO    (MFX: 210)
# 194 EVO-1  (MFX :211)
# 215 EVO-2  (MFX :212)
# 216 EVO-3  (MFX :213)

class Evosequence:
    def __init__(self, sequencer):
        self.sequencer = sequencer

    @property
    def current_rate(self):
        """Current configured EventSequencer rate"""
        delta = self.sequencer.sequence.get_seq()[0][1]
        rate = 120/(delta + 3)
        return int(rate)

    def configure_sequencer(self, rate=30, show_seq=True):
        """
        Setup laser triggers and EventSequencer

        Parameters
        ----------
        rate : int or str, optional
            Any of the following rates
            30Hz, 24Hz, 20Hz, 15Hz, 12Hz, 10Hz,
            8Hz, 6Hz, 5Hz, 4Hz, 3Hz, 2Hz, 1Hz
        """
        logger.info("Configure EventSequencer ...")
        valid_rates = (60, 30, 24, 20, 15, 12, 10, 8, 6, 5, 4, 3, 2, 1)

        if isinstance(rate, str):
            rate = int(rate[:-2])
        elif isinstance(rate, float):
            if rate.is_integer():
                rate = int(rate)

        if rate not in valid_rates:
            raise RuntimeError('Invalid rate, recieved {} but must be one of '
                               '{}'.format(rate, valid_rates))

        if rate == 60:
            self.sequencer.sync_marker.put('60Hz')
            sequence = [[194, 1, 0, 0],
                        [193, 1, 0, 0],
                        [95, 0, 0, 0]]

        else:
            # Use sequence to regulate rate, not sync marker
            self.sequencer.sync_marker.put('120Hz')

            # Construct the sequence and submit
            delta = int(120/rate - 3)
#MFX:
#        sequence = [[213, 197, 212, 211, 210, 198],
#        sequence = [[216, 94, 215, 194, 193, 95],
#                    [delta, 1, 0, 1, 1, 0],
#                    [0, 0, 0, 0, 0, 0],
#                    [0, 0, 0, 0, 0, 0]]
            sequence = [[216, delta, 0, 0],
                        [94, 1, 0, 0],
                        [215, 0, 0, 0],
                        [194, 1, 0, 0],
                        [193, 1, 0, 0],
                        [95, 0, 0, 0]]



        retries = 5
        success = False
        for i in range(retries):
            self.sequencer.sequence.put_seq(sequence)
            read_seq = [list(s) for s in self.sequencer.sequence.get_seq()]
            if read_seq == sequence:
                success = True
                break

        if success:
            logger.info('Successfully configured sequencer')
        else:
            logger.error('Putting to sequencer failed!')

        if show_seq:
            self.sequencer.sequence.show()
