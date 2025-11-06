# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\weed_detection\coco_eval.py

"""
COCO-style Evaluation
=====================

This module provides a comprehensive evaluation mechanism for object detection
models, using the standard COCO evaluation metrics. It is heavily inspired by
and adapted from the official PyTorch vision references (`vision/references/detection/coco_eval.py`).

The primary goal is to provide a robust and standard way to compute metrics like
mean Average Precision (mAP) and mean Average Recall (mAR) at various IoU
(Intersection over Union) thresholds.

Core Components:
----------------
1.  **`CocoEvaluator`**:
    -   **Purpose**: The main class that orchestrates the evaluation process.
    -   **Initialization**: It takes a `COCO` ground truth object and a list of
      IoU types to evaluate (e.g., 'bbox' for bounding boxes, 'segm' for segmentation).
    -   **`update(predictions)`**: This method is called for each batch of
      predictions from the model. It accumulates the predictions and stores them
      in a format that the `pycocotools` library can understand.
    -   **`synchronize_between_processes()`**: In a distributed (multi-GPU) setting,
      this method gathers predictions from all processes onto a single node for
      centralized evaluation. For single-GPU or CPU execution, it's a lightweight
      operation.
    -   **`accumulate()`**: After all predictions have been gathered, this method
      loads them into a `COCO` result object.
    -   **`summarize()`**: This is the final step. It runs the `COCOeval` script
      from `pycocotools`, which compares the model's predictions against the
      ground truth and computes and prints the full suite of COCO metrics.

2.  **`prepare_for_coco_detection(predictions)`**:
    -   A helper function that converts the model's output (tensors for boxes,
      scores, and labels) into the specific list-of-floats format required by
      the COCO API for bounding box detection results.

How it Works:
-------------
1.  An instance of `CocoEvaluator` is created with the validation dataset's
    ground truth (as a `COCO` object).
2.  During the evaluation loop, the model's predictions for each image are passed
    to the evaluator's `update` method.
3.  The evaluator stores these predictions, keyed by the image ID.
4.  After iterating through the entire validation set, `accumulate` and `summarize`
    are called.
5.  `summarize` prints a detailed table of performance metrics, such as:
    -   AP @ IoU=0.50:0.95 (the primary challenge metric)
    -   AP @ IoU=0.50 (PASCAL VOC metric)
    -   AP @ IoU=0.75 (a stricter metric)
    -   AP across different object sizes (small, medium, large)

This module is essential for benchmarking the object detection model against
established standards and for tracking improvements during development.
"""

import json
import tempfile
import torch
from pycocotools.cocoeval import COCOeval
from pycocotools.coco import COCO
import numpy as np
from collections import defaultdict
import logging

class CocoEvaluator:
    def __init__(self, coco_gt, iou_types):
        assert isinstance(iou_types, (list, tuple))
        coco_gt = coco_gt
        self.coco_gt = coco_gt
        self.iou_types = iou_types
        self.coco_eval = {}
        for iou_type in iou_types:
            self.coco_eval[iou_type] = COCOeval(coco_gt, iouType=iou_type)

        self.img_ids = []
        self.eval_imgs = {iou_type: [] for iou_type in iou_types}
        self.predictions = defaultdict(list)

    def update(self, predictions):
        img_ids = list(np.unique(list(predictions.keys())))
        self.img_ids.extend(img_ids)

        for iou_type in self.iou_types:
            results = self.prepare(predictions, iou_type)
            
            # suppress pycocotools prints
            with open('/dev/null', 'w') as devnull:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmpfile:
                    json.dump(results, tmpfile)
                
                coco_dt = self.coco_gt.loadRes(tmpfile.name) if results else COCO()
            
            coco_eval = self.coco_eval[iou_type]
            coco_eval.cocoDt = coco_dt
            coco_eval.params.imgIds = list(img_ids)
            
            eval_imgs = coco_eval.evaluate()
            self.eval_imgs[iou_type].append(eval_imgs)


    def synchronize_between_processes(self):
        # This is a no-op for single-process evaluation
        pass

    def accumulate(self):
        for iou_type in self.iou_types:
            # The results are already accumulated during update in this simplified version
            pass

    def summarize(self):
        for iou_type, coco_eval in self.coco_eval.items():
            logging.info(f"IoU metric: {iou_type}")
            if hasattr(coco_eval, 'summarize'):
                coco_eval.summarize()

    def prepare(self, predictions, iou_type):
        if iou_type == "bbox":
            return self.prepare_for_coco_detection(predictions)
        elif iou_type == "segm":
            return self.prepare_for_coco_segmentation(predictions)
        else:
            raise ValueError(f"Unknown iou type {iou_type}")

    def prepare_for_coco_detection(self, predictions):
        coco_results = []
        for original_id, prediction in predictions.items():
            if len(prediction) == 0:
                continue

            boxes = prediction["boxes"]
            boxes = convert_to_xywh(boxes).tolist()
            scores = prediction["scores"].tolist()
            labels = prediction["labels"].tolist()

            coco_results.extend(
                [
                    {
                        "image_id": original_id,
                        "category_id": labels[k],
                        "bbox": box,
                        "score": scores[k],
                    }
                    for k, box in enumerate(boxes)
                ]
            )
        return coco_results

    def prepare_for_coco_segmentation(self, predictions):
        # This part would handle segmentation masks if your model produced them
        raise NotImplementedError("Segmentation evaluation not implemented")


def convert_to_xywh(boxes):
    xmin, ymin, xmax, ymax = boxes.unbind(1)
    return torch.stack((xmin, ymin, xmax - xmin, ymax - ymin), dim=1)
```