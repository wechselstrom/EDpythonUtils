#!/usr/bin/env python3

# Author: Stefan Weber
# CopyPolicy: Released under the terms of the LGPLv2.1 or later, see LGPL.TXT

### !!!!!! Note !!!!!!!
### this example server allows receiving vBottles without python bindings.
### for speed and cleanliness reasons, you are well advised however to use the python bindings

import yarp
import numpy as np
import numba
from numba import jit
import event_driven

@jit
def process(arr):
    print('received')
    for i in range(arr.shape[0]):
        if arr[i,3] >20:
            arr[i,3] -= 20
        if arr[i,3] <100:
            arr[i,3] += 50
    return arr


def decode(str_rep):
    k = list(map(int, str_rep.split()))
    data = np.array(k, dtype=np.uint32)
    data = data.reshape((-1,2))
    timestamps = data[:,0] & ~(0x1<<31)
    polarity=data[:,1]&0x01

    data[:,1]>>=1;
    x=data[:,1]&0x1FF;

    data[:,1]>>=9;
    y=data[:,1]&0xFF;

    data[:,1]>>=10;
    channel=data[:,1]&0x01;
    return np.vstack([timestamps, channel, x, y, polarity]).T

def encode(datamatrix):
    timestamps, channel, x, y, polarity = datamatrix.T
    cxyp = np.uint32(((channel&0x01)<<20)|((y&0x0FF)<<10)|((x&0x1FF)<<1)|(polarity&0x01));
    cxyp |= (0x1<<26)
    timestamps |= (0x1<<31)
    vals = np.int32(np.stack([timestamps, cxyp]).T.flatten())
    str_rep = ' '.join([str(x) for x in vals])
    return str_rep


po = yarp.BufferedPortBottle()

class DataProcessor(yarp.PortReader):

    def read(self,connection):
        print('entered read')
        if not(connection.isValid()):
            print("Connection shutting down")
            return False
        #binp = yarp.Bottle()
        binp = yarp.Bottle()
        bout = po.prepare()
        bout.clear()
        ok = binp.read(connection)
        if not(ok):
            print("Failed to read input")
            return False
        #data = event_driven.getData(binp)
        data = decode(binp.pop().toString())
        print(data[0][0])
        processed = process(data)
        str_rep_new = encode(processed)
        v = yarp.Value()
        v.fromString('(%s)'%str_rep_new)
        bout.addString('AE')
        bout.add(v)
        po.write()
        return True

if __name__ == '__main__':
    yarp.Network.init()
    pi = yarp.Port()
    po.open("/python_out1");
    r = DataProcessor()
    pi.setReader(r)
    pi.open("/python_in1");
    
    yarp.Time.delay(1000000)
    print("Test program timer finished")
    
    yarp.Network.fini();
