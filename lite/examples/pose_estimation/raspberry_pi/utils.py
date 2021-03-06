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
"""Utility functions to display the pose detection results."""

import math
from typing import List, Tuple

import cv2
from data import Person
import numpy as np


# Dictionary that maps from joint names to keypoint indices.
KEYPOINT_DICT = {
    'nose': 0,
    'left_eye': 1,
    'right_eye': 2,
    'left_ear': 3,
    'right_ear': 4,
    'left_shoulder': 5,
    'right_shoulder': 6,
    'left_elbow': 7,
    'right_elbow': 8,
    'left_wrist': 9,
    'right_wrist': 10,
    'left_hip': 11,
    'right_hip': 12,
    'left_knee': 13,
    'right_knee': 14,
    'left_ankle': 15,
    'right_ankle': 16
}

# map edges to a RGB color
KEYPOINT_EDGE_INDS_TO_COLOR = {
    (0, 1): (147, 20, 255),
    (0, 2): (255, 255, 0),
    (1, 3): (147, 20, 255),
    (2, 4): (255, 255, 0),
    (0, 5): (147, 20, 255),
    (0, 6): (255, 255, 0),
    (5, 7): (147, 20, 255),
    (7, 9): (147, 20, 255),
    (6, 8): (255, 255, 0),
    (8, 10): (255, 255, 0),
    (5, 6): (0, 255, 255),
    (5, 11): (147, 20, 255),
    (6, 12): (255, 255, 0),
    (11, 12): (0, 255, 255),
    (11, 13): (147, 20, 255),
    (13, 15): (147, 20, 255),
    (12, 14): (255, 255, 0),
    (14, 16): (255, 255, 0)
}


def draw_landmarks_edges(image,
                         keypoint_locs,
                         keypoint_edges,
                         edge_colors,
                         keypoint_color=(0, 255, 0)):
  """Draw landmarks and edges on the input image and return it."""
  for landmark in keypoint_locs:
    landmark_x = min(landmark[0], image.shape[1] - 1)
    landmark_y = min(landmark[1], image.shape[0] - 1)
    cv2.circle(image, (int(landmark_x), int(landmark_y)), 2, keypoint_color, 4)

  for idx, edge in enumerate(keypoint_edges):
    cv2.line(image, (int(edge[0][0]), int(edge[0][1])),
             (int(edge[1][0]), int(edge[1][1])), edge_colors[idx], 2)

  return image


def keypoints_and_edges_for_display(keypoints_with_scores,
                                    height,
                                    width,
                                    keypoint_threshold=0.11):
  """Returns high confidence keypoints and edges for visualization.

  Args:
      keypoints_with_scores: An numpy array with shape [17, 3] representing the
        keypoint coordinates and scores returned by the MoveNet/PoseNet models.
      height: height of the image in pixels.
      width: width of the image in pixels.
      keypoint_threshold: minimum confidence score for a keypoint to be
        visualized.

  Returns:
      A (keypoints_xy, edges_xy, edge_colors) containing:
      * the coordinates of all keypoints of all detected entities;
      * the coordinates of all skeleton edges of all detected entities;
      * the colors in which the edges should be plotted.
  """
  keypoints_all = []
  keypoint_edges_all = []
  edge_colors = []
  kpts_x = keypoints_with_scores[:, 1]
  kpts_y = keypoints_with_scores[:, 0]
  kpts_scores = keypoints_with_scores[:, 2]
  kpts_absolute_xy = np.stack(
      [width * np.array(kpts_x), height * np.array(kpts_y)], axis=-1)
  kpts_above_thresh_absolute = kpts_absolute_xy[
      kpts_scores > keypoint_threshold]
  keypoints_all.append(kpts_above_thresh_absolute)

  for edge_pair, color in KEYPOINT_EDGE_INDS_TO_COLOR.items():
    if (kpts_scores[edge_pair[0]] > keypoint_threshold and
        kpts_scores[edge_pair[1]] > keypoint_threshold):
      x_start = kpts_absolute_xy[edge_pair[0], 0]
      y_start = kpts_absolute_xy[edge_pair[0], 1]
      x_end = kpts_absolute_xy[edge_pair[1], 0]
      y_end = kpts_absolute_xy[edge_pair[1], 1]
      line_seg = np.array([[x_start, y_start], [x_end, y_end]])
      keypoint_edges_all.append(line_seg)
      edge_colors.append(color)
  if keypoints_all:
    keypoints_xy = np.concatenate(keypoints_all, axis=0)
  else:
    num_instances, _ = keypoints_with_scores.shape
    keypoints_xy = np.zeros((0, num_instances, 2))

  if keypoint_edges_all:
    edges_xy = np.stack(keypoint_edges_all, axis=0)
  else:
    edges_xy = np.zeros((0, 2, 2))

  return keypoints_xy, edges_xy, edge_colors


def visualize(
    image: np.ndarray,
    list_persons: List[Person],
    keypoint_threshold: float = 0.05,
    instance_threshold: float = 0.1,
    keypoint_color: Tuple[int, ...] = (0, 255, 0)
) -> np.ndarray:
  """Draws landmarks and edges on the input image and return it.

  Args:
    image: The input RGB image.
    list_persons: The list of all "Person" entities to be visualize.
    keypoint_threshold: minimum confidence score for a keypoint to be drawn.
    instance_threshold: minimum confidence score for a person to be drawn.
    keypoint_color: the colors in which the landmarks should be plotted.

  Returns:
    Image with keypoints and edges.
  """
  for person in list_persons:
    if person.score < instance_threshold:
      continue

    keypoints = person.keypoints
    bounding_box = person.bounding_box

    # Draw all the landmarks
    for i in range(len(keypoints)):
      if keypoints[i].score >= keypoint_threshold:
        cv2.circle(image, keypoints[i].coordinate, 2, keypoint_color, 4)

    # Draw all the edges
    for edge_pair, color in KEYPOINT_EDGE_INDS_TO_COLOR.items():
      if (keypoints[edge_pair[0]].score > keypoint_threshold and
          keypoints[edge_pair[1]].score > keypoint_threshold):
        cv2.line(image, keypoints[edge_pair[0]].coordinate,
                 keypoints[edge_pair[1]].coordinate, color, 2)

    # Draw bounding_box with multipose
    if bounding_box is not None:
      start_point = bounding_box.start_point
      end_point = bounding_box.end_point
      cv2.rectangle(image, start_point, end_point, keypoint_color, 1)

  return image


def keep_aspect_ratio_resizer(
    image: np.ndarray, target_size: int) -> Tuple[np.ndarray, Tuple[int, int]]:
  """Resizes the image.

  The function resizes the image such that its longer side matches the required
  target_size while keeping the image aspect ratio. Note that the resizes image
  is padded such that both height and width are a multiple of 32, which is
  required by the model. See
  https://tfhub.dev/google/tfjs-model/movenet/multipose/lightning/1 for more
  detail.

  Args:
    image: The input RGB image as a numpy array of shape [height, width, 3].
    target_size: Desired size that the image should be resize to.

  Returns:
    image: The resized image.
    (target_height, target_width): The actual image size after resize.

  """
  height, width, _ = image.shape
  if height > width:
    scale = float(target_size / height)
    target_height = target_size
    scaled_width = math.ceil(width * scale)
    image = cv2.resize(image, (scaled_width, target_height))
    target_width = int(math.ceil(scaled_width / 32) * 32)
  else:
    scale = float(target_size / width)
    target_width = target_size
    scaled_height = math.ceil(height * scale)
    image = cv2.resize(image, (target_width, scaled_height))
    target_height = int(math.ceil(scaled_height / 32) * 32)

  padding_top, padding_left = 0, 0
  padding_bottom = target_height - image.shape[0]
  padding_right = target_width - image.shape[1]
  # add padding to image
  image = cv2.copyMakeBorder(image, padding_top, padding_bottom, padding_left,
                             padding_right, cv2.BORDER_CONSTANT)
  return image, (target_height, target_width)
