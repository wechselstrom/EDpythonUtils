import numpy as np
import vBuffer


#generate data
data = np.sort(np.random.randint(17000,10000000,(100357, 5)),axis=0)%1000000
splits = np.where(np.random.random(100357)>0.95)
test_data = np.split(data, splits[0])

#instantiate buffer
bufferTime = 1028
buf = vBuffer.Buffer(bufferTime)
#generate outputs
outs = []
for x in test_data:
    outs += buf.add_data(x)

assert(len(outs)>10), 'expecting more outputs, typically around thousand given this data'
couts = np.concatenate(outs)
ctest_data = np.concatenate(test_data)
assert(len(couts) + np.sum([len(x) for x in buf.storage]) == len(ctest_data)),\
        'number of events does not match'
assert((couts == ctest_data[:len(couts)]).all()), 'some events were changed'
assert np.all([x[0,1]-x[-1,1]<bufferTime for x in outs]), 'some outputs were longer than expected.'

assert np.all([(a==b).all() for a,b in zip(outs, np.split(couts,
     np.where(np.concatenate([[0],
                              np.diff(couts[:,1]//bufferTime)]))[0]))]),\
               'deviated from other implementation'
