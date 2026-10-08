"""Test of the resume of the cluster linking with frames written without the iuid column.

With a single threshold (e.g. DBSCAN of lightning strokes) the empty frames are written without iuid, and the resume
used to fail reading that column from them. The resume must also stop at a linked file truncated by an interrupted run.
"""
import pandas as pd

from pyfortracc.cluster_linking.cluster_linking import resume_linking


def test_resume_with_empty_frame_without_iuid(tmp_path):
    spatial, linked = tmp_path / 'spatial', tmp_path / 'linked'
    spatial.mkdir()
    linked.mkdir()
    names = ['20140101_0000.parquet', '20140101_0012.parquet', '20140101_0024.parquet', '20140101_0036.parquet']
    for n in names:
        (spatial / n).touch()
    pd.DataFrame({'uid': [1, 2], 'iuid': [None, None], 'threshold_level': [0, 0],
                  'cindex': [0, 1]}).to_parquet(linked / names[0])
    pd.DataFrame({'uid': pd.Series([], dtype='int64'), 'threshold_level': pd.Series([], dtype='int64'),
                  'cindex': pd.Series([], dtype='int64')}).to_parquet(linked / names[1])        # empty, no iuid
    pd.DataFrame({'uid': [3], 'iuid': [None], 'threshold_level': [0], 'cindex': [2]}).to_parquet(linked / names[2])
    (linked / names[3]).write_bytes(b'PAR1 truncated')                                         # interrupted write
    start, prv_frame, prv_stamp, uid_iter, cdx, iuid_cnt = resume_linking(
        [str(spatial / n) for n in names], f'{linked}/', pd.DataFrame(), None, 0, 0, {})
    assert start == 3                              # resumes at the truncated frame
    assert uid_iter == 4                           # next free uid
    assert list(prv_frame['uid']) == [3]
    assert prv_stamp == pd.Timestamp('2014-01-01 00:24')
