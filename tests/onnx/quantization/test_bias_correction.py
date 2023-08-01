# Copyright (c) 2023 Intel Corporation
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#      http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Dict, List

import numpy as np
import onnx
import pytest
import torch

from nncf.common.factory import NNCFGraphFactory
from nncf.onnx.graph.model_utils import remove_fq_from_inputs
from nncf.onnx.graph.node_utils import get_bias_value
from nncf.quantization.algorithms.bias_correction.onnx_backend import ONNXBiasCorrectionAlgoBackend
from tests.onnx.quantization.common import compare_nncf_graph
from tests.post_training.test_templates.test_bias_correction import TemplateTestBCAlgorithm
from tests.shared.paths import TEST_ROOT


def get_data_from_node(model: onnx.ModelProto, node_name: str):
    data = [t for t in model.graph.initializer if t.name == node_name]
    if data:
        return onnx.numpy_helper.to_array(data[0])
    return None


class TestONNXBCAlgorithm(TemplateTestBCAlgorithm):
    @staticmethod
    def list_to_backend_type(data: List) -> np.ndarray:
        return np.array(data)

    @staticmethod
    def get_backend() -> ONNXBiasCorrectionAlgoBackend:
        return ONNXBiasCorrectionAlgoBackend

    @staticmethod
    def backend_specific_model(model: torch.nn.Module, tmp_dir: str) -> onnx.ModelProto:
        onnx_path = f"{tmp_dir}/model.onnx"
        torch.onnx.export(model, torch.rand(model.INPUT_SIZE), onnx_path, opset_version=13, input_names=["input.1"])
        onnx_model = onnx.load(onnx_path)
        return onnx_model

    @staticmethod
    def fn_to_type(tensor) -> np.ndarray:
        return np.array(tensor)

    @staticmethod
    def get_transform_fn() -> callable:
        def transform_fn(data_item):
            tensor, _ = data_item
            return {"input.1": tensor}

        return transform_fn

    @staticmethod
    def remove_fq_from_inputs(model: onnx.ModelProto) -> onnx.ModelProto:
        return remove_fq_from_inputs(model)

    @staticmethod
    def get_ref_path(suffix: str) -> str:
        return TEST_ROOT / "onnx" / "data" / "reference_graphs" / "quantization" / "subgraphs" / f"{suffix}.dot"

    @staticmethod
    def compare_nncf_graphs(model: onnx.ModelProto, ref_path: str) -> None:
        return compare_nncf_graph(model, ref_path)

    @staticmethod
    def check_bias(model: onnx.ModelProto, ref_biases: Dict) -> None:
        nncf_graph = NNCFGraphFactory.create(model)
        for ref_name, ref_value in ref_biases.items():
            node = nncf_graph.get_node_by_name(ref_name)
            ref_value = np.array(ref_value)
            curr_value = get_bias_value(node, model)
            # TODO(AlexanderDokuchaev): return atol=0.0001 after fix 109189
            assert np.all(np.isclose(curr_value, ref_value, atol=0.01)), f"{curr_value} != {ref_value}"

    @pytest.fixture()
    def quantized_test_model(self, tmpdir) -> onnx.ModelProto:
        pytest.xfail("Skipped until the issue with NNCFGraph builder (ONNX) not fixed.")
        return super().quantized_test_model(tmpdir)
