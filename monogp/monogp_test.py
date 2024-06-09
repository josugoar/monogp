import torch
from mmengine.structures import InstanceData

from mmdet3d.models import Base3DDetector
from mmdet3d.registry import MODELS
from mmdet3d.structures import points_cam2img
from .utils import points_img2plane

EPSILON = 1e-4


@MODELS.register_module()
class MonoGpTest(Base3DDetector):

    def __init__(self,
                 *args,
                 pred_shift_height=False,
                 origin=(0.5, 0.5, 0.5),
                 **kwargs):
        self.pred_shift_height = pred_shift_height
        self.origin = origin
        super().__init__(*args, **kwargs)

    def loss(self, batch_inputs, batch_data_samples):
        raise NotImplementedError

    def predict(self, batch_inputs, batch_data_samples):
        results = []

        for batch_data_sample in batch_data_samples:
            cam2img = batch_data_sample.metainfo['cam2img']
            plane = batch_data_sample.metainfo['plane']
            box_type_3d = batch_data_sample.metainfo['box_type_3d']

            bboxes_3d = batch_data_sample.eval_ann_info['gt_bboxes_3d']
            labels_3d = bboxes_3d.tensor.new_tensor(
                batch_data_sample.eval_ann_info['gt_labels_3d'],
                dtype=torch.long)
            scores_3d = bboxes_3d.tensor.new_ones(labels_3d.shape)

            if self.origin[1] == 0.5:
                centers_2d = points_cam2img(bboxes_3d.gravity_center, cam2img)
            elif self.origin[1] == 1.0:
                centers_2d = points_cam2img(bboxes_3d.bottom_center, cam2img)
            else:
                raise ValueError(f'Unsupported origin {self.origin}')

            shift_height = 0
            if self.pred_shift_height:
                shift_height = plane[3] - bboxes_3d.bottom_height

            bboxes_3d.tensor[:, :3] = points_img2plane(
                centers_2d,
                bboxes_3d.height,
                cam2img,
                plane,
                shift_height,
                origin=self.origin)

            result = InstanceData()
            result.bboxes_3d = box_type_3d(
                bboxes_3d.tensor - EPSILON,
                box_dim=bboxes_3d.box_dim,
                with_yaw=bboxes_3d.with_yaw,
                origin=self.origin)
            result.labels_3d = labels_3d
            result.scores_3d = scores_3d
            results.append(result)

        predictions = self.add_pred_to_datasample(batch_data_samples, results)

        return predictions

    def _forward(self, batch_inputs, batch_data_samples=None):
        raise NotImplementedError

    def extract_feat(self, batch_inputs):
        raise NotImplementedError
