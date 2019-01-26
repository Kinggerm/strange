#!/usr/bin/env python

from __future__ import print_function

import os
import re
import subprocess
import tempfile
import sys
from copy import deepcopy

import toytree
import numpy as np
import pandas as pd


# suppress the terrible h5 warning
import warnings
with warnings.catch_warnings(): 
    warnings.filterwarnings("ignore", category=FutureWarning)
    import h5py
    import msprime as ms


class Coalseq:
    """
    Simulate tree sequences on a input species tree and write to a workdir.
    """
    def __init__(
        self, 
        tree,
        name,
        workdir="analysis-strange",
        theta=0.01,
        length=10000,
        mutation_rate=1e-8,
        recombination_rate=1e-8,
        get_sequences=True,
        random_seed=None,
        ):
       
        # store param settings
        self.name = name
        self.workdir = os.path.realpath(os.path.expanduser(workdir))
        self.theta = theta
        self.mutation_rate = mutation_rate
        self.recombination_rate = recombination_rate
        self.length = length
        self.Ne = (self.theta / self.mutation_rate) / 4.
        self.tree = (
            tree if isinstance(tree, toytree.tree) else toytree.tree(tree)
        )
        self.ntips = self.tree.ntips
        self.random_seed = random_seed

        # find seq-gen binary
        strange_path = os.path.dirname(os.path.dirname(__file__))
        bins_path = os.path.join(strange_path, "bins")
        platform = ("linux" if "linux" in sys.platform else "macos")
        self.seqgen_binary = os.path.realpath(os.path.join(
            bins_path,
            'seq-gen-{}'.format(platform)
        ))

        # output attributes:
        self.treeseq = None
        self.tree_table = None
        self.clade_table = None
        self.database = os.path.join(self.workdir, self.name + ".hdf5")
        if not os.path.exists(self.workdir):
            os.makedirs(self.workdir)

        # clade search output attrs
        self.cladeslist = None
        self.cladesarr = None

        # fill treeseq, tree_table, and seqarr which is written to .hdf5
        self._simulate()
        self._get_tree_table()
        self._get_clade_table()
        if get_sequences:
            self._get_sequences()

        # write results to disk in workdir
        # first the tree with its original names
        self.tree.write(
            os.path.join(self.workdir, self.name + ".tree.newick"))

        # now with tip labels replaced
        nodedict = self.tree.get_node_dict()
        ivd = {v: k for k, v in nodedict.items()}
        tmptree = deepcopy(self.tree)
        copynodedict = tmptree.get_node_dict()
        tiplabs = tmptree.get_tip_labels()
        for leaf in tmptree.treenode.get_leaves():
            leaf.name = str(ivd[leaf.name]+1)
        tmptree.write(
            os.path.join(self.workdir, self.name + ".tree_ids.newick"))

        # now write topology:
        tmptree.write(
            os.path.join(self.workdir, self.name + ".topology.newick"),fmt=9)

        self.clade_table.to_csv(
            os.path.join(self.workdir, self.name + ".clade_table.csv"))
        self.tree_table.to_csv(
            os.path.join(self.workdir, self.name + ".tree_table.csv"))

        # save a key to get original tip labels back
        idlist = []
        for idx, label in enumerate(self.tree.get_tip_labels()):
            idlist.append([idx+1,label])
        pd.DataFrame(idlist).to_csv(os.path.join(self.workdir, self.name + ".tip_id.csv"))



    def _get_demography(self):
        "Define demographic events for msprime."
        ## Define demographic events for msprime
        demog = set()

        ## tag min index child for each node, since at the time the node is 
        ## called it may already be renamed by its child index b/c of 
        ## divergence events.
        for node in self.tree.treenode.traverse():
            if node.children:
                node._schild = min([i.idx for i in node.get_descendants()])
            else:
                node._schild = node.idx

        ## Add divergence events
        for node in self.tree.treenode.traverse():
            if node.children:
                dest = min([i._schild for i in node.children])
                source = max([i._schild for i in node.children])
                time = node.height * 2. * self.Ne  
                demog.add(ms.MassMigration(time, source, dest))

        ## sort events by time
        demog = sorted(list(demog), key=lambda x: x.time)
        return demog


    def _get_popconfig(self):
        "returns population_configurations for N tips of a tree"
        population_configurations = [
            ms.PopulationConfiguration(sample_size=1, initial_size=self.Ne)
            for ntip in range(self.ntips)]
        return population_configurations


    def _simulate(self):
        "Call msprime to generate tree sequence."
        migmat = np.zeros((self.ntips, self.ntips), dtype=int).tolist()    
        sim = ms.simulate(
            random_seed=self.random_seed,
            length=self.length,
            num_replicates=1,  
            mutation_rate=self.mutation_rate,
            recombination_rate=self.recombination_rate,
            migration_matrix=migmat,
            population_configurations=self._get_popconfig(),
            demographic_events=self._get_demography()
        )
        self.treeseq = next(sim)
   

    def _get_tree_table(self):
        "Parse msprime tree sequence into a dataframe"

        intervals = np.array(list(self.treeseq.breakpoints())).astype(int)       
        self.tree_table = pd.DataFrame({
            "start": intervals[:-1], 
            "end": intervals[1:],
            "length": intervals[1:] - intervals[:-1],
            "nsnps": 0,
            "treeheight": [
                int(tree.get_time(tree.get_root())) for tree 
                in self.treeseq.trees()], 
            "mstree": [tree.newick() for tree in self.treeseq.trees()], 
            # "treematch": [
            #     toytree.tree(tree.newick()).treenode.robinson_foulds(
            #         self.tree, topology_only=True)[0] == 0 
            #     for tree in self.treeseq.trees()], 
        })
        # drop intervals of length zero
        # (keeping these for now, sorting out later)
        # self.tree_table = self.tree_table[self.tree_table.length > 0]


    def _get_clade_table(self):
        """
        Build a df of whether each clade in the species tree is present in the
        genealogy of each interval.
        """
        # make a dictionary of all clades in the species tree
        clades = get_clades(self.tree)

        # make a dataframe for storing results      
        self.clade_table = pd.DataFrame({
            node.idx: np.zeros(self.tree_table.shape[0], dtype=int) 
            for node in self.tree.treenode.traverse("postorder") 
            if not node.is_leaf() and not node.is_root()
        })

        # fill clade table
        tarr = [
            get_clades(toytree.tree(self.tree_table.mstree[idx]))
            for idx in self.tree_table.index
        ]
        for node in self.tree.treenode.traverse():
            if not node.is_leaf() and not node.is_root():
                arr = np.array([clades[node.idx] in i.values() for i in tarr])
                self.clade_table[node.idx] = arr.astype(int)


    def _get_sequences(self):
        "Generate sequence data on genealogies, get nsnps, write to phylip."
        # init the supermatrix
        seqarr = np.zeros((self.ntips, self.tree_table.end.max()), dtype=bytes)

        # TODO: submit jobs to run asynchronously in parallel
        for idx in self.tree_table.index:
            if self.tree_table.length[idx]:
                arr, nsnps = self._call_seqgen_on_mstree(idx)

                # append tree to the tree table
                self.tree_table.loc[idx, 'nsnps'] = int(nsnps)

                # fill sequences into the supermatrix
                start = self.tree_table.start[idx]
                end = self.tree_table.end[idx]
                seqarr[:, start:end] = arr

        # format names for writing to phylip file:
        names = sorted(self.tree.get_tip_labels())
        longname = max([len(i) for i in names]) + 1
        printstr = "{:<" + str(longname) + "} "
        names = [printstr.format(i).encode() for i in names]

        # write sequence data as hdf5 array (todo: could chunk vertically)
        with h5py.File(self.database, 'w') as io5:
            # store name order (alphanumeric)
            io5.attrs["names"] = names

            # store sequence array
            io5["seqarr"] = seqarr
 

    def _call_seqgen_on_mstree(self, idx):
        """
        Generate sequence data for each fragment (interval + genealogy) and 
        a model of sequence substitution. Pass sequence to raxml to get mltree. 
        """
        # write tree to a file
        fname = os.path.join(tempfile.gettempdir(), str(os.getpid()) + ".tmp")
        with open(fname, 'w') as temp:
            temp.write(self.tree_table.mstree[idx])

        # write sequence data to a tempfile
        proc1 = subprocess.Popen([
            self.seqgen_binary, 
            "-m", "GTR", 
            "-l", str(self.tree_table.length[idx]), 
            "-s", str(self.mutation_rate),
            fname,
            # ... other model params...,
            ],
            stderr=subprocess.STDOUT, 
            stdout=subprocess.PIPE,
        )

        # check for errors
        out, _ = proc1.communicate()
        if proc1.returncode:
            raise Exception("seq-gen error: {}".format(out.decode()))

        # remove the "Time taken: 0.0000 seconds" bug in seq-gen
        physeq = re.sub(
            pattern=r"Time\s\w+:\s\d.\d+\s\w+\n", 
            repl="", 
            string=out.decode())

        # make seqs into array, sort it, and count differences
        physeq = physeq.strip().split("\n")[-(self.ntips + 1):]
        arr = np.array([list(i.split()[-1]) for i in physeq[1:]], dtype=bytes)
        order = np.argsort([i.split()[0] for i in physeq[1:]])
        sarr = arr[order, :]
        nsnps = np.invert(np.all(arr == arr[0], axis=0)).sum()
        return sarr, nsnps


    def get_clade_lengths_bp(self, cidx):
        lengths = []
        flen = 0
        for idx in self.clade_table.index:
            # extend fragment
            if self.clade_table.loc[idx, cidx] == 1 and idx in self.tree_table.index:
                flen += self.tree_table.loc[idx][1]
            # terminate fragment
            else:
                if flen:
                    lengths.append(flen)
                    flen = 0
        return np.array(lengths)


    def _get_cladeslist(self):
        cladeslist = []
        for mstree in self.tree_table.mstree:
            for i in get_clades(toytree.tree(mstree)).values():
                if i not in cladeslist:
                    cladeslist.append(i)
        sortedlist = np.array(cladeslist)[np.argsort([len(i) for i in cladeslist])]
        self.cladeslist = sortedlist


    def make_cladesarr(self):
        self._get_cladeslist()
        cladesarr = np.zeros((len(self.tree_table.mstree),len(self.cladeslist)),dtype=np.int8)
        for row in range(len(self.tree_table.mstree)):
            idxs= np.hstack([np.where(np.equal(i,
                              self.cladeslist)) for i in get_clades(toytree.tree(self.tree_table.mstree[row])).values()])[0]
            cladesarr[row,idxs] = 1
        self.cladesarr = cladesarr

    def query_clades(self,clades):
        '''
        clades is a list of sets of taxa. 

        For each row of cladesarr, we're interested in 
        whether all of our queried are present (i.e. "does this topology exist")

        returns an boolean array of len = number of mstrees where each index corresponds
        to whether that mstree contains all clades queried.
        '''
        all_clades_present = np.zeros((len(self.cladesarr)),dtype=np.bool)
        presentidxs = set(np.hstack([np.where(np.equal(i,self.cladeslist)) for i in clades])[0])
        for idx,i in enumerate(self.cladesarr):
            all_clades_present[idx] = presentidxs.issubset(set(np.where(i)[0]))
        return(all_clades_present)


def get_clades(ttree):
    "Used internally by _get_clade_table()"
    clades = {}
    for node in ttree.treenode.traverse():
        clade = set(i.name for i in node.get_leaves())
        if len(clade) > 1 and len(clade) < ttree.ntips:
            clades[node.idx] = clade
    return clades
