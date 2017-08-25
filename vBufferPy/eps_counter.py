#!/usr/bin/env python3

# Author: Stefan Weber
# CopyPolicy: Released under the terms of the LGPLv2.1 or later, see LGPL.TXT

import yarp
import numpy as np
import vBuffer

yarp.Network.init()

bottleBuffer = vBuffer.VBottleBuffer(100000, "/eps_counter:i")
with bottleBuffer as buf:
    po = yarp.BufferedPortBottle()
    po.open("/eps_counter:o")

    while True:
        data = bottleBuffer.timeFrameQueue.get()
        bout = po.prepare()
        bout.clear()
        val = int(data.shape[0])
        bout.addInt(val)
        print('writing %s' % val)
        po.write()

