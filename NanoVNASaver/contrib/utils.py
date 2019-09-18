'''
Created on 27 lug 2019

@author: mauro
'''
from _tracemalloc import start, stop
import logging


try:
    from matplotlib.ticker import EngFormatter
except ImportError:
    def EngFormatter(*args, **kwargs):
        def myformatter(value):
            return value
        return myformatter

logger = logging.getLogger()

formatterF = EngFormatter(unit='Hz')
formatterC = EngFormatter(unit='F')
# formatterF = EngFormatter(unit='Hz')

BANDE_RADIOAMATORIALI = (
    (1830000, 1850000),      # 160m
    (3500000, 3800000),  # 80m
    (5331500, 5366500),  # 60m
    (7000000, 7200000),  # 40m
    (10100000, 10150000),  # 30m
    (14000000, 14350000),  # 20m
    (18068000, 18168000),  # 17m
    (21000000, 21450000),      # 15m
    (24890000, 24990000),    # 12m
    (25615000, 27855000),  # CB
    (28000000, 29700000),  # 10m
)


def identifica(start, stop, distanza=None):
    logger.debug("start %s stop %s distanza %s", start, stop, distanza)
    print("start %s stop %s distanza %s" % (start, stop, distanza))
    res = []
    for x1, x2 in BANDE_RADIOAMATORIALI:
        # print("cerco in", x1, x2)
        mark_low = mark_hi = None
        band_low = x1  # * 1000000
        band_hi = x2  # * 1000000
        logger.debug("confronto con banda %s - %s", band_low, band_hi)
        if start <= band_low <= stop:
            logger.debug("inizio banda è dentro intervallo")
            if distanza:
                logger.debug("siccome c'è distanza prendo la frequenza minima")
                mark_low = start
            else:
                mark_low = band_low
        elif band_low <= start <= band_hi:
            logger.debug("inizio intervallo è dentro banda")
            if distanza:
                logger.debug("siccome c'è distanza prendo la frequenza minima")
                mark_low = band_low
            else:
                mark_low = start

        else:
            logger.debug("non interseca banda amatoriale")
            if distanza:
                logger.debug("provo con tolleranza")
                new_start = start - distanza
                if band_low <= new_start <= band_hi:
                    logger.debug("includo banda in basso")
                    mark_low = band_low

        if band_low <= stop <= band_hi:
            logger.debug("fine banda è dentro intervallo")
            if distanza:
                logger.debug(
                    "siccome c'è distanza prendo la frequenza massima")
                mark_hi = band_hi
            else:
                mark_hi = stop
        elif start <= band_hi <= stop:
            if distanza:
                mark_hi = stop
            else:
                mark_hi = band_hi
        else:
            logger.debug("non interseca banda amatoriale")
            if distanza:
                logger.debug("provo con tolleranza")
                new_stop = stop + distanza
                if band_low <= new_stop <= band_hi:
                    logger.debug("includo banda in alto")
                    mark_hi = band_hi
                    if mark_low is None:
                        mark_low = start
        if mark_hi is None and distanza and mark_low:
            logger.debug(
                "siccome ho trovato limite inferiore ed ho tolleranza, metto limite superiore")
            mark_hi = stop

        logger.debug("Ritorno %s, %s", mark_low, mark_hi)
        if (mark_low is None and mark_hi) or (mark_hi is None and mark_low):
            raise ValueError("Non posso avere solo un valore None")
        if all((mark_low, mark_hi)):
            res.append((mark_low, mark_hi))

    return res
