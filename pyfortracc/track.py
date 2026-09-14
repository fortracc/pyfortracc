import shutil
from .features_extraction import features_extraction
from .spatial_operations import spatial_operations
from .cluster_linking import cluster_linking
from .concat import concat
from .post_processing.duration import compute_duration


def track(name_lst={},
            read_fnc=None,
            parallel=True,
            feat_ext=True,
            spat_ope=True,
            clst_lnk=True,
            concat_r=True,
            duration=False,
            clean=True,
            resume=False):
    """ Track Module
    It is a module that performs the tracking clusters in time and space.

    Parameters
    ----------
    name_lst : dict
        Dictionary with the parameters to be used.
    read_fnc : function
        Function to read the data.
    parallel : bool
        If True, parallel processing is used.
    feat_ext : bool
        If True, features extraction is performed.
    spat_ope : bool
        If True, spatial operations are performed.
    clst_lnk : bool
        If True, cluster linking is performed.
    clean : bool
        If True, the output_path is removed before the tracking.
        Ignored when resuming.
    resume : bool
        If True, resume an interrupted run from the files already written in
        output_path. Run again with the same name_lst of the interrupted run.
    """
    # Parameters check
    if name_lst == {}:
        raise ValueError('name_lst parameter is empty')
    if read_fnc is None:
        raise ValueError('read_fnc object is empty')
    # Set resume to be used by each stage. The argument always overrides the
    # name_lst value, so a name_lst reused from a resumed run starts clean
    name_lst['resume'] = resume
    # Clean previous results
    if clean and not name_lst['resume']:
        shutil.rmtree(name_lst['output_path'], ignore_errors=True)
    # Extract features
    if feat_ext:
        features_extraction(name_lst, read_fnc, parallel=parallel)
    # Spatial operations
    if spat_ope:
        spatial_operations(name_lst, read_fnc, parallel=parallel)
    # Cluster linking
    if clst_lnk:
        cluster_linking(name_lst)
    # Concatenate results
    if concat_r:
        concat(name_lst)
    # Compute duration
    if duration:
        compute_duration(name_lst, parallel=parallel)
