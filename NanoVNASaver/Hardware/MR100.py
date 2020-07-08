#  NanoVNASaver
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019.  Rune B. Broberg
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
import logging
from typing import List
import numpy as np
from NanoVNASaver.Hardware.VNA import VNA, Version
import time
import socket
import sys
from NanoVNASaver.Hardware.Serial import drain_serial
from time import sleep

logger = logging.getLogger(__name__)


class Mr100(VNA):
    '''
    Generalizzazione per raccogliere misure
    in futuro potrei prendere altro strumento,
    ma voler analizzare i dati

    TODO: creare "interfaccia"
    '''
    name = "MR100"
    prompt = ">>"
    valid_datapoints = (101,)

    def __init__(self,  iface, addr="00:15:83:35:63:A1", port=1, raw=False):
        super().__init__(iface)
        self.port = port
        self.addr = addr
        self.s = None
        self.raw = raw
        self.setSweep(3000000, 30000000)

    @classmethod
    def misura_test(cls, len_buffer=50):
        '''
        per vedere se cambiando metodo si velocizza, ma
        a me sembrano sempre 19s, secondo più secondo meno
        NB nel secondo caso mancano 3s circa della connessione
        quindi i tempi sono praticamente uguali
        :param cls:
        :param len_buffer:
        '''
        start = time.time()
        a = cls()
        res = a.test_bt_command(
            "scan 3000000 6000000 25000", len_buffer=len_buffer)
        end = time.time()
        print((end - start))
        time.sleep(2)
        start = time.time()
        res = list(a.scan_bt(3000000, 6000000, 25000))
        end = time.time()
        print((end - start))
        return res

    def test_bt_command(self, cmd, len_buffer=50):

        logger.info("connetto")
        s = socket.socket(socket.AF_BLUETOOTH,
                          socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        s.connect((self.addr, self.port))
        logger.info("connesso e lancio comando %s", cmd)

        s.send(bytes("%s\r" % cmd, 'UTF-8'))
        s.timeout = 2
        res = []
        out = ""
        while True:
            out += s.recv(len_buffer).decode()
            # print(out)
            l = out.split("\r")
            if l[-1].endswith("\n"):
                logger.debug("termina corretto")
                res.extend((r.strip() for r in l))
            else:
                # ultima riga non terminata
                out = l[-1]
                logger.debug("nuovo out")
                res.extend((r.strip() for r in l[:-1]))
            if ">>" in out:
                # res.append(out)
                break

        s.close()
        return res

    def aggiorna_df(self, start, stop, step, df=None, colonne=None, z0=50):
        '''
        PRovo a fare funzione che :
         - inizializza DataFrame con frequenza e dati

         - alla prima iterazione ritorna DF "vuoto"

         - alle successive lo aggiorna e ritorna solo riga aggiornata.

         NB
         Mi aspetto che un eventuale refresh del plot del df venga aggiornato.

        :param start:
        :param stop:
        :param step:
        :param z0:
        '''

        if df is None:
            df, colonne = self.new_df(start, stop, step)
        else:
            if colonne is None:
                raise ValueError("Se indichi df devi mettere anche colonne")

        for res in self.leggi_dati_bt(start, stop, step):
            for c in colonne:
                df.at[res["freq"], c] = res[c]
            # print res
            yield res

    def leggi_dati_bt(self, start, stop, step):
        logger.debug("Leggo raw %s", self.raw)
        for progressivo, data in enumerate(self.scan_bt(start, stop, step)):
            # print "iprogressivo ed r", progressivo, r
            if self.raw:
                res = self.calcola(*[float(i) for i in data], z0=50)
            else:
                vswr, r, x, z = [float(i) for i in data]
                cr = (vswr - 1) / (vswr + 1)
                rl = -20 * np.log10(cr)
                res = {"rl": rl,
                       "vswr": vswr,
                       "z": z,
                       "r": r,
                       "x": x,
                       "phi": None,
                       "vf": None,
                       "vr": None,
                       "vz": None,
                       "va": None,
                       "z0": 50,
                       "cr": cr,
                       # "roe2": vswr,
                       }
            res["freq"] = start + step * progressivo
            # print res
            yield res

    def connect(self):

        if self.s is None:
            s = socket.socket(socket.AF_BLUETOOTH,
                              socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)

            try:
                s.connect((self.addr, self.port))
            except OSError as e:
                logger.exception(e)
                logger.error("Verifica Connessione BlueTooth")
                sys.exit(1)

            self.s = s
        return self.s

    def close(self):
        if self.s:
            self.s.close()
            self.s = None

    def _flush(self):
        s = self.connect()
        s.settimeout(.5)
        ok = False
        out = ''
        prev = '101001011'
        while True:
            try:
                out += s.recv(1).decode()
            except Exception as e:
                if "%s" % e == "timed out":
                    return
                else:
                    logger.info("e '%s' %s", e, e.__dict__)
                    raise e

    def scan_bt(self, start, stop, step):

        s = self.connect()
        if self.raw:
            cmd = "scanr"
        else:
            cmd = "scan"
        s.send(bytes("%s %s %s %s \r" % (cmd, start, stop, step), "UTF-8"))
        ok = False
        out = ''
        prev = '101001011'
        while True:
            # promemoria, anche con bufer >1 la velocità non cambia
            # quindi un carattere alla volta è più semplice da controllare
            # TODO: vedere se python ha metodo "più elegante"
            out += s.recv(1).decode()
            # print(out)
            if out.endswith("\r\n"):
                if not ok:
                    ok = True
                    # primo a capo, lo salto
                else:
                    res = out[:-2]
                    if res == "Start":
                        logger.info("Comando accettato")
                    elif res == "End":
                        logger.info("comando terminato")
                        # s.close()
                        return
                    elif res in [">>", ""]:
                        logger.debug("ignoro %s", res)
                    else:
                        yield res.split(",")

                out = ""

            if prev == out:
                s.close()
                return
            prev = out

    # MIXIN:

    def setSweep(self, start, stop):

        FMIN = 1000000
        FMAX = 50000000
        if start < FMIN or start > FMAX or stop < FMIN or start > FMAX:
            raise ValueError("MR100 only 1-50 MHz")
        self.start = start
        self.stop = stop
        self.step = round((stop - start) / (self.datapoints - 1))

    def readFrequencies(self) -> List[int]:
        frequencies = [f for f in range(self.start, self.stop, self.step)]
        frequencies.append(self.stop)
        return frequencies

    def readValues11(self) -> List[str]:
        logger.debug("reading s11")
        Z0 = 50 + 0j
        values = []
        if self.raw:
            cmd = "scanr"
        else:
            cmd = "scan"
        full_cmd = "%s %s %s %s \r" % (
            cmd, self.start, self.stop + self.step, self.step)
        logger.debug("using command: %s", full_cmd)

        for swr, r, x, z in self._readValues(full_cmd):
            Z = complex("%s+%sj" % (r, x))
            S11 = (Z - Z0) / (Z + Z0)
            values.append("%s %s" % (S11.real, S11.imag))
        return values

    def readValues21(self) -> List[str]:
        logger.error("Only S11 from MR100")
        return ["1 0"] * 101

    def readBtValues(self, data):

        if data == "frequencies":
            return ["%s" % f for f in range(self.start, self.stop, self.step)]
        elif data == "data 0":
            Z0 = 50 + 0j
            values = []
            for swr, r, x, z in self.scan_bt(self.start, self.stop, self.step):
                Z = complex("%s+%sj" % (r, x))
                S11 = (Z - Z0) / (Z + Z0)
                values.append("%s %s" % (S11.real, S11.imag))
            return values

        elif data == "data 1":
            logger.error("Only S11 from MR100")
            return ["1 1"] * 101

    def readFirmware(self):
        return "not implemented"

    def readValues(self, value) -> List[str]:

        if value == "data 0":
            return self.readValues11()
        elif value == "data 1":
            return self.readValues21()

    def _readValues(self, value, pre="Start", post="End") -> List[str]:
        logger.debug("VNA reading %s", value)
        values = []

        with self.serial.lock:
            drain_serial(self.serial)
            self.serial.write(f"{value}\r".encode('ascii'))
            data = "a"
            sleep(0.05)
            while data != self.prompt:
                logger.debug("leggo")
                data = self.serial.readline().decode('ascii').strip("\r\n")
                logger.debug("letto '%s'", data)
                if pre:
                    if data == pre:
                        logger.debug("read %s, next line is data")
                        pre = None
                    else:
                        logger.warning("waiting %s skipping %s", pre, data)
                    continue
                if post and data == post:
                    logger.debug("read %s, end of data")
                    break
                if data not in ["", self.prompt]:
                    values.append(data.split(","))
            # values = result.split("\r\n")

        logger.debug(
            "VNA done reading %s (%d values)",
            value, len(values))
        logger.debug(values)
        return values[:self.datapoints]

    def readVersion(self) -> 'Version':
        logger.debug("dummy version")
        return Version("v13")

    def read_features(self):
        pass
