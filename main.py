from src.NanoVNASaverHeadless import NanoVNASaverHeadless


############### TODO: Implement high level script for newbies. #######################
vna = NanoVNASaverHeadless(vna_index=0, verbose=True)
vna.set_sweep(2.9e9, 3.1e9)
vna.stream_data()
# vna.calibrate()
vna.kill()
