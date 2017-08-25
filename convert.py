#!/usr/bin/env python3
import numpy as np
import re
import sys
import gzip

pattern = re.compile('([0-9]+)\s([0-9]+\.[0-9]+)\sAE\s\((.*)\)\s')

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

def main(argv):
    if len(argv) != 2:
        sys.exit('need exactly one argument!')
    filename = argv[1]
    k = []
    with open(filename,'r') as f:
        for bottle in f:
            found = pattern.match(bottle)
            number, timestamp,  raw_data = found.groups()
            number = int(number)
            timestamp = float(timestamp)
            decoded = decode(raw_data)
            k.append(decoded)
    np.save(gzip.open('out.npy.gz', 'wb', 5), np.concatenate(k))

if __name__ == '__main__':
    main(sys.argv)
