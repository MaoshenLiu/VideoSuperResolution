"""
Copyright: Intel Corp. 2018
Author: Wenyi Tang
Email: wenyi.tang@intel.com
Created Date: May 8th 2018
Updated Date: May 8th 2018

Image processing tools
"""

import numpy as np
from PIL import Image
from .Utility import to_list


def array_to_img(x, mode='YCbCr'):
    """Convert an ndarray to PIL Image."""
    return Image.fromarray(x.astype('uint8'), mode=mode)


def img_to_array(img, data_format=None):
    """Converts a PIL Image instance to a Numpy array.

      Copy from Keras
    """
    if data_format is None:
        data_format = 'channels_last'
    if data_format not in {'channels_first', 'channels_last'}:
        raise ValueError('Unknown data_format: ', data_format)
    # Numpy array x has format (height, width, channel)
    # or (channel, height, width)
    # but original PIL image1 has format (width, height, channel)
    x = np.asarray(img, dtype=np.uint8)
    if len(x.shape) == 3:
        if data_format == 'channels_first':
            x = x.transpose([2, 0, 1])
    elif len(x.shape) == 2:
        if data_format == 'channels_first':
            x = x.reshape((1, x.shape[0], x.shape[1]))
        else:
            x = x.reshape((x.shape[0], x.shape[1], 1))
    else:
        raise ValueError('Unsupported image1 shape: ', x.shape)
    return x


def img_to_yuv(frame, mode, grayscale=False):
    """Change color space of `frame` from any supported `mode` to YUV

      Args:
          frame: 3-D tensor in either [H, W, C] or [C, H, W]
          mode: A string, must be one of [YV12, YV21, NV12, NV21, RGB, BGR]
          grayscale: discard uv planes

      return:
          3-D tensor of YUV in [H, W, C]
    """

    _planar_mode = ('YV12', 'YV21', 'NV12', 'NV21')
    _packed_mode = ('RGB', 'BGR')
    _allowed_mode = (*_planar_mode, *_packed_mode)
    if not isinstance(frame, list):
        raise TypeError("frame must be a list of numpy array")
    if not mode in _allowed_mode:
        raise ValueError("invalid mode: " + mode)
    if mode in _planar_mode:
        if mode in ('YV12', 'YV21'):
            y, u, v = frame
        elif mode in ('NV12', 'NV21'):
            y, uv = frame
            u = uv.flatten()[0::2].reshape([1, uv.shape[1] // 2, uv.shape[2]])
            v = uv.flatten()[1::2].reshape([1, uv.shape[1] // 2, uv.shape[2]])
        else:
            y = u = v = None
        y = np.transpose(y)
        u = np.transpose(u)
        v = np.transpose(v)
        if '21' in mode:
            u, v = v, u
        if not grayscale:
            up_u = np.zeros(shape=[u.shape[0] * 2, u.shape[1] * 2, u.shape[2]])
            up_v = np.zeros(shape=[v.shape[0] * 2, v.shape[1] * 2, v.shape[2]])
            up_u[0::2, 0::2, :] = up_u[0::2, 1::2, :] = u
            up_u[1::2, ...] = up_u[0::2, ...]
            up_v[0::2, 0::2, :] = up_v[0::2, 1::2, :] = v
            up_v[1::2, ...] = up_v[0::2, ...]
            yuv = np.concatenate([y, up_u, up_v], axis=-1)
            yuv = np.transpose(yuv, [1, 0, 2])  # PIL needs [W, H, C]
            img = Image.fromarray(yuv.astype('uint8'), mode='YCbCr')
        else:
            y = np.squeeze(y)
            img = Image.fromarray(np.transpose(y).astype('uint8'), mode='L')
    elif mode in _packed_mode:
        assert len(frame) is 1
        rgb = np.asarray(frame[0])
        if mode == 'BGR':
            rgb = rgb[..., ::-1]
        rgb = np.transpose(rgb, [1, 0, 2])
        if not grayscale:
            img = Image.fromarray(rgb, mode='RGB').convert('YCbCr')
        else:
            img = Image.fromarray(rgb, mode='RGB').convert('L')
    else:
        raise RuntimeError("unreachable!")
    # return img_to_array(image1) if turn_array else image1
    return img


def imresize(image, scale, mode=None):
    """Image resize using simple cubic provided in PIL

    @Todo: perhaps more accurate resize kernel should be used.
    """

    size = (np.array(image.size) * scale).astype(int)
    if image.mode in ('RGB', 'BGR'):
        image = image.convert('YCbCr')
    mode = image.mode if not mode else mode
    return image.resize(size, resample=Image.BICUBIC).convert(mode)


def shrink_to_multiple_scale(image, scale):
    """Crop the `image` to make its width and height multiple of scale factor"""
    size = np.asarray(image.size, dtype='int32')
    scale = np.asarray(scale, dtype='int32')
    size -= size % scale
    return image.crop([0, 0, *size])


def imread(url, mode='RGB'):
    """Read image from file to ndarray"""

    img = Image.open(url)
    return img_to_array(img.convert(mode))


def random_crop_batch_image(image, batch, shape, seed=None):
    h, w = image.shape[:2]
    b = []
    np.random.seed(seed)
    for _ in range(batch):
        y = np.random.randint(0, h - shape[1])
        x = np.random.randint(0, w - shape[0])
        b.append(image[y:y + shape[1], x:x + shape[0], :])
    return np.stack(b)


import tensorflow as tf

"""
Functions that start with `tf_` process image(s) using TF functions,
this intends to speed up image procession.

But I personally thought `tf.image` is hard to use
"""


def tf_decode_image_file(url, dtype=None):
    """Decode image from file
      Args:
          url: path to image
          dtype: target image type

      Return:
          A 4-D tensor image with shape [len(url), H, W, C]
    """
    url = to_list(url)
    with tf.name_scope('DecodeImageFile'):
        images = []
        for _url in url:
            with open(_url, 'rb') as fp:
                img = tf.image.decode_image(fp.read())
                img = tf.image.convert_image_dtype(img, dtype)
            images.append(img)
        return tf.concat(images, 0)


def tf_random_crop_batch_image(image, batch, shape, seed=None, name=None):
    """Randomly crop a single image into `batch` pieces

      Args:
          image: A 3-D tensor with shape [H, W, C]
          batch: A scalar of type UINT
          shape: A 3-D tensor with crop shape
          seed: seed of random op
          name: op name

      Return:
          A 4-D tensor image with shape [batch, *shape]
    """

    with tf.name_scope('RandomCropBatchImage'):
        image = tf.expand_dims(image, 0)
        op = tf.random_crop(image, [1, shape[0], shape[1], shape[2]], seed, name)
        image = tf.tile(op, [batch, 1, 1, 1])
    return image
