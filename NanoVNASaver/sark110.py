# ---------------------------------------------------------
"""
  This file is a part of the "SARK110 Antenna Vector Impedance Analyzer" software

  MIT License

  @author Copyright (c) 2020 Melchor Varela - EA4FRB

  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files (the "Software"), to deal
  in the Software without restriction, including without limitation the rights
  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  copies of the Software, and to permit persons to whom the Software is
  furnished to do so, subject to the following conditions:

  The above copyright notice and this permission notice shall be included in all
  copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
  SOFTWARE.
"""
# ---------------------------------------------------------
import os
import struct
import time

if os.name == 'nt':
    import pywinusb.hid as hid
    import threading
elif os.name == 'posix':
    import hid
else:
    raise ImportError("Error: no implementation for your platform ('{}') available".format(os.name))

SARK110_VENDOR_ID = 0x0483
SARK110_PRODUCT_ID = 0x5750

WAIT_HID_DATA_MS = 1000


class Sark110:
    _handler = 0
    _is_connect = 0
    _max_freq = 0
    _min_freq = 0
    _dev_name = ""
    _fw_version = ""
    _fw_protocol = -1

    @property
    def fw_version(self) -> str:
        return self._fw_version

    @property
    def fw_protocol(self) -> int:
        return self._fw_protocol

    @property
    def dev_name(self) -> str:
        return self._dev_name

    @property
    def max_freq(self) -> int:
        return self._max_freq

    @property
    def min_freq(self) -> int:
        return self._min_freq

    @property
    def is_connected(self) -> bool:
        return self._is_connect

    def __init__(self):
        self._handler = 0
        self._is_connect = 0

    def open(self) -> int:
        """
        Opens the device
        :return: <0 err; >0 ok
        """
        # Windows: pywinusb
        if os.name == 'nt':
            target_vendor_id = SARK110_VENDOR_ID
            target_product_id = SARK110_PRODUCT_ID
            hid_filter = hid.HidDeviceFilter(vendor_id=target_vendor_id, product_id=target_product_id)
            try:
                self._handler = hid_filter.get_devices()[0]
                if not self._handler:
                    return -1
                else:
                    self._handler.open()
                    self._handler.set_raw_data_handler(self._rx_handler)
                    return 1
            except:
                return -2

        # Linux: hidapi
        else:
            self._handler = hid.device()
            try:
                self._handler.open(SARK110_VENDOR_ID, SARK110_PRODUCT_ID)
                self._handler.set_nonblocking(0)
                return 1
            except IOError as ex:
                return -1

    def connect(self) -> int:
        """
        Connect to the device and get its characteristics
        :return: <0 err; >0 ok
        """
        if not self._handler:
            return -1
        if self._cmd_version() < 0:
            return -2
        self._is_connect = 1;
        return 1

    def close(self):
        """
        Closes the device
        :return:
        """
        if self._handler:
            self._handler.close()
        self._handler = 0
        self._is_connect = 0

    def measure(self, freq: int, rs: float, xs: float, cal=True, samples=1) -> int:
        """
        Takes one measurement sample at the specified frequency
        :param freq:    frequency in hertz; 0 to turn-off the generator
        :param cal:     True to get OSL calibrated data; False to get uncalibrated data
        :param samples: number of samples for averaging
        :param rs       real part of the impedance
        :param xs       imag part of the impedance
        :return: <0 err; >0 ok
        """
        if not self._is_connect:
            return -1
        snd = [0x0] * 19
        snd[1] = 2
        b = self._int2bytes(freq)
        snd[2] = b[0]
        snd[3] = b[1]
        snd[4] = b[2]
        snd[5] = b[3]
        if cal:
            snd[6] = 1
        else:
            snd[6] = 0
        snd[7] = samples
        rcv = self._send_rcv(snd)
        if rcv[0] != 79:
            return -2
        b = bytearray([0, 0, 0, 0])
        b[0] = rcv[1]
        b[1] = rcv[2]
        b[2] = rcv[3]
        b[3] = rcv[4]
        rs[0] = struct.unpack('f', b)
        b[0] = rcv[5]
        b[1] = rcv[6]
        b[2] = rcv[7]
        b[3] = rcv[8]
        xs[0] = struct.unpack('f', b)
        return 1

    def buzzer(self, freq=0, duration=0) -> int:
        """
        Sounds the sark110 buzzer.
        :param device:      handler
        :param freq:        frequency in hertz
        :param duration:    duration in ms
        :return: <0 err; >0 ok
        """
        if not self._is_connect:
            return -1
        snd = [0x0] * 19
        snd[1] = 20
        b = self._short2bytes(freq)
        snd[2] = b[0]
        snd[3] = b[1]
        b = self._short2bytes(duration)
        snd[4] = b[0]
        snd[5] = b[1]
        rcv = self._send_rcv(snd)
        if duration == 0:
            time.sleep(.2)
        else:
            time.sleep(duration / 1000)
        if rcv[0] == 79:
            return 1
        return -2

    def reset(self) -> int:
        """
        Resets the device
        :return: <0 err; >0 ok
        """
        if not self._is_connect:
            return -1
        snd = [0x0] * 19
        snd[1] = 50
        rcv = self._send_rcv(snd)
        if rcv == 79:
            return 1
        return -2

    def measure_ext(self, freq: int, step: int, rs: float, xs: float, cal=True, samples=1) -> int:
        """
        Takes four measurement samples starting at the specified frequency and incremented at the specified step
        Uses half float, so a bit less precise
        :param device:  handler
        :param freq:    frequency in hertz; 0 to turn-off the generator
        :param step:    step in hertz
        :param cal:     True to get OSL calibrated data; False to get uncalibrated data
        :param samples: number of samples for averaging
        :param rs       real part of the impedance (four vals)
        :param xs       imag part of the impedance (four vals)
        :return: <0 err; >0 ok
        """
        if not self._is_connect:
            return -1
        snd = [0x0] * 19
        snd[1] = 12
        b = self._int2bytes(freq)
        snd[2] = b[0]
        snd[3] = b[1]
        snd[4] = b[2]
        snd[5] = b[3]
        b = self._int2bytes(step)
        snd[8] = b[0]
        snd[9] = b[1]
        snd[10] = b[2]
        snd[11] = b[3]
        if cal:
            snd[6] = 1
        else:
            snd[6] = 0
        snd[7] = samples
        rcv = self._send_rcv(snd)
        if rcv[0] != 79:
            return -2

        rs[0] = self._half2float(rcv[1], rcv[2])
        xs[0] = self._half2float(rcv[3], rcv[4])
        rs[1] = self._half2float(rcv[5], rcv[6])
        xs[1] = self._half2float(rcv[7], rcv[8])
        rs[2] = self._half2float(rcv[9], rcv[10])
        xs[2] = self._half2float(rcv[11], rcv[12])
        rs[3] = self._half2float(rcv[13], rcv[14])
        xs[3] = self._half2float(rcv[15], rcv[16])

        return 1

    # ---------------------------------------------------------
    # Get version command: used to check the connection and dev params
    def _cmd_version(self):
        if not self._handler:
            return -1
        self._fw_protocol = 0
        self._fw_version = ""

        snd = [0x0] * 19
        snd[1] = 1
        rcv = self._send_rcv(snd)
        if rcv[0] != 79:
            return -2
        self._fw_protocol = (rcv[2] << 8) & 0xFF00
        self._fw_protocol += rcv[1] & 0xFF
        ver = [0x0] * 15
        ver[:] = rcv[3:]

        # Identifies the device
        if (self._fw_protocol & 0xff00) == 0x0100:
            self._max_freq = 200000000
            self._min_freq = 100000
            self._dev_name = "sark110 (100k to 200M)"
        elif (self._fw_protocol & 0xff00) == 0x0200:
            self._max_freq = 230000000
            self._min_freq = 10000
            self._dev_name = "sark110 (10k to 230M)"
        elif (self._fw_protocol & 0xff00) == 0x0300:
            self._max_freq = 230000000
            self._min_freq = 10000
            self._dev_name = "sark110 mk1"
        elif (self._fw_protocol & 0xff00) == 0x0a00:
            self._max_freq = 1000000000
            self._min_freq = 100000
            self._dev_name = "sark110 ulm"
        else:
            self._max_freq = 230000000
            self._min_freq = 100000
            self._dev_name = "sark110"

        # Converts version to str
        for i in range(15):
            if ver[i] == 0:
                break
            elif ver[i] == 46:
                self._fw_version += "."
            else:
                self._fw_version += "%c" % (ver[i])
        return 1

    # ---------------------------------------------------------
    # half float decompress
    def _half2float(self, byte1, byte2):
        hfs = (byte2 << 8) & 0xFF00
        hfs += byte1 & 0xFF
        temp = self.__half2float(hfs)
        res_pack = struct.pack('I', temp)
        return struct.unpack('f', res_pack)[0]

    def __half2float(self, float16):
        s = int((float16 >> 15) & 0x00000001)  # sign
        e = int((float16 >> 10) & 0x0000001f)  # exponent
        f = int(float16 & 0x000003ff)  # fraction

        if e == 0:
            if f == 0:
                return int(s << 31)
            else:
                while not (f & 0x00000400):
                    f = f << 1
                    e -= 1
                e += 1
                f &= ~0x00000400
            # print(s,e,f)
        elif e == 31:
            if f == 0:
                return int((s << 31) | 0x7f800000)
            else:
                return int((s << 31) | 0x7f800000 | (f << 13))

        e = e + (127 - 15)
        f = f << 13
        return int((s << 31) | (e << 23) | f)

    # ---------------------------------------------------------
    def _short2bytes(self, n):
        """
        short to buffer array
        :param n:
        :return:
        """
        b = bytearray([0, 0])
        b[0] = n & 0xFF
        n >>= 8
        b[1] = n & 0xFF
        return b

    def _int2bytes(self, n):
        """
        int to buffer array
        :param n:
        :return:
        """
        b = bytearray([0, 0, 0, 0])
        b[0] = n & 0xFF
        n >>= 8
        b[1] = n & 0xFF
        n >>= 8
        b[2] = n & 0xFF
        n >>= 8
        b[3] = n & 0xFF
        return b

    # ---------------------------------------------------------
    def _send_rcv(self, snd):
        # Windows: pywinusb
        if os.name == 'nt':
            try:
                report = self._handler.find_output_reports()[0]
                self.event.clear()
                report.set_raw_data(snd)
                report.send()
                self.event.wait()
                return _g_rcv[1:18]
            except:
                return [0] * 18
        # Linux: hidapi
        else:
            try:
                self._handler.write(snd)
                return self._handler.read(18, WAIT_HID_DATA_MS)
            except:
                return [0] * 18

    def _rx_handler(self, data):
        """
        Handler called when a report is received
        :param data:
        :return:
        """
        global _g_rcv
        _g_rcv = data.copy()
        self.event.set()

    # ---------------------------------------------------------
    _g_rcv = [0xff] * 19
    if os.name == 'nt':
        event = threading.Event()
