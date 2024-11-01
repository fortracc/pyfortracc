'''
The choice of strategy for increasing the standard deviation of your matrix 
depends on the specific goals and constraints of your application. 
There isn't a one-size-fits-all "best" strategy because it depends on what
you're trying to achieve. Here are some common strategies, each with its
own advantages and use cases:

    Gaussian Noise Addition:
        Advantages: This approach is statistically rigorous and can precisely
        control the standard deviation of the resulting matrix.
        Use Case: If you need to simulate data with a specific level of noise 
        for testing or modeling purposes, adding Gaussian noise is a
        good choice.

    Smoothing or Blurring:
        Advantages: Applying a smoothing filter like Gaussian blur can 
        effectively increase the standard deviation of a matrix while preserving
        some spatial characteristics.
        Use Case: When working with images or spatial data and you want to 
        reduce high-frequency noise while increasing overall variability.

    Scaling or Amplification:
        Advantages: You can multiply the entire matrix by a scalar factor to
        increase its standard deviation. This is a straightforward method.
        Use Case: When you need to quickly adjust the standard deviation 
        without introducing randomness or altering the data distribution.

    Data Transformation:
        Advantages: For specific types of data, you may use mathematical 
        transformations to adjust the standard deviation. For example, 
        for normally distributed data, you can use the Z-score transformation.
        Use Case: When working with data that follows a known distribution and 
        you want to standardize it.

The "best" strategy depends on the nature of your data, your objectives, and 
the specific context of your application. Here are some considerations to help
you choose:

    Preservation of Data Characteristics: Consider whether you need to preserve 
    the original data characteristics, such as the data distribution or spatial
    features. Some methods (e.g., Gaussian noise addition) may introduce 
    randomness that alters the data distribution.

    Application-Specific Requirements: Think about the requirements of your 
    application. For example, if you're working on image processing, blurring 
    might be suitable for noise reduction and increasing variability.

    Control and Reproducibility: If you require precise control over the 
    standard deviation and need to reproduce the same results, methods like 
    Gaussian noise addition or scaling may be better suited.

    Data Understanding: Understand the underlying data and the effect of each 
    method on the data's interpretation and analysis. Consider how each approach
    may impact the quality of your results.

Ultimately, the choice of strategy should align with your specific objectives 
and the nature of your data. It may also involve experimentation to determine 
the best approach based on the results you achieve.
'''

import cv2
import numpy as np

# Function to add Gaussian noise to an image
def add_gaussian_noise(image, mean=0, stddev=25):
    """ 
    Add Gaussian noise to an image.

    Parameters
    ----------
    image : numpy.ndarray
        The input image to which Gaussian noise will be added. This should be a grayscale or color image in the form.
    mean : float, optional
        The mean of the Gaussian noise distribution. Default is 0.
    stddev : float, optional
        The standard deviation of the Gaussian noise distribution. Default is 25.

    Returns
    -------
    noisy_image : numpy.ndarray
        The image with added Gaussian noise. It has the same shape as the input image.

    Notes
    -----
    - Gaussian noise is generated using a normal distribution with the specified mean and standard deviation.
    - The noise is added to the image using 'cv2.add' to ensure proper handling of pixel values, preventing overflow or underflow.
    - The noise is cast to an unsigned 8-bit integer (np.uint8) before addition to match typical image data types.
    """
    # Generate Gaussian noise
    noise = np.random.normal(mean, stddev, image.shape).astype(np.uint8)
    # Add noise to the image
    noisy_image = cv2.add(image, noise)
    return noisy_image

# Function to apply Gaussian blur (smoothing) to an image
def apply_gaussian_blur(image, kernel_size=(5, 5), sigma=1.0):
    """ 
    Apply Gaussian blur (smoothing) to an image.

    Parameters
    ----------
    image : numpy.ndarray
        The input image to which Gaussian blur will be applied. This should be a grayscale or color image in the form.
    kernel_size : tuple of int, optional
        The size of the Gaussian kernel. It should be a tuple of two odd integers (width, height). Default is (5, 5).
    sigma : float, optional
        The standard deviation of the Gaussian kernel in both X and Y directions. Default is 1.0.

    Returns
    -------
    blurred_image : numpy.ndarray
        The image after applying Gaussian blur. It has the same shape as the input image.

    Notes
    -----
    - Gaussian blur is used to reduce image noise and detail by averaging pixel values with a Gaussian-weighted kernel.
    - The 'kernel_size' should be odd and positive; otherwise, the function will adjust the values automatically.
    - A larger 'sigma' value results in more significant blurring. If 'sigma' is set to 0, it is calculated based on 'kernel_size'.
    """
    # Apply Gaussian blur
    blurred_image = cv2.GaussianBlur(image, kernel_size, sigma)
    return blurred_image

# Function to scale the intensity of an image
def scale_image_intensity(image, scale_factor=2.0):
    """ 
    Scale the intensity of an image by a specified factor.

    Parameters
    ----------
    image : numpy.ndarray
        The input image whose intensity will be scaled. This should be a grayscale or color image.
    scale_factor : float, optional
        The factor by which to scale the image's intensity. Default is 2.0.

    Returns
    -------
    scaled_image : numpy.ndarray
        The image with scaled intensity. It has the same shape as the input image.

    Notes
    -----
    - Intensity scaling multiplies each pixel value by the 'scale_factor'. This can brighten or darken the image.
    - The function uses 'cv2.multiply' to handle the scaling, which ensures that pixel values stay within the valid range (0-255) for 8-bit images.
    - If 'scale_factor' is greater than 1.0, the image will become brighter. If it's between 0 and 1.0, the image will become darker.
    - Scaling may cause pixel values to exceed the maximum value of 255, leading to clipping.
    """
    # Scale the image intensity
    scaled_image = cv2.multiply(image, np.array([scale_factor]))
    return scaled_image

# Function to apply Z-score transformation to an image
def zscore_transform(image):
    """ 
    Apply Z-score transformation to an image.

    Parameters
    ----------
    image : numpy.ndarray
        The input image to be transformed, typically in the form of a NumPy array.

    Returns
    -------
    zscore_image : numpy.ndarray
        The image after Z-score transformation, with the same shape as the input image. The output values will be standardized, having a mean of 0 and a standard deviation of 1.

    Notes
    -----
    - The Z-score transformation standardizes the image by subtracting the mean and dividing by the standard deviation of the pixel values.
    - This transformation is useful for normalizing the image, especially in preprocessing steps for machine learning models.
    - The image is converted to `float32` before performing the transformation to ensure precision and to avoid integer overflow or underflow.
    - The resulting values may not be in the typical 0-255 range, as they represent standard deviations from the mean.
    """
    # Convert image to float32 for Z-score calculation
    image_float = image.astype(np.float32)
    # Calculate mean and standard deviation of the image
    mean = np.mean(image_float)
    stddev = np.std(image_float)
    # Apply Z-score transformation
    zscore_image = (image_float - mean) / stddev
    return zscore_image

# Function to perform histogram equalization
def histogram_equalization(image):
    """ 
    Perform histogram equalization on an image to enhance contrast.

    Parameters
    ----------
    image : numpy.ndarray
        The input image for which histogram equalization will be applied.

    Returns
    -------
    equalized_image : numpy.ndarray
        The image after applying histogram equalization. If the input was a color image, the output will be a grayscale image.

    Notes
    -----
    - Histogram equalization is a technique for improving the contrast in images by spreading out the most frequent intensity values.
    - If the input image is a color image, it will be converted to grayscale before applying histogram equalization.
    - The function uses 'cv2.equalizeHist', which applies the equalization on a per-channel basis for grayscale images.
    """
    # Convert image to grayscale if it's in color
    if len(image.shape) == 3:
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray_image = image
    # Apply histogram equalization
    equalized_image = cv2.equalizeHist(gray_image)
    return equalized_image

# Function to perform image thresholding
def threshold_image(image, threshold_value=128, max_value=255,
                    threshold_type=cv2.THRESH_BINARY):
    """ 
    Perform image thresholding to create a binary or segmented image.

    Parameters
    ----------
    image : numpy.ndarray
        The input image to which thresholding will be applied.
    threshold_value : int, optional
        The threshold value used to classify the pixel values. Default is 128.
    max_value : int, optional
        The maximum value assigned to pixels that meet the thresholding condition. Default is 255.
    threshold_type : int, optional
        The type of thresholding to apply. Default is 'cv2.THRESH_BINARY'.

    Returns
    -------
    thresholded_image : numpy.ndarray
        The image after applying the specified thresholding. If the input was a color image, the output will be a grayscale thresholded image.

    Notes
    -----
    - Thresholding is a technique used to create binary images by setting pixel values to a max value if they exceed a certain threshold, or to zero otherwise.
    - The function first converts color images to grayscale before applying thresholding, as thresholding is typically applied to single-channel images.
    - The 'threshold_type' parameter allows for different types of thresholding behaviors, providing flexibility in image segmentation.
    """
    # Convert image to grayscale if it's in color
    if len(image.shape) == 3:
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray_image = image
    # Apply thresholding
    _, thresholded_image = cv2.threshold(gray_image, threshold_value, max_value,
                                        threshold_type)
    return thresholded_image

# Function to sharpen an image
def sharpen_image(image):
    """ 
    Sharpen an image using a Laplacian kernel.

    Parameters
    ----------
    image : numpy.ndarray
        The input image to be sharpened.

    Returns
    -------
    sharpened_image : numpy.ndarray
        The image after applying the sharpening filter, with enhanced edges and details.

    Notes
    -----
    - Sharpening an image enhances its edges and details, making the features more pronounced.
    - The sharpening kernel used here is a Laplacian kernel, which emphasizes the center pixel and subtracts the neighboring pixel values.
    - The function uses 'cv2.filter2D' to apply the convolution of the image with the sharpening kernel. This method is effective for both grayscale and color images.
    - The sharpening process may introduce noise or artifacts, particularly in images with already high contrast.
    """
    # Define a sharpening kernel (Laplacian)
    kernel = np.array([[0, -1, 0],
                    [-1, 5,-1],
                    [0, -1, 0]], dtype=np.float32)
    
    # Apply convolution with the sharpening kernel
    sharpened_image = cv2.filter2D(image, -1, kernel)
    return sharpened_image

# Function to perform median filtering for denoising
def denoise_median(image, kernel_size=5):
    """ 
    Perform median filtering to denoise an image.

    Parameters
    ----------
    image : numpy.ndarray
        The input image to be denoised.
    kernel_size : int, optional
        The size of the kernel to be used for median filtering. It must be a positive odd integer (e.g., 3, 5, 7). The default value is 5.

    Returns
    -------
    denoised_image : numpy.ndarray
        The image after applying median filtering, with reduced noise and preserved edges.

    Notes
    -----
    - Median filtering is a non-linear filtering technique commonly used to remove salt-and-pepper noise while preserving edges.
    - The `kernel_size` parameter determines the size of the neighborhood considered around each pixel when applying the median filter. A larger kernel size will result in stronger noise reduction but may also cause more blurring.
    - The function uses 'cv2.medianBlur' to perform the median filtering, which is effective for both grayscale and color images.
    - The kernel size must be an odd number to ensure that the median can be correctly computed from the pixel neighborhood.
    """
    # Apply median filtering
    denoised_image = cv2.medianBlur(image, kernel_size)
    return denoised_image

# Function to perform Canny edge detection
def detect_edges_canny(image, low_threshold=50, high_threshold=150):
    """ 
    Perform Canny edge detection on an image.

    Parameters
    ----------
    image : numpy.ndarray
        The input image on which edge detection will be performed.
    low_threshold : int, optional
        The lower bound for the hysteresis thresholding. Default is 50.
    high_threshold : int, optional
        The upper bound for the hysteresis thresholding. Default is 150.

    Returns
    -------
    edges : numpy.ndarray
        The binary image showing the detected edges.

    Notes
    -----
    - Canny edge detection is a multi-stage algorithm that identifies the edges in an image by looking for areas of rapid intensity change.
    - The 'low_threshold' and 'high_threshold' parameters control the sensitivity of the edge detection. Pixels with gradient values below the 'low_threshold' are discarded, while those above the 'high_threshold' are considered strong edges. 
    - The input image is automatically converted to grayscale if it is in color, as the Canny algorithm works on single-channel images.
    """
    # Convert image to grayscale if it's in color
    if len(image.shape) == 3:
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray_image = image
    # Apply Canny edge detection
    edges = cv2.Canny(gray_image, low_threshold, high_threshold)
    return edges

# Function to perform dilation operation
def dilate_image(image, kernel_size=3):
    """ 
    Perform dilation operation on an image.

    Parameters
    ----------
    image : numpy.ndarray
        The input image to be dilated.
    kernel_size : int, optional
        The size of the square structuring element (kernel) used for dilation. Default is 3.

    Returns
    -------
    dilated_image : numpy.ndarray
        The image after applying the dilation operation.

    Notes
    -----
    - Dilation is a morphological operation that enlarges the boundaries of objects in an image. It is commonly used to increase the size of foreground objects, fill in small holes, or connect disjointed elements.
    - The 'kernel_size' parameter defines the size of the structuring element used for dilation. A larger kernel size results in more significant dilation.
    - The structuring element (kernel) is generated as a square matrix of ones using 'np.ones' with the specified 'kernel_size'.
    - The function applies the dilation operation using 'cv2.dilate', which shifts the kernel over the image and replaces the center pixel with the maximum pixel value covered by the kernel.
    """
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    dilated_image = cv2.dilate(image, kernel, iterations=1)
    return dilated_image

# Function to perform erosion operation
def erode_image(image, kernel_size=3):
    """
    Perform erosion operation on an image.

    Parameters
    ----------
    image : numpy.ndarray
        The input image to be eroded.
    kernel_size : int, optional
        The size of the square structuring element (kernel) used for erosion. Default is 3.

    Returns
    -------
    eroded_image : numpy.ndarray
        The image after applying the erosion operation.

    Notes
    -----
    - Erosion is a morphological operation that reduces the boundaries of objects in an image. It is often used to remove small-scale noise, separate connected components, or shrink foreground objects.
    - The 'kernel_size' parameter defines the size of the structuring element used for erosion. A larger kernel size will result in more significant erosion.
    - The structuring element (kernel) is created as a square matrix of ones using 'np.ones' with the specified 'kernel_size'.
    - The function performs erosion using 'cv2.erode', which shifts the kernel over the image and replaces the center pixel with the minimum pixel value covered by the kernel.
    """
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    eroded_image = cv2.erode(image, kernel, iterations=1)
    return eroded_image

# Function to perform texture analysis (example: Gabor filter)
def texture_analysis(image, kernel_size=7, theta=0, sigma=2.0, frequency=0.2):
    """ 
    Perform texture analysis on an image using a Gabor filter.

    Parameters
    ----------
    image : numpy.ndarray
        The input image to which the Gabor filter will be applied.
    kernel_size : int, optional
        The size of the Gabor kernel. The kernel will be a square matrix of size (kernel_size, kernel_size). Default is 7.
    theta : float, optional
        The orientation of the Gabor filter in radians. The angle is measured from the x-axis. Default is 0 (horizontal orientation).
    sigma : float, optional
        The standard deviation of the Gaussian envelope of the Gabor filter. Default is 2.0.
    frequency : float, optional
        The spatial frequency of the sinusoidal component of the Gabor filter. Default is 0.2.

    Returns
    -------
    filtered_image : numpy.ndarray
        The image after applying the Gabor filter, highlighting texture features.

    Notes
    -----
    - A Gabor filter is used for texture analysis and edge detection. It is especially effective at capturing texture patterns and frequencies.
    - The 'kernel_size' determines the dimensions of the Gabor kernel, which will be a square matrix with size (kernel_size, kernel_size).
    - The 'theta' parameter controls the orientation of the filter. A value of 0 indicates horizontal orientation, while other values rotate the filter accordingly.
    - The 'sigma' parameter controls the width of the Gaussian envelope, affecting the filter's scale and the extent of smoothing.
    - The 'frequency' parameter defines the spatial frequency of the sinusoidal component, which influences the filter's sensitivity to different texture patterns.
    - The function uses OpenCV's 'cv2.getGaborKernel' to create the Gabor kernel and 'cv2.filter2D' to apply the filter to the image.
    """
    # Create a Gabor kernel
    kernel = cv2.getGaborKernel((kernel_size, kernel_size), sigma, theta, 1.0, 
                                frequency, 0, ktype=cv2.CV_32F)
    # Apply Gabor filter to the image
    filtered_image = cv2.filter2D(image, cv2.CV_8UC3, kernel)
    return filtered_image
