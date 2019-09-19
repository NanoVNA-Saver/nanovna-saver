'''
Created on 27 lug 2019

@author: mauro
'''

import logging


logger = logging.getLogger()


BANDE_RADIOAMATORIALI = (
    (135700, 135800),  # 2200m
    (472000, 479000),  # 640m
    (1830000, 1850000),  # 160m
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
    (50000000, 54000000),  # 6m
    (70000000, 70500000),  # 4m
    (144000000, 146000000),  # 2m
    (430000000, 440000000),  # 70cm
    (1240000000, 1300000000),  # 23cm
)


def identifica(start, stop):
    logger.debug("start %s stop %s ", start, stop)
    res = []
    for x1, x2 in BANDE_RADIOAMATORIALI:
        # print("cerco in", x1, x2)
        mark_low = mark_hi = None
        band_low = x1  # * 1000000
        band_hi = x2  # * 1000000
        logger.debug("confronto con banda %s - %s", band_low, band_hi)
        if start <= band_low <= stop:
            logger.debug("inizio banda è dentro intervallo")

            mark_low = band_low
        elif band_low <= start <= band_hi:
            logger.debug("inizio intervallo è dentro banda")

            mark_low = start

        else:
            logger.debug("non interseca banda amatoriale")

        if band_low <= stop <= band_hi:
            logger.debug("fine banda è dentro intervallo")

            mark_hi = stop
        elif start <= band_hi <= stop:

            mark_hi = band_hi
        else:
            logger.debug("non interseca banda amatoriale")

        logger.debug("Ritorno %s, %s", mark_low, mark_hi)
        if (mark_low is None and mark_hi) or (mark_hi is None and mark_low):
            raise ValueError("Non posso avere solo un valore None")
        if all((mark_low, mark_hi)):
            res.append((mark_low, mark_hi))

    return res
