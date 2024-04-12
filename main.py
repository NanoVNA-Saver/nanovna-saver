from src.NanoVNASaverHeadless import NanoVNASaverHeadless


############### TODO: Implement high level script for newbies. #######################
vna = NanoVNASaverHeadless(vna_index=0, verbose=True)
vna.calibrate(None, "Calibration_file_2024-04-12 12:23:02.604314.s2p")
vna.set_sweep(2.9e9, 3.1e9, 1, 101)
vna.stream_data()
vna.kill()
