#!/usr/bin/env python

"MCMC functions for tree importance/decay sampling"

from __future__ import print_function

import os
import pickle

import toytree
import numpy as np
from numba import njit


class MCMC:
    def __init__(self, name, workdir="analysis-strange", ipyclient=None):

        # load args
        self.name = name
        self.workdir = workdir
        self.ipyclient = ipyclient

        # load the mb results from Window analysis
        self.arr = np.load(os.path.join(self.workdir, self.name + ".mb.npy"))

        # load the tree dictionary for mapping indices to newick {0: tree1, ..}
        phandle = os.path.join(self.workdir, self.name + ".mb.p")
        with open(phandle, 'rb') as pin:
            self.treedict = pickle.load(pin)

        # the species tree as toytree, should have theta and Ne as features?
        self.sptree = toytree.tree(
            os.path.join(self.workdir, self.name + ".newick"))

        # the likelihood of each topology given species tree {0: 0.001, 1: 0..}
        # if we can jit the whole mcmc chain then this could be a lookup array
        # instead of a dict...
        self.treeliks = {i: 0 for i in self.treedict}
        self.get_gtree_likelihoods()


    def run(self):
        # start chain 
        while 1:

            # propose a move
            newarr = jsample(self.arr)

            # calculate score: get modes, turn into trees, get liks product
            mdarr = jmodes(newarr)
            score = np.prod([self.treeliks[i] for i in mdarr])

            # calculate whether to accept new move
            

            # write to disk


            # 


    def get_gtree_likelihoods(self):
        pass




# @jit
# def rmse(predictions, targets):
#     return np.sqrt(((predictions - targets) ** 2).mean())




# class MBmcmc:
#     def __init__(self,
#         name,
#         workdir):
#         self.name = name
#         self.workdir = workdir

#         self.mbcsv = np.array(pd.read_csv(os.path.join(self.workdir, 
#             name + "_mb_mstrees_mcmc.csv")
#             ,index_col=0))
#         self.topokey = pd.read_csv(os.path.join(self.workdir, 
#             name + "_mb_mstrees_topokey.csv"),
#             index_col=0)

#         self.topoprobs = np.array(self.topokey['probs'])

#     def update_x_times(self,
#                        mixnum,
#                        num_times,
#                        sd_normal):
#         for i in range(num_times):
#             replace(self.mbcsv,
#                     mixnum,
#                     sd_normal)

#     def score(self):
#         counted = Counter(mode(self.mbcsv)[0])
#         expected = self.topoprobs[np.array(counted.keys())]
#         observed = np.array(counted.values()).astype(float)/len(counted.values())
#         return(rmse(expected,observed))



# # from: https://stackoverflow.com/questions/16330831/most-efficient-way-to-find-mode-in-numpy-array
# def mode(ndarray, axis=0):
#     # Check inputs
#     ndarray = np.asarray(ndarray)
#     ndim = ndarray.ndim
#     if ndarray.size == 1:
#         return (ndarray[0], 1)
#     elif ndarray.size == 0:
#         raise Exception('Cannot compute mode on empty array')
#     try:
#         axis = range(ndarray.ndim)[axis]
#     except:
#         raise Exception('Axis "{}" incompatible with the {}-dimension array'.format(axis, ndim))

#     # If array is 1-D and numpy version is > 1.9 numpy.unique will suffice
#     if all([ndim == 1,
#             int(np.__version__.split('.')[0]) >= 1,
#             int(np.__version__.split('.')[1]) >= 9]):
#         modals, counts = numpy.unique(ndarray, return_counts=True)
#         index = np.argmax(counts)
#         return modals[index], counts[index]

#     # Sort array
#     sort = np.sort(ndarray, axis=axis)
#     # Create array to transpose along the axis and get padding shape
#     transpose = np.roll(np.arange(ndim)[::-1], axis)
#     shape = list(sort.shape)
#     shape[axis] = 1
#     # Create a boolean array along strides of unique values
#     strides = np.concatenate([np.zeros(shape=shape, dtype='bool'),
#                                  np.diff(sort, axis=axis) == 0,
#                                  np.zeros(shape=shape, dtype='bool')],
#                                 axis=axis).transpose(transpose).ravel()
#     # Count the stride lengths
#     counts = np.cumsum(strides)
#     counts[~strides] = np.concatenate([[0], np.diff(counts[~strides])])
#     counts[strides] = 0
#     # Get shape of padded counts and slice to return to the original shape
#     shape = np.array(sort.shape)
#     shape[axis] += 1
#     shape = shape[transpose]
#     slices = [slice(None)] * ndim
#     slices[axis] = slice(1, None)
#     # Reshape and compute final counts
#     counts = counts.reshape(shape).transpose(transpose)[tuple(slices)] + 1

#     # Find maximum counts and return modals/counts
#     slices = [slice(None, i) for i in sort.shape]
#     del slices[axis]
#     index = np.ogrid[slices]
#     index.insert(axis, np.argmax(counts, axis=axis))
#     return sort[tuple(index)], counts[tuple(index)]


# class MB_posts_csv:
#     def __init__(self,
#         posterior_path):
#         self.mbcsv = pd.read_csv(posterior_path,index_col=0)

#     def update_full(self,
#                 df,
#                 prop = .8,
#                 num_resamp = 300,
#                 scale = 1):
#         tot_list = []
#         num_focal = np.int(np.round(num_resamp*prop))
#         num_non = num_resamp - num_focal
#         nummbtrees = np.max(df['idx'])
#     #    newfile=h5py.File('../tests/test.hdf5')
#         for idx in range(nummbtrees):
#             samp_idx = np.int(np.round(np.random.normal(idx,scale)))
#             if samp_idx < 0 or samp_idx >= nummbtrees:
#                 samp_idx = idx + (samp_idx-idx)*-1

#             newdraw = np.hstack([make_draw(df,idx,num_focal),make_draw(df, samp_idx, num_non)])
#             counts = Counter(newdraw)
#     #        newfile[str(idx)] = np.array(zip(np.repeat(0,len(counts)),
#     #                                counts.keys(),
#     #                                np.array(counts.values()).astype(float)/np.sum(counts.values())))
#             tot_list.extend(zip(np.repeat(idx,len(counts)),
#                                 counts.keys(),
#                                 np.array(counts.values()).astype(float)/np.sum(counts.values())))
#     #    newfile.close()
#         return(pd.DataFrame(tot_list,columns=['idx','topo_idx','prob']))


# class MB_posts_hdf5:
#     # uses hdf5


#     def __init__(self,
#         posterior_path):
#         mbinfs = h5py.File(name=posterior_path)
#         self.posterior_list = [np.array(mbinfs[str(i)]) for i in range(len(mbinfs.keys())-1)]
#         mbinfs.close()

#     def resample_neighbors(self,
#         num_times,
#         prop,
#         resamp_num=300):
#         full_list = self.posterior_list
#         for i in range(num_times):
#             newfull_list = []
#             for curridx in range(len(full_list)):
#                 ps = full_list[curridx][1]
#                 resamp = np.random.choice(len(ps),p=ps.astype(float)/np.sum(ps.astype(float)),size=np.int(resamp_num*prop))
#                 newsamped = full_list[curridx][0][resamp]
#                 if curridx != 0 and curridx != (len(full_list)-1):
#                     leftright = np.array([curridx-1,curridx+1])
#                 elif curridx == 0:
#                     leftright = np.array([curridx+1])
#                 else:
#                     leftright = np.array([curridx-1])

#                 remaining = np.int(np.round((1-prop)*resamp_num))
#                 neighborsamps = []
#                 for neighbor in leftright:
#                     ps = full_list[neighbor][1]
#                     neighborsamps.extend(full_list[neighbor][0][np.random.choice(len(ps),p=ps.astype(float)/np.sum(ps.astype(float)),size=np.int(remaining/len(leftright)))])

#                 newsamped = np.hstack([newsamped,neighborsamps])
#                 countitem = Counter(newsamped)
#                 newfull_list.append([np.array(countitem.keys()),np.array(countitem.values()).astype(float)/np.sum(countitem.values())])
#             del full_list
#             full_list = deepcopy(newfull_list)
#         return(full_list)

#     def resample_index(self,full_list,orig_index,samp_index,prop,resamp_num=300):
#         '''
#         hand this a list (probably an adjusted copy of self.posterior list) to 
#         resample a particular index
#         '''
#         newfull_list = []
#         curridx = orig_index
#         ps = full_list[curridx][1]
#         resamp = np.random.choice(len(ps),p=ps.astype(float)/np.sum(ps.astype(float)),size=np.int(resamp_num*prop))
#         newsamped = full_list[curridx][0][resamp]

#         remaining = np.int(np.round((1-prop)*resamp_num))
#         neighborsamps = []
#         neighbor = samp_index
#         ps = full_list[neighbor][1]
#         neighborsamps.extend(full_list[neighbor][0][np.random.choice(len(ps),p=ps.astype(float)/np.sum(ps.astype(float)),size=np.int(remaining))])

#         newsamped = np.hstack([newsamped,neighborsamps])
#         countitem = Counter(newsamped)
#         newfull_list.append([np.array(countitem.keys()),np.array(countitem.values()).astype(float)/np.sum(countitem.values())])
#         return(newfull_list)


#     def resample_normal(self,
#                         num_times,
#                         scale,
#                         prop,
#                         resamp_num):
#         '''
#         This resamples across all mb posterior distributions a specific number of times. 
#         Sliding across all gene trees: For each tree, an integer is drawn from a normal distribution
#         with mean of 0 and a specified variance. The corresponding posterior distribution away from the
#         focal distribution is resampled from with a designated proportion.
        
#         full_list: list of all posterior distributions of gene trees.
#         num_times: number of times to resample all of the gene trees
#         scale: the variance of the normal distribution used to draw a nearby tree to sample from
#         prop: the proportion of resamples to be taken from the focal gene tree, as opposed to nearby trees
#         resamp_num: the number of total resample draws, later normalized to floats between 0 and 1.
#         '''
#         full_list = self.posterior_list
#         for _ in range(num_times):
#             new_list = []
#             listlen = len(full_list)
#             for idx in range(listlen):
#                 newidx = self.get_samp_index(idx,scale)
#                 if newidx < 0 or newidx >= listlen:
#                     newidx = idx + (newidx - idx)*(-1)
#                 new_list.append(
#                     self.resample_index(full_list,
#                            orig_index=idx,
#                            samp_index=newidx,
#                            prop = prop,
#                            resamp_num=resamp_num)[0]
#                 )
#             full_list = deepcopy(new_list)
#         return(full_list)

#     def get_samp_index(self,starting_idx, scale):
#         return(np.int(starting_idx + np.round(np.random.normal(loc=0,scale=scale))))


# @jit
# def make_draw(self,df,idx,size):
#     topos = df['topo_idx'][df['idx'] == idx]
#     probs = df['prob'][df['idx'] == idx]
#     probs = probs / np.sum(probs)
#     return(np.random.choice(topos,p=probs,replace=True,size = size))



def modes_multi(arr, treedict, topn=4):
    "deprecated... return MJ consensus of top N trees in each column"

    # empty array of -1s
    modes = np.zeros((topn, arr.shape[1]), dtype=np.uint32)
    modes.fill(-1)

    # fill with topn trees, if only <n tress in dist then -1 remains
    for i in range(arr.shape[1]):
        tops = np.unique(arr[:, i], return_counts=True)[1][:topn]
        modes[:tops.size, i] = tops

    # replace tree indices with the actual trees
    txs = [[treedict.get(i) for i in modes[:, i]] for i in range(arr.shape[1])]

    # get consensus trees
    constres = [
        toytree.mtree(i).get_consensus_tree().write(fmt=9) for i in txs
    ]

    # turn consensus trees back into indices (could make a new tree! ugh...)
    return modes   


@njit
def jmodes(arr):
    "return top 1 tree in each column, muchhh faster than modes_multi()"
    modes = np.zeros(arr.shape[1], dtype=np.uint32)
    for i in range(arr.shape[1]):
        modes[i] = int(np.bincount(arr[:, i]).argmax())
    return modes


@njit
def jsample(arr, nsamp=5, decay=2):
    "Resample nsamp indices in 2-d array using distance decay."
    # get up/down position of cells to replace for each col
    sampy1 = np.zeros((nsamp, arr.shape[1]), dtype=np.uint32)
    for idx in range(arr.shape[1]):
        sampy1[:, idx] = np.random.choice(arr.shape[0], nsamp, replace=False)

    # get up/down position of cells to fill replacements   
    sampy2 = np.zeros((nsamp, arr.shape[1]), dtype=np.uint32)
    for idx in range(arr.shape[1]):
        sampy2[:, idx] = np.random.choice(arr.shape[0], nsamp, replace=False)
    
    # get how far left or right to draw new sample from at each cell
    xdiff = np.random.normal(0, 2, size=(nsamp, arr.shape[1])).astype(np.int8)

    # turn those samples into x indices
    sampx = np.zeros((nsamp, arr.shape[1]), dtype=np.int32)
    for idx in range(nsamp):
        sampx[idx] = np.arange(arr.shape[1]) + xdiff[idx]
    
    # do not allow wrapping around ends
    for row in range(sampx.shape[0]):
        for col in range(sampx.shape[1]):
            if sampx[row, col] < 0:
                sampx[row, col] = 0
            if sampx[row, col] > arr.shape[1] - 1:
                sampx[row, col] = arr.shape[1] - 1

    # replace sampled values with new sampled values
    for row in range(sampx.shape[0]):
        for col in range(sampx.shape[1]):
            xer = (sampx[row, col])
            y1 = sampy1[row, col]
            y2 = sampy2[row, col]
            arr[y1, xer] = arr[y2, xer]
    return arr
