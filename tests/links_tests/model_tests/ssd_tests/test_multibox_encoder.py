import numpy as np
import unittest

from chainer import cuda
from chainer import testing
from chainer.testing import attr

from chainercv.links.model.ssd import MultiboxEncoder


def _random_array(shape):
    return np.random.uniform(-1, 1, size=shape).astype(np.float32)


@testing.parameterize(*testing.product_dict(
    [
        {
            'grids': (4,),
            'aspect_ratios': ((2,),),
            'steps': (1,),
            'sizes': (1, 2),
        },
        {
            'grids': (4, 2, 1),
            'aspect_ratios': ((2,), (3, 4), (5,)),
            'steps': (1, 2, 4),
            'sizes': (1, 2, 3, 4),
        },
    ],
    testing.product({
        'n_fg_class': [1, 5],
        'nms_thresh': [None, 0.5],
        'score_thresh': [0, 0.5, np.inf],
    })
))
class TestDefaultBboxEncoder(unittest.TestCase):

    def setUp(self):
        self.encoder = MultiboxEncoder(
            self.grids, self.aspect_ratios, self.steps, self.sizes, (0.1, 0.2))
        self.n_bbox = sum(
            grid * grid * (len(ar) + 1) * 2
            for grid, ar in zip(self.grids, self.aspect_ratios))
        self.mb_loc = _random_array((self.n_bbox, 4))
        self.mb_conf = _random_array((self.n_bbox, self.n_fg_class + 1))

    @attr.gpu
    def test_to_cpu(self):
        self.encoder.to_gpu()
        self.encoder.to_cpu()
        self.assertEqual(self.encoder.xp, np)

    @attr.gpu
    def test_to_gpu(self):
        self.encoder.to_gpu()
        self.assertEqual(self.encoder.xp, cuda.cupy)

    def test_dafault_bbox(self):
        self.assertEqual(
            self.encoder._default_bbox.shape, (self.n_bbox, 4))

    def _check_decode(self, mb_loc, mb_conf):
        xp = self.encoder.xp

        bbox, label, score = self.encoder.decode(
            mb_loc, mb_conf, self.nms_thresh, self.score_thresh)

        self.assertIsInstance(bbox, xp.ndarray)
        self.assertEqual(bbox.ndim, 2)
        self.assertLessEqual(bbox.shape[0], self.n_bbox * self.n_fg_class)
        self.assertEqual(bbox.shape[1], 4)

        self.assertIsInstance(label, xp.ndarray)
        self.assertEqual(label.ndim, 1)
        self.assertEqual(label.shape[0], bbox.shape[0])

        self.assertIsInstance(score, xp.ndarray)
        self.assertEqual(score.ndim, 1)
        self.assertEqual(score.shape[0], bbox.shape[0])

    def test_decode_cpu(self):
        self._check_decode(self.mb_loc, self.mb_conf)

    @attr.gpu
    def test_decode_with_default_bbox_gpu(self):
        self.encoder.to_gpu()
        self._check_decode(cuda.to_gpu(self.mb_loc), cuda.to_gpu(self.mb_conf))


testing.run_module(__name__, __file__)
