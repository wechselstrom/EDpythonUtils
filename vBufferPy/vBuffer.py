#!/usr/bin/env python3

# Author: Stefan Weber
# CopyPolicy: Released under the terms of the LGPLv2.1 or later, see LGPL.TXT

import yarp
import numpy as np
import event_driven
import queue
import sys


class VBottleBuffer(yarp.PortReader):

    def __init__(self, timestep, portname):
        super().__init__()
        self.storedEvents = Buffer(timestep)
        self.timeFrameQueue = queue.Queue()
        self.portname = portname

    def addEvents(self, data):
        out = self.storedEvents.add_data(data)
        #print(data[-1][1], data[0][1])
        for x in out:
            self.timeFrameQueue.put(x)

    def __enter__(self):
        self.pi = yarp.Port()
        self.pi.setReader(self)
        self.pi.open(self.portname);

    def __exit__(self, exc_type, exc_value, traceback):
        yarp.Network.fini();
    
    def read(self, connection):
        #print('entered read')
        if not(connection.isValid()):
            print("Connection shutting down")
            return False
        #binp = yarp.Bottle()
        binp = event_driven.vBottle()
        ok = binp.read(connection)
        if not(ok):
            print("Failed to read input")
            return False
        data = event_driven.getData(binp)
        self.addEvents(data)
        return True

class Buffer():
    def __init__(self, timestep):
        self.storage = []
        self.current=None
        self.timestep = timestep

    def add_data(self, x):
        """
        add_data is called when new data should be inserted. The data is then
        stored and if a timestep has passed, according to the internal
        timestamps, all events within this timestep will be concatenated into one
        numpy array. All completed time windows, given the stored and new data,
        are then returned.
        Note:If no events occur within a timestep, no empty array will be
        returned. Instead the timestep will just be silently ignored.
        """
        out = []
        classes = x[:,1]//self.timestep
        splitted = split(x, classes)
        if len(splitted)==1:
            if self.current == classes[0]:
                self.storage.append(splitted[0])
            else:
                if self.storage != []:
                    out.append(np.concatenate(self.storage))
                self.storage, self.current = [splitted[0]], classes[0]
        else:
            if self.storage != []:
                if self.current == classes[0]:
                    out.append(np.concatenate(self.storage + [splitted[0]]))
                    self.storage, self.current = [], None
                else:
                    out.append(np.concatenate(self.storage))
                    out.append(splitted[0])
                    self.storage, self.current = [], None
            else:
                out.append(splitted[0])
            out += splitted[1:-1]
            self.storage.append(splitted[-1])
            self.current = classes[-1]
        return out
        #if self.current is None:
        #    self.current = new_data[0,1]//self.timestep
        #last = new_data[-1,1]//self.timestep
        #print((self.current, last))
        #self.storage.append(new_data)
        #if self.current != last:
        #    out = np.concatenate([x[np.where((
        #             x[:,1]//self.timestep == self.current))] for x in
        #        self.storage])
        #    self.storage = self.storage[-1:]
        #    self.current = last
        #    return out

    

def split(sequence, classes):
    change_indices = np.where(np.concatenate([[0], np.diff(classes)]))[0]
    return np.split(sequence, change_indices)


if __name__ == '__main__':
    timestep = 10000
    if len(sys.argv) > 1:
        timestep = int(sys.argv[1])
    yarp.Network.init()
    bottleBuffer = VBottleBuffer(timestep, "/buffer:i")
    with bottleBuffer as buf:
        while True:
            data = bottleBuffer.timeFrameQueue.get()
            print(data.shape, data[-1][1],data[0][1])
