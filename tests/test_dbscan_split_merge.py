"""Tests for the DBSCAN clustering parameters and the choice of the continuing branch at splits and merges.

With DBSCAN the cluster size is a small count of points, so two branches of a split (or two parents of a merge) often
have the same size. Before, the branches of a split tied with the largest were neither the continuation (SPL) nor a
new split (NEW/SPL): they stayed NEW and lost their split. Now exactly one branch continues, the largest, with ties
broken by the largest overlap and then by the index, and every other branch is a new split.
"""
import operator

import numpy as np
import pandas as pd

from pyfortracc.default_parameters import default_parameters
from pyfortracc.features_extraction.clustering import clustering, dbscan_clustering
from pyfortracc.spatial_operations.spatial_class import merge, split


def overlays(rows):
    """Overlay table as overlay_ returns it (one row per pair current x previous cluster)."""
    return pd.DataFrame(rows, columns=['index_1', 'cluster_id_1', 'size_1', 'index_2', 'cluster_id_2', 'size_2',
                                       'overlap'])


def test_split_tie_in_size_broken_by_overlap():
    # previous cluster 0 splits into three current clusters; 10 and 11 have the same (largest) size
    op = overlays([[10, 1, 5, 0, 1, 12, 30.0],
                   [11, 2, 5, 0, 1, 12, 40.0],
                   [12, 3, 3, 0, 1, 12, 20.0]])
    spl, spl_prv, new_spl, new_spl_prv, coming = split(op)
    assert list(spl) == [11]                       # largest size, largest overlap
    assert sorted(new_spl) == [10, 12]             # the tied branch is a new split, not left out
    assert list(new_spl_prv) == [0, 0]
    assert list(coming) == [11, 11]                # new splits come from the continuing branch


def test_split_tie_in_size_and_overlap_broken_by_index():
    op = overlays([[21, 2, 4, 5, 9, 10, 25.0],
                   [20, 1, 4, 5, 9, 10, 25.0]])
    spl, _, new_spl, _, _ = split(op)
    assert list(spl) == [20]
    assert list(new_spl) == [21]


def test_split_largest_branch_continues():
    op = overlays([[30, 1, 3, 7, 4, 20, 90.0],
                   [31, 2, 9, 7, 4, 20, 10.0]])
    spl, spl_prv, new_spl, _, _ = split(op)
    assert list(spl) == [31] and list(spl_prv) == [7]   # size first, overlap only breaks ties
    assert list(new_spl) == [30]


def test_every_branch_of_every_split_is_classified():
    rng = np.random.default_rng(0)
    rows = []
    for prv in range(30):                      # 30 splits of 2-4 branches with small integer sizes (many ties)
        for k in range(rng.integers(2, 5)):
            rows.append([1000 + 10 * prv + k, 10 * prv + k, int(rng.integers(3, 6)), prv, prv, 20,
                         float(rng.integers(10, 50))])
    op = overlays(rows)
    spl, _, new_spl, _, _ = split(op)
    assert len(spl) == 30
    assert sorted(np.concatenate([spl, new_spl])) == sorted(op.index_1)


def test_merge_tie_in_size_broken_by_overlap():
    # current cluster 50 is the merge of previous 3 and 4, of the same size
    op = overlays([[50, 1, 30, 3, 1, 8, 15.0],
                   [50, 1, 30, 4, 2, 8, 60.0],
                   [51, 2, 5, 6, 3, 5, 80.0]])
    mrg, mrg_prv, frame = merge(op)
    assert list(mrg) == [50]
    assert list(mrg_prv) == [4]                    # continues the parent with the largest overlap
    assert sorted(frame.merge_ids.iloc[0]) == [3, 4]


def test_merge_largest_parent_continues():
    op = overlays([[60, 1, 30, 3, 1, 9, 15.0],
                   [60, 1, 30, 4, 2, 8, 60.0]])
    _, mrg_prv, _ = merge(op)
    assert list(mrg_prv) == [3]                    # size first


def chain_field():
    """Strokes on a grid: two dense storms (5 x 5 points) 45 px apart, joined by a line of isolated points 4 px
    apart (a chain)."""
    data = np.zeros((40, 120))
    data[10:15, 10:15] = 1
    data[10:15, 60:65] = 1
    data[12, 18:59:4] = 1
    return data


def test_dbscan_min_samples_breaks_chain():
    data = chain_field()
    _, lab3 = dbscan_clustering(data, operator.ge, 1, 3, eps=4, min_samples=3)
    _, lab6 = dbscan_clustering(data, operator.ge, 1, 3, eps=4, min_samples=6)
    assert len(np.unique(lab3[:, -1])) == 1        # the chain joins the two storms
    assert len(np.unique(lab6[:, -1])) == 2        # with a denser core the storms stay apart
    assert len(lab6) < len(lab3)                   # the middle of the chain is noise


def test_clustering_passes_min_samples_and_default():
    data = chain_field()
    _, lab = clustering('dbscan', data, operator.ge, 1, 3, eps=4, min_samples=6)
    assert len(np.unique(lab[:, -1])) == 2
    _, lab = clustering('dbscan', data, operator.ge, 1, 3, eps=4)
    assert len(np.unique(lab[:, -1])) == 1         # default min_samples = 3, as before
    nl = default_parameters({'input_path': '/nonexistent/', 'x_dim': 1, 'y_dim': 1})
    assert nl['min_samples'] == 3
