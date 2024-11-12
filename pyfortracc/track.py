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
            clean=True):
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
    """
    # Parameters check
    if name_lst == {}:
        raise ValueError('name_lst parameter is empty')
    if read_fnc is None:
        raise ValueError('read_fnc object is empty')
    # Clean previous results
    if clean:
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
