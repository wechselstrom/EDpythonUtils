#!/usr/bin/env python3

# Author: Stefan Weber
# CopyPolicy: Released under the terms of the LGPLv2.1 or later, see LGPL.TXT

import yarp
import numpy as np
import vBuffer

yarp.Network.init()

timestep = 1000
bottleBuffer = vBuffer.VBottleBuffer(timestep=timestep, portname="/eps_counter:i")
with bottleBuffer as buf:
    po = yarp.BufferedPortBottle()
    po.open("/eps_counter:o")

    while True:
        data = bottleBuffer.timeFrameQueue.get()
        bout = po.prepare()
        bout.clear()
        eps = 1e6 * data.shape[0] / timestep
        bout.addDouble(eps)
        print('writing %.4E' % eps)
        po.write()

