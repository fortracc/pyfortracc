import geopandas as gpd
import cv2
import numpy as np
from shapely.ops import linemerge
from shapely.geometry import Point, LineString, MultiLineString
from pyfortracc.utilities.math_utils import point_position, calc_mean_uv
from .opticalflow_filters import histogram_equalization, apply_gaussian_blur
from shapely.affinity import affine_transform

# Set number of threads cv2
cv2.setNumThreads(2)


def opticalflow_mtd(cur_df, prev_df, name_list, geotrf):
    """
    Calculate optical flow between two frames using specified optical flow methods.

    This function computes the optical flow between two sets of frames using either the Lucas-Kanade or Farneback method. 
    It processes the frames, calculates the flow vectors, and generates a vector field based on the calculated optical flow. 
    The resulting vector field is then spatially joined with the current frame to associate each vector with a specific region.

    Parameters
    ----------
    cur_df : GeoDataFrame
        The current frame containing the geometries and thresholds used for optical flow calculation.
    prev_df : GeoDataFrame
        The previous frame containing the geometries and thresholds used for optical flow calculation.
    read_fnc : function
        Function used to read and normalize the image frames.
    name_list : dict
        A dictionary containing configuration information, including paths and settings.
    geotrf : tuple
        A tuple containing the geotransform information for the image frames.
        
    Returns
    -------
    index : list
        List of indexes corresponding to the frames where optical flow was calculated.
    u_ : list
        List of u components of the optical flow vectors.
    v_ : list
        List of v components of the optical flow vectors.
    vector_field : GeoSeries
        GeoSeries containing the vector field with LineString or MultiLineString geometries representing the flow.

    Notes
    -----
    - The function supports two optical flow methods: 'lucas-kanade' and 'farneback'. The chosen method determines how the 
    optical flow is calculated between frames.
    - The `read_fnc` function is used to read and normalize the images before processing. The images are adjusted based 
    on a threshold value.
    - The optical flow is computed between consecutive frames, and the resulting flow vectors are used to create a vector field.
    - The vector field is spatially joined with the current frame to ensure that the flow vectors are associated with 
    the correct regions.
    - If multiple LineStrings are present, they are merged into a MultiLineString to represent the combined flow vectors.
    - A buffer is applied to the geometries in the current frame to ensure that points are within the polygonal areas for 
    accurate spatial joining.
    """
    
    # Set output
    index, u_, v_, vector_field = [], [], [], []
    # Set optical flow method
    if name_list['opt_mtd'] == 'lucas-kanade':
        optical_flow = lucas_kanade
    elif name_list['opt_mtd'] == 'farneback':
        optical_flow = farneback
    else:
        optical_flow = lucas_kanade
        print(f"optical flow method {name_list['opt_mtd']} \
                not implemented, by default using lucas_kanade")
    

    # Mount current image based on the current frame
    cur_y = cur_df['array_y'].explode().values.astype(int)
    cur_x = cur_df['array_x'].explode().values.astype(int)
    cur_v = cur_df['array_values'].explode().values
    current_img = np.zeros((name_list['y_dim'], name_list['x_dim']), dtype=np.float32)
    current_img[cur_y, cur_x] = cur_v

    # Mount previous image based on the previous frame
    prev_y = prev_df['array_y'].explode().values.astype(int)
    prev_x = prev_df['array_x'].explode().values.astype(int)
    prev_v = prev_df['array_values'].explode().values
    previous_img = np.zeros((name_list['y_dim'], name_list['x_dim']), dtype=np.float32)
    previous_img[prev_y, prev_x] = prev_v

    # Normalize images
    current_img = cv2.normalize(current_img, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)
    previous_img = cv2.normalize(previous_img, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)

    # Apply histogram equalization
    current_img = histogram_equalization(current_img)
    previous_img = histogram_equalization(previous_img)

    # Add cur_img and prev_img to img_frames list
    img_frames = [current_img, previous_img]
    
    # Initialize empty array for current points
    currPts = np.empty((0,1,2), dtype=int)

    # Save p0 points
    v_field, p0_, u_, v_ = [], [], [], []
    # Iterate over the images to calculate the optical flow
    u_vec, v_vec = [], [] # Initialize empty arrays for u and v components
    for tm in range(len(img_frames) - 1):
        cur_img = img_frames[tm] # Current image
        prv_img = img_frames[tm + 1] # Previous image
        # Call Optical Flow Methods
        prevPts, currPts = optical_flow(cur_img, prv_img, currPts)
        for point in zip(prevPts, currPts):
            # Calculate u and v components
            u = (point[1][0][0] - point[0][0][0]) * name_list['x_res']
            v = (point[1][0][1] - point[0][0][1]) * name_list['y_res']
            # Append u and v components
            u_vec.append(u)
            v_vec.append(v)
            # Mount vector Line
            vect_line = LineString([Point(point[0]), Point(point[1])])
            # Apply transformation to vector Line
            vect_line = affine_transform(vect_line, geotrf)
            v_field.append(vect_line)
            # Get p0 points
            p0 = affine_transform(Point(point[1]), geotrf)
            p0_.append(p0)
        currPts = prevPts # Set current points

    # Check if no vector field was calculated
    if len(v_field) == 0:
        return [], [], [], []   
    # Merge lines if using more than one optical flow time
    if len(prev_df.file.unique()) > 1:
        v_field = linemerge(v_field)
        if isinstance(v_field, LineString):
            v_field = [v_field]
        elif isinstance(v_field, MultiLineString):
            v_field = list(v_field.geoms)
    # Create GeoDataFrame with p0 points p0_x and p0_y
    vec_field = gpd.GeoDataFrame({'vector_field': v_field,
                                'geometry': p0_,
                                'u': u_vec,
                                'v': v_vec})
    # Before spatial join, apply a buffer into current frame to increase the
    # area of the polygon and avoid points that are outside of the polygon
    ccur_df = cur_df.copy()
    buffer_size = (name_list['x_res'] + name_list['y_res']) / 2
    ccur_df['geometry'] = ccur_df['geometry'].buffer(buffer_size)
    # Spatial join to associate vector_field with current frame
    within = gpd.sjoin(vec_field, ccur_df, how='inner', predicate='within', 
                    lsuffix='l', rsuffix='r').reset_index()
    # Sort by threshold_level in descending order
    within = within.sort_values(by=['threshold_level'], ascending=False)
    # Drop duplicates in index column
    within = within.drop_duplicates(subset=['index'])
    # Groupby index_r
    g_within = within.groupby('index_r')
    # Iterate over groups
    for idx, group in g_within:
        index.append(idx)
        mean_uv = calc_mean_uv(group[['u','v']].values)
        u_.append(mean_uv[0])
        v_.append(mean_uv[1])
        if len(group) == 1: # If only one LineString
            vector_field.append(group['vector_field_l'].values[0])
        else: # If more than one LineString Convert to MultiLineString
            m_lines = MultiLineString(group['vector_field_l'].values.tolist())
            vector_field.append(m_lines)
    return index, u_, v_, vector_field

    
def lucas_kanade(current_img, previous_img, currPts):
    """ 
    Lucas Kanade optical flow method used to compute the optical flow for a
    sparse feature set using the iterative Lucas-Kanade method with pyramids.
    Using reverse image order (t-1,t-2,t-3,...)
    
    Commend parameters of ShiTomasi corner detection

    cv2.goodFeaturesToTrack Parameters:
    - image (array): Input 8-bit or floating-point 32-bit, single-channel image.
    - maxCorners (int): Maximum number of corners to return. If there are
    more corners than are found, the strongest of them
    is returned. maxCorners <= 0 implies that no limit
    on the maximum is set and all detected corners are
    returned.
    - qualityLevel (float): Parameter characterizing the minimal accepted
    quality of image corners. The parameter value is
    multiplied by the best corner quality measure,
    which is the minimal eigenvalue (see
    cornerMinEigenVal ) or the Harris function
    response (see cornerHarris ). The corners with
    the quality measure less than the product are
    rejected. For example, if the best corner has
    the quality measure = 1500, and the
    qualityLevel=0.01 , then all the corners with
    the quality measure less than 15 are rejected.
    - minDistance (float): Minimum possible Euclidean distance between the
    returned corners.
    - mask (array): Optional region of interest. If the image is not empty
    (it needs to have the type CV_8UC1 and the same size as
    image ), it specifies the region in which the corners
    are detected.
    - blockSize (int): Size of an average block for computing a derivative
    covariation matrix over each pixel neighborhood.
    - useHarrisDetector (bool): Parameter indicating whether to use a Harris
    detector (see cornerHarris) or
    cornerMinEigenVal.
    - k (float): Free parameter of the Harris detector.
    
    ----------------------------------------
    
    cv2.calcOpticalFlowPyrLK Parameters:
    - prevImg (array): first 8-bit single-channel input image.
    - nextImg (array): second input image of the same size and the same type
    as prevImg.
    - prevPts (array): vector of 2D points for which the flow needs to be
    found; point coordinates must be single-precision
    floating-point numbers.
    - nextPts (array): output vector of 2D points (with single-precision
    floating-point coordinates) containing the calculated
    new positions of input features in the second image;
    when OPTFLOW_USE_INITIAL_FLOW flag is passed, the
    vector must have the same size as in the input.
    - winSize (tuple): size of the search window at each pyramid level.
    - maxLevel (int): 0-based maximal pyramid level number; if set to 0,
    pyramids are not used (single level), if set to 1,
    two levels are used, and so on; if pyramids are
    passed to input then algorithm will use as many
    levels as pyramids have but no more than maxLevel.
    - criteria (tuple): parameter, specifying the termination criteria of
    the iterative search algorithm (after the specified
    maximum number of iterations criteria.maxCount or
    when the search window moves by less than
    criteria.epsilon.
    - flags (int): operation flags: 0 or OPTFLOW_LK_GET_MIN_EIGENVALS.
    - minEigThreshold (float): the algorithm calculates the minimum eigen
    value of a 2x2 normal matrix of optical flow
    equations (this matrix is called a spatial
    gradient matrix in [Bouguet00]), divided by
    number of pixels in a window; if this value
    is less than minEigThreshold, then a
    corresponding feature is filtered out and
    its flow is not processed, so it allows to
    remove bad points and get a performance boost.
    """
    # Check if currPts is empty (first iteration) and call ShiTomasi
    if len(currPts) == 0:
        # Params for ShiTomasi corner detection
        feature_params = dict(
            maxCorners=None,
            qualityLevel=0.01,
            minDistance=0.5,
            blockSize=2,
            useHarrisDetector=False,
            k=0.04,)
        # ShiTomasi corner detection
        currPts = cv2.goodFeaturesToTrack(current_img, mask=None,
                                          **feature_params)
        # Check if currPts is None
        if currPts is None:
            return [], []
    # Call Lucas Kanade optical flow
    win_percent = 20 # Percent of image size to use as window size
    win_size = (current_img.shape[1] // win_percent, 
                current_img.shape[0] // win_percent)
    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01)
    flags = cv2.OPTFLOW_LK_GET_MIN_EIGENVALS
    nextPts, status, _ = cv2.calcOpticalFlowPyrLK(prevImg=current_img,
                                                nextImg=previous_img,
                                                prevPts=currPts,
                                                nextPts=None,
                                                winSize=win_size,
                                                maxLevel=3,
                                                criteria=criteria,
                                                flags=flags,
                                                minEigThreshold=1e-4)
    # Select good points and reshape to correct format
    nextPts = nextPts[status == 1]
    currPts = currPts[status == 1]
    nextPts = nextPts[:, np.newaxis, :]
    currPts = currPts[:, np.newaxis, :] 
    return nextPts, currPts
    
    
def farneback(current_img, previous_img, _ ):
    """ 
    Compute optical flow between two images using the Farneback method.

    This function calculates the dense optical flow between two consecutive images using the Farneback method, 
    which is suitable for estimating motion and tracking feature points. The function also processes the flow 
    to extract a sparse set of feature points based on their magnitude and converts them to next position coordinates.

    Parameters
    ----------
    current_img : numpy.ndarray
        The current image (t) in the sequence, used as the second input for optical flow calculation.
    previous_img : numpy.ndarray
        The previous image (t-1) in the sequence, used as the first input for optical flow calculation.
    _ : placeholder
        Unused parameter for compatibility with specific function signatures.

    Returns
    -------
    nextPts : numpy.ndarray
        Array of feature points' next positions calculated from the optical flow. Shape is (-1, 1, 2).
    currPts : numpy.ndarray
        Array of feature points' current positions before applying the optical flow. Shape is (-1, 1, 2).

    Notes
    -----
    - The Farneback method computes the optical flow field, which represents the apparent motion of objects between two frames.
    - The 'cv2.calcOpticalFlowFarneback' function is used with specific parameters to control the flow estimation:
        - pyr_scale: 0.5 for pyramid scaling, where each next layer is half the size of the previous.
        - levels: 3 pyramid levels, including the initial image.
        - winsize: 50, the size of the averaging window.
        - iterations: 3 iterations per pyramid level.
        - poly_n: 10, the pixel neighborhood size for polynomial expansion.
        - poly_sigma: 1.1, the standard deviation of the Gaussian used for smoothing derivatives.
    - Magnitudes of flow vectors greater than 1 are considered, and a sparsity factor of 10 is used to reduce the number of feature points.
    - The function uses 'cv2.cartToPolar' to convert Cartesian coordinates to polar coordinates to extract magnitude and angle.
    - The 'point_position' function is used to compute the next positions of the points based on their magnitude and angle.
    - The function checks for infinite values in the calculated next positions and removes them if necessary.
    """
    flow = cv2.calcOpticalFlowFarneback(prev=current_img,
                                        next=previous_img,
                                        flow=None,
                                        pyr_scale=0.5,
                                        levels=3,
                                        winsize=50,
                                        iterations=3,
                                        poly_n=10,
                                        poly_sigma=1.1,
                                        flags=0)
    magn, angle = cv2.cartToPolar(flow[...,0], flow[...,1]) 
    y_idx, x_idx = np.where(magn > 1)  # Get position of points magnitude > 1
    pixel_sparsity = 10 # Sparsity of pixels
    y_idx = y_idx[::pixel_sparsity]
    x_idx = x_idx[::pixel_sparsity]
    magn = magn[y_idx, x_idx] # Get magnitude of points with magnitude > 1
    angle = np.rad2deg(angle[y_idx, x_idx]) # angle of points with magnitude > 1
    points = [point_position(x_idx[p],y_idx[p], magn[p], angle[p]) 
            for p in range(len(y_idx))]
    nextPts = np.array(points).reshape(-1, 1, 2)
    currPts = np.array([x_idx, y_idx]).T.reshape(-1, 1, 2)
    if np.any(np.isinf(nextPts)): # Verify if have inf values in nextPts
        inf_idx = np.where(np.isinf(nextPts))
        nextPts = np.delete(nextPts, inf_idx[0], axis=0)
        currPts = np.delete(currPts, inf_idx[0], axis=0)
    return nextPts, currPts