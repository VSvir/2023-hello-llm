"""
Neural machine translation module.
"""
# pylint: disable=too-few-public-methods, undefined-variable, too-many-arguments, super-init-not-called
from collections import namedtuple
from pathlib import Path
from typing import Iterable, Iterator, Sequence

import numpy as np
from datasets import load_dataset
import torchinfo
from transformers import BertForSequenceClassification

try:
    import torch
    from torch.utils.data.dataset import Dataset
except ImportError:
    print('Library "torch" not installed. Failed to import.')
    Dataset = dict
    torch = namedtuple('torch', 'no_grad')(lambda: lambda fn: fn)  # type: ignore

try:
    from pandas import DataFrame
except ImportError:
    print('Library "pandas" not installed. Failed to import.')
    DataFrame = dict  # type: ignore

from core_utils.llm.llm_pipeline import AbstractLLMPipeline
from core_utils.llm.metrics import Metrics
from core_utils.llm.raw_data_importer import AbstractRawDataImporter
from core_utils.llm.raw_data_preprocessor import AbstractRawDataPreprocessor, ColumnNames
from core_utils.llm.task_evaluator import AbstractTaskEvaluator
from core_utils.llm.time_decorator import report_time


class RawDataImporter(AbstractRawDataImporter):
    """
    A class that imports the HuggingFace dataset.
    """

    @report_time
    def obtain(self) -> None:
        """
        Download a dataset.

        Raises:
            TypeError: In case of downloaded dataset is not pd.DataFrame
        """
        self._raw_data = load_dataset(self._hf_name, 'ru', split='validation').to_pandas()


class RawDataPreprocessor(AbstractRawDataPreprocessor):
    """
    A class that analyzes and preprocesses a dataset.
    """

    def analyze(self) -> dict:
        """
        Analyze a dataset.

        Returns:
            dict: Dataset key properties
        """
        info = {
            'dataset_number_of_samples': self._count_samples(),
            'dataset_columns': self._count_columns(),
            'dataset_duplicates': self._count_duplicates(),
            'dataset_empty_rows': self._count_empty(),
            'dataset_sample_min_len': self._count_min(),
            'dataset_sample_max_len': self._count_max()
            }
        return info

    def _count_samples(self):
        """Count number of rows in a DataFrame"""
        return len(self._raw_data)

    def _count_columns(self):
        """Count number of columns in a DataFrame"""
        return self._raw_data.shape[1]

    def _count_duplicates(self):
        """Count number of duplicates in a DataFrame"""
        return self._raw_data.duplicated().sum()

    def _count_empty(self):
        """Count number of empty rows in a DataFrame including those having empty strings"""
        return len(self._raw_data) - len(self._raw_data.replace('', np.nan).dropna())

    def _count_min(self):
        """Count length of the shortest sample"""
        return min(len(min(self._raw_data['premise'], key=len)),
                   len(min(self._raw_data['hypothesis'], key=len)))

    def _count_max(self):
        """Count length of the longest sample"""
        return max(len(max(self._raw_data['premise'], key=len)),
                   len(max(self._raw_data['hypothesis'], key=len)))

    @report_time
    def transform(self) -> None:
        """
        Apply preprocessing transformations to the raw dataset.
        """
        self._data = (self._raw_data
                      .rename(columns={'label': ColumnNames['TARGET'].value})
                      .drop_duplicates()
                      .replace('', np.nan).dropna()
                      .reset_index(drop=True)
                      )


class TaskDataset(Dataset):
    """
    A class that converts pd.DataFrame to Dataset and works with it.
    """

    def __init__(self, data: DataFrame) -> None:
        """
        Initialize an instance of TaskDataset.

        Args:
            data (pandas.DataFrame): Original data
        """
        super().__init__()
        self._data = data

    def __len__(self) -> int:
        """
        Return the number of items in the dataset.

        Returns:
            int: The number of items in the dataset
        """
        return len(self._data)

    def __getitem__(self, index: int) -> tuple[str, ...]:
        """
        Retrieve an item from the dataset by index.

        Args:
            index (int): Index of sample in dataset

        Returns:
            tuple[str, ...]: The item to be received
        """
        return self._data.iloc[index]['premise'], self._data.iloc[index]['hypothesis']

    @property
    def data(self) -> DataFrame:
        """
        Property with access to preprocessed DataFrame.

        Returns:
            pandas.DataFrame: Preprocessed DataFrame
        """
        return self._data


class LLMPipeline(AbstractLLMPipeline):
    """
    A class that initializes a model, analyzes its properties and infers it.
    """

    def __init__(self, model_name: str, dataset: TaskDataset, max_length: int, batch_size: int,
                 device: str) -> None:
        """
        Initialize an instance of LLMPipeline.

        Args:
            model_name (str): The name of the pre-trained model
            dataset (TaskDataset): The dataset used
            max_length (int): The maximum length of generated sequence
            batch_size (int): The size of the batch inside DataLoader
            device (str): The device for inference
        """
        super().__init__(model_name, dataset, max_length, batch_size, device)
        self._model = BertForSequenceClassification.from_pretrained(self._model_name)

    def analyze_model(self) -> dict:
        """
        Analyze model computing properties.

        Returns:
            dict: Properties of a model
        """
        embeddings_length = self._model.config.max_position_embeddings
        ids = torch.ones(self._batch_size, embeddings_length, dtype=torch.long)
        model_summary = self._get_summary(ids)
        input_shape = {
            'input_ids': [ids.shape[0], ids.shape[1]],
            'attention_mask': [ids.shape[0], ids.shape[1]]
        }

        info = {
            'input_shape': input_shape,
            'embedding_size': embeddings_length,
            'output_shape': model_summary.summary_list[-1].output_size,
            'num_trainable_params': model_summary.trainable_params,
            'vocab_size': self._model.config.vocab_size,
            'size': model_summary.total_param_bytes,
            'max_context_length': 'idk where to get it'
        }
        return info

    @report_time
    def infer_sample(self, sample: tuple[str, ...]) -> str | None:
        """
        Infer model on a single sample.

        Args:
            sample (tuple[str, ...]): The given sample for inference with model

        Returns:
            str | None: A prediction
        """

    @report_time
    def infer_dataset(self) -> DataFrame:
        """
        Infer model on a whole dataset.

        Returns:
            pd.DataFrame: Data with predictions
        """

    def _get_summary(self, ids) -> torchinfo.model_statistics.ModelStatistics:
        """
        Get model summary using torchinfo

        Returns:
            torchinfo.model_statistics.ModelStatistics: model summary
        """
        data = {
            'input_ids': ids,
            'attention_mask': ids
        }
        return torchinfo.summary(self._model, input_data=data)

    @torch.no_grad()
    def _infer_batch(self, sample_batch: Sequence[tuple[str, ...]]) -> list[str]:
        """
        Infer model on a single batch.

        Args:
            sample_batch (Sequence[tuple[str, ...]]): Batch to infer the model

        Returns:
            list[str]: Model predictions as strings
        """


class TaskEvaluator(AbstractTaskEvaluator):
    """
    A class that compares prediction quality using the specified metric.
    """

    def __init__(self, data_path: Path, metrics: Iterable[Metrics]) -> None:
        """
        Initialize an instance of Evaluator.

        Args:
            data_path (pathlib.Path): Path to predictions
            metrics (Iterable[Metrics]): List of metrics to check
        """

    @report_time
    def run(self) -> dict | None:
        """
        Evaluate the predictions against the references using the specified metric.

        Returns:
            dict | None: A dictionary containing information about the calculated metric
        """
