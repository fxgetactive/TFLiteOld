# Copyright 2021 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Code to run a TFLite pose classification model."""
import os
import numpy as np

# pylint: disable=g-import-not-at-top
try:
  # Import TFLite interpreter from tflite_runtime package if it's available.
  from tflite_runtime.interpreter import Interpreter
except ImportError:
  # If not, fallback to use the TFLite interpreter from the full TF package.
  import tensorflow as tf
  Interpreter = tf.lite.Interpreter
# pylint: enable=g-import-not-at-top


class Classifier(object):
  """A wrapper class for a TFLite pose classification model."""

  def __init__(self, model_name, label_file, score_threshold=0.1):
    """Initialize a pose classification model.

    Args:
      model_name: Name of the TFLite pose classification model.
      label_file: Path of the label list file.
      score_threshold: The minimum keypoint score to run classification.
    """

    # Append TFLITE extension to model_name if there's no extension
    _, ext = os.path.splitext(model_name)
    if not ext:
      model_name += '.tflite'

    # Initialize model
    interpreter = Interpreter(model_path=model_name, num_threads=4)
    interpreter.allocate_tensors()

    self._input_index = interpreter.get_input_details()[0]['index']
    self._output_index = interpreter.get_output_details()[0]['index']
    self._interpreter = interpreter

    self.pose_class_names = self._load_labels(label_file)
    self.score_threshold = score_threshold

  def _load_labels(self, label_path):
    """Load label list from file.

    Args:
      label_path: Full path of label file.

    Returns:
      An array contains the list of labels.
    """
    with open(label_path, 'r') as f:
      return [line.strip() for _, line in enumerate(f.readlines())]

  def classify_pose(self, keypoints_and_scores):
    """Run classification on an input.

    Args:
      keypoints_and_scores: A list of coordinates and scores of 17 COCO
        keypoints. Shape: (17, 3). You can pass the output of Posenet#detect()
        and Movenet#detect() here.

    Returns:
      A list of prediction result in the (class_name, probability) format.
      Sorted by probability descendingly.
    """
    # Check if keypoints are all detected before running the classifier.
    # If there's a keypoint below the threshold, return zero probability for all
    # class.
    min_score = np.amin(keypoints_and_scores[:, 2])
    if min_score < self.score_threshold:
      return [(class_name, 0) for class_name in self.pose_class_names]

    # Flatten the input and add an extra dimension to match with the requirement
    # of the TFLite model.
    input_tensor = keypoints_and_scores.flatten().astype(np.float32)
    input_tensor = np.expand_dims(input_tensor, axis=0)

    # Set the input and run inference
    self._interpreter.set_tensor(self._input_index, input_tensor)
    self._interpreter.invoke()

    # Extract the output and squeeze the batch dimension
    output = self._interpreter.get_tensor(self._output_index)
    output = np.squeeze(output, axis=0)

    # Sort output by probability descendingly
    prob_descending = sorted(
        range(len(output)), key=lambda k: output[k], reverse=True)
    prob_list = [
        (self.pose_class_names[idx], output[idx]) for idx in prob_descending
    ]

    return prob_list
