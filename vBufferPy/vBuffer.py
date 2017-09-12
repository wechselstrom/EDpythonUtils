#!/usr/bin/env python3

# Author: Stefan Weber
# CopyPolicy: Released under the terms of the LGPLv2.1 or later, see LGPL.TXT

import yarp
import numpy as np
import event_driven
import queue
import sys
import time
import multiprocessing


class VBottleBuffer():
    def __init__(self, timestep=1000, limit=1<<24, portname='/vBuffer:i'):
        self.bottleQueue = multiprocessing.Queue()
        self.timeFrameQueue = multiprocessing.Queue()
        self.killswitch = multiprocessing.Event()
        self._p1 = _ReceiverProcess(self.bottleQueue, self.killswitch, portname)
        self._p2 = _BufferProcess(self.bottleQueue, self.timeFrameQueue,
                                  self.killswitch, timestep, limit)
    def __enter__(self):
        self._p1.start()
        self._p2.start()
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.killswitch.set()
        self._p1.join()
        self._p2.join()


class _BufferProcess(multiprocessing.Process):
    def __init__(self, q_in, out_q, killswitch, timestep, limit):
        super().__init__()
        self.buf = Buffer(timestep, limit)
        self.killswitch = killswitch
        self.q_in = q_in
        self.out_q = out_q


    def run(self):
        i=0
        while not self.killswitch.is_set():
            i+=1
            inp = self.q_in.get()
            outp = self.buf.add_data(inp)
            for x in outp:
                self.out_q.put(x)
            #if not i%1000:
            #    print('q_in:%d, out_q:%d, num:%d' %(self.q_in.qsize(),
            #                                self.out_q.qsize(),
            #                                       len(outp)))

class _ReceiverProcess(multiprocessing.Process):
    def __init__(self, out_q, killswitch, portname):
        super().__init__()

        self.out_q = out_q
        self.decode_q = queue.Queue()
        self.rec = Receiver(q=self.decode_q)
        self.killswitch = killswitch
        self.portname = portname


    def run(self):
        i=0
        input_port = yarp.BufferedPortBottle()
        input_port.open(self.portname);
        input_port.useCallback(self.rec)
        while not self.killswitch.is_set():
            b = self.decode_q.get()
            binp = event_driven.bottleToVBottle(b)
            data = event_driven.getData(binp)
            self.out_q.put(data)
            i+=1
            #if not i%10:
            #    print('decode_q:%d, out_q:%d' %(self.decode_q.qsize(),
            #                                        self.out_q.qsize()))


class Receiver(yarp.BottleCallback):

    def __init__(self, q=queue.Queue()):
        super().__init__()
        self.q = q
        self.last = 0

    
    def onRead(self, *args):
        b = yarp.Bottle(args[0])
        self.q.put(b)
        return


class Buffer():
    def __init__(self, timestep, limit=1<<24):
        self.storage = []
        self.current=None
        self.timestep = timestep
        self.s = None
        self.limit = limit
        self.zeroarray = np.zeros((0,5),dtype=np.uint32)


    def add_data(self, new_data):
        """
        add_data is called when new data should be inserted. The data is then
        stored and if a timestep has passed, according to the internal
        timestamps, all events within this timestep will be concatenated into one
        numpy array. All completed time windows, given the stored and new data,
        are then returned.
        Note:If no events occur within a timestep, an empty array will be
        returned.
        """

        ## Sometimes we get malformed data, if event rate is really high.
        ## So we don't process these bottles when they match the heuristic.
        if abs(np.int64(new_data[-1,1]) - np.int64(new_data[0,1])) > 1e5:
            if new_data[-1,1] > 1e5:
                print('dropped corrupted:')
                return []

        ## We first generate a splitted version containing all the different
        ## timewindows which we find in the events
        out = []
        classes = np.uint16(new_data[:,1]//self.timestep)
        splitted = split(new_data, classes)
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
        if out == []:
            return out
        ## and finally we insert empty time windows if there were no events
        ## in the window
        if self.s is None:
            self.s = out[0][0,1]//self.timestep
        e = out[-1][0,1]//self.timestep
        if self.s<=e:
            tws = np.arange(self.s, e+1)
        else:
            tws = np.concatenate([
                np.arange(self.s,self.limit//self.timestep+1),
                np.arange(e+1)
                ])
        mapping = {a:b for a, b in zip(tws,np.arange(len(tws)))}
        li = [x for x in range(len(tws))]
        try:
            for x in out:
                li[mapping[x[0,1]//self.timestep]] = x
        ## if our heuristic did not work... well we reset since there is not
        ## much else we can do 
        except KeyError:
            self.storage = []
            self.s = None
            return []

        indices = np.where([type(x)==int for x in li])[0]
        for i in indices: li[i] = self.zeroarray
        self.s = out[-1][0,1]//self.timestep + 1
        return li

    

def split(sequence, classes):
    #change_indices = np.where(np.concatenate([[0], np.diff(classes)]))[0]
    change_indices = np.where(np.diff(classes))[0]+1
    out = np.split(sequence, change_indices)
    return out

if __name__ == '__main__':
    timestep = 1000
    if len(sys.argv) > 1:
        timestep = int(sys.argv[1])
    yarp.Network.init()
    bottleBuffer = VBottleBuffer(timestep=timestep, portname="/buffer:i")
    with bottleBuffer as buf:
        i=0
        while True:
            data = bottleBuffer.timeFrameQueue.get()
            if data.shape[0]==0:
                print(';', end='')
            else:
                print('.', end='')
                #assert((data[0,1]%(1<<24)) == data[0,1]), 'test: %d %d' %\
                #((data[0,1]%(1<<24)), data[0,1])
            i+=1
            if not i%100:
                print('')
    yarp.Network.fini()
