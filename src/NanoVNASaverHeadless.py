from Hardware import Hardware as hw
from Hardware.VNA import VNA

ifaces = hw.get_interfaces()
iface = hw.get_interfaces()[0]
print(ifaces, iface)
vna = VNA(iface)
#print(hw.get_comment(iface))

vna1 = hw.get_VNA(iface)
vna.connect()
vna.reconnect()
quit()
#print(hw.get_portinfos())
#print(hw.detect_version(iface))
print("VNA is connected: ", vna.connected())
print("VNA1 is connected: ", vna1.connected())
vna1.reconnect()

print(vna1.readFirmware())
print(vna1.read_features())
print(vna1.setSweep(1000, 2000))
data = vna1.readValues("data 0")

vna.disconnect()
