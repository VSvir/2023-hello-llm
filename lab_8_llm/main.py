"""
Laboratory work.

Working with Large Language Models.
"""
# pylint: disable=too-few-public-methods, undefined-variable, too-many-arguments, super-init-not-called, duplicate-code
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd
import torch
from datasets import load_dataset
from evaluate import load
from pandas import DataFrame
from torch.utils.data import DataLoader, Dataset
from torchinfo import summary
from transformers import GPT2TokenizerFast, GPTNeoForCausalLM

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
        self._raw_data = load_dataset(
            self._hf_name,
            name='generation',
            split='validation'
        ).to_pandas()


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
        lengths = self._raw_data.dropna()['question'].apply(lambda x: len(x))

        return {
            'dataset_number_of_samples': len(self._raw_data),
            'dataset_columns': len(self._raw_data.columns),
            'dataset_duplicates': len(self._raw_data[self._raw_data['question'].duplicated()]),
            'dataset_empty_rows': len(self._raw_data[self._raw_data.isna().any(axis=1)]),
            'dataset_sample_min_len': lengths.min().min(),
            'dataset_sample_max_len': lengths.max().max()
        }

    @report_time
    def transform(self) -> None:
        """
        Apply preprocessing transformations to the raw dataset.
        """
        self._data = self._raw_data.drop(columns=[
            'type',
            'category',
            'correct_answers',
            'incorrect_answers',
            'source'
        ]).rename(columns={'best_answer': ColumnNames.TARGET.value})


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
        return self._data[ColumnNames.QUESTION.value].iloc[index],

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
    _model: torch.nn.Module

    def __init__(
            self,
            model_name: str,
            dataset: TaskDataset,
            max_length: int,
            batch_size: int,
            device: str
    ) -> None:
        """
        Initialize an instance of LLMPipeline.

        Args:
            model_name (str): The name of the pre-trained model
            dataset (TaskDataset): The dataset used
            max_length (int): The maximum length of generated sequence
            batch_size (int): The size of the batch inside DataLoader
            device (str): The device for inference
        """
        self._model_name = model_name
        self._model = GPTNeoForCausalLM.from_pretrained(model_name)
        self._dataset = dataset
        self._device = device
        self._tokenizer = GPT2TokenizerFast.from_pretrained(model_name, padding_side='left')
        self._tokenizer.pad_token = self._tokenizer.eos_token
        self._batch_size = batch_size
        self._max_length = max_length

    def analyze_model(self) -> dict:
        """
        Analyze model computing properties.

        Returns:
            dict: Properties of a model
        """
        if self._model is None:
            return {}

        config = self._model.config
        simulation = torch.ones(1, config.max_position_embeddings, dtype=torch.long)
        info = summary(self._model, input_data=simulation, device=self._device, verbose=0)

        return {
            'input_shape': {'attention_mask': list(info.input_size),
                            'input_ids': list(info.input_size)},
            'embedding_size': config.max_position_embeddings,
            'output_shape': info.summary_list[-1].output_size,
            'num_trainable_params': info.trainable_params,
            'vocab_size': config.vocab_size,
            'size': info.total_param_bytes,
            'max_context_length': config.max_length
        }

    @report_time
    def infer_sample(self, sample: tuple[str, ...], gen_params: dict | None = None) -> str | None:
        """
        Infer model on a single sample.

        Args:
            sample (tuple[str, ...]): The given sample for inference with model
            gen_params (dict | None): Optional parameters dictionary for generation

        Returns:
            str | None: A prediction
        """
        if gen_params is None:
            gen_params = {}
        return None if self._model is None else self._infer_batch((sample, ), gen_params)[0]

    @report_time
    def infer_dataset(self) -> DataFrame:
        """
        Infer model on a whole dataset.

        Returns:
            pd.DataFrame: Data with predictions
        """
        predictions = []
        dataloader = DataLoader(self._dataset, batch_size=self._batch_size)

        for batch in dataloader:
            predictions.extend(self._infer_batch(batch,
                                                 {'repetition_penalty': 2.0,
                                                  'no_repeat_ngram_size': 8}))

        return DataFrame(
            {
                'target': self._dataset.data[ColumnNames.TARGET.value].tolist(),
                'predictions': predictions
            }
        )

    @torch.no_grad()
    def _infer_batch(self,
                     sample_batch: Sequence[tuple[str, ...]],
                     generation_params: dict) -> list[str]:
        """
        Infer model on a single batch.

        Args:
            sample_batch (Sequence[tuple[str, ...]]): Batch to infer the model
            generation_params (dict): a dictionary of parameters to use in generation

        Returns:
            list[str]: Model predictions as strings
        """
        tokens = self._tokenizer(
            sample_batch[0],
            padding=True,
            truncation=True,
            return_tensors='pt'
        )
        outputs = self._model.generate(
            **tokens,
            max_length=self._max_length,
            **generation_params
        )
        generated_texts = self._tokenizer.batch_decode(outputs, skip_special_tokens=True)
        return [
            text.removeprefix(f'{sample_batch[0][i]}\n') for i, text in enumerate(generated_texts)
        ]


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
        self._data_path = data_path
        self._metrics = metrics

    @report_time
    def run(self) -> dict | None:
        """
        Evaluate the predictions against the references using the specified metric.

        Returns:
            dict | None: A dictionary containing information about the calculated metric
        """
        data = pd.read_csv(self._data_path)
        scores = {}

        for metric_name in self._metrics:
            metric = load(metric_name.value)
            score = metric.compute(
                predictions=data[ColumnNames.PREDICTION.value],
                references=data[ColumnNames.TARGET.value]
            )

            if metric_name.value == Metrics.ROUGE.value:
                scores[metric_name.value] = score.get(f'{metric_name.value}L')
            else:
                scores[metric_name.value] = score.get(metric_name.value)

        return scores
