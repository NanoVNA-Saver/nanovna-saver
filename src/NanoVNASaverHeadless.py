from Hardware import Hardware as hw
from Hardware.VNA import VNA

iface = hw.get_interfaces()[0]

vna = hw.get_VNA(iface)
#vna.connect()
#vna.reconnect()

#print(hw.get_portinfos())
#print(hw.detect_version(iface))

print(vna.setSweep(1000, 2000))
data = vna.readValues("data 0")

vna.disconnect()

class NanoVNASaverHeadless:
    def __init__(self, vna_index=0, verbose=False):
        self.verbose = verbose
        self.iface = hw.get_interfaces()[vna_index]
        self.vna = hw.get_VNA(iface)
        if self.verbose:
            print("VNA is connected: ", self.vna.connected())
            print("Firmware: ", self.vna.readFirmware())
            print("Features: ", self.vna.read_features())

    def calibrate(self):
        pass

    def set_sweep(self):
        pass

    def stream_data(self):
        pass

    def kill(self):
        self.vna.disconnect()
        if self.vna.connected():
            raise Exception("The VNA was not successfully disconnected.")
        else:
            if self.verbose:
                print("Disconnected VNA.")
            return
