from Hardware import Hardware as hw
from Hardware.VNA import VNA

iface = hw.get_interfaces()[0]

vna = hw.get_VNA(iface)
#vna.connect()
#vna.reconnect()

#print(hw.get_portinfos())
#print(hw.detect_version(iface))
print("VNA is connected: ", vna.connected())
vna.reconnect()

print(vna.readFirmware())
print(vna.read_features())
print(vna.setSweep(1000, 2000))
data = vna.readValues("data 0")

vna.disconnect()
