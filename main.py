from src.NanoVNASaverHeadless import NanoVNASaverHeadless


############### TODO: Implement high level script for newbies. #######################

CALIBRATION_FILE = (
    "./test_cali.s2p"  # "Calibration_file_2024-04-12 12:23:02.604314.s2p"
)

vna = NanoVNASaverHeadless(vna_index=0, verbose=False)
vna.calibrate(None, CALIBRATION_FILE)
vna.set_sweep(2.9e9, 3.1e9, 1, 101)

old = None
# for i in range(100):
new = vna.stream_data()
if new != old:
    for data in new:
        # print(data)
        print("---------------------------------------------------------------")


vna.kill()
