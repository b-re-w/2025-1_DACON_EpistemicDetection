from pathlib import Path
import os

from tqdm.auto import tqdm
import pandas as pd

from torch.utils.data import Dataset
from torchvision.datasets.utils import download_url, extract_archive
from torchvision import datasets
datasets.utils.tqdm = tqdm

from sklearn.model_selection import train_test_split as train_val_split


class SWUnivDaconDataset(Dataset):
    """
    SWUnivDaconDataset for the 2025 SW-University Dacon AI competition.

    Dataset Info.
        train.csv [파일] - 학습 데이터
        title : 글의 제목
        full_text : 전체 글(Text)
        generated : 해당 글이 AI로 생성되었는 지의 유무 (0 : 사람이 작성, 1 : 생성 AI가 작성)

        test.csv [파일] - 평가 데이터
        ID : 평가 샘플 고유 식별자
        title : 글의 제목
        paragraph_index : 글을 구성하는 문단의 번호(순서)
        paragraph_text : 문단(Text)

        sample_submission.csv [파일] - 제출 양식
        ID : 평가 샘플 고유 식별자
        generated : 해당 글이 AI로 생성되었을 확률 (0~1)

    ※ Training data was sourced from the 2022 Korean Wikipedia dump (Wikimedia Foundation), licensed under CC BY-SA 3.0.

    :ref: https://dacon.io/competitions/official/236473/overview/description
    """
    classes = ("Human", "AI")
    dataset_name = "swuniv_dacon"
    download_url = "https://cfiles.dacon.co.kr/competitions/236473/open.zip"
    filename = "swuniv_dacon.zip"
    train_file = "train.csv"
    augmented_file = "augmented.csv"
    test_file = "test.csv"
    submission_file = "sample_submission.csv"
    random_state = 42

    def __init__(self, root: str, force_download: bool = False, train: bool = True, valid: bool = False, valid_ratio: float = 0.2):
        self._download(root, force=force_download)

        self.root = Path(root)
        self.is_train = train
        self.is_valid = valid
        self.data_file = ""

        self.data, self.labels, self.raw = self._load_data(valid_ratio=valid_ratio)

    @classmethod
    def _download(cls, root: str, force: bool = False):
        root = Path(root)
        dataset_dir = root / cls.dataset_name
        if not dataset_dir.exists() or force:
            print(f"INFO: Downloading '{cls.dataset_name}' dataset from {cls.download_url} to {root}...")
            download_url(cls.download_url, root, filename=cls.filename, md5=None)
            extract_archive(root / cls.filename, dataset_dir)
        else:
            print(f"INFO: Dataset '{cls.dataset_name}' already exists at {root}. Skipping download.")

    def _load_data(self, valid_ratio=0.2, seed=None):
        if seed is None:
            seed = self.random_state

        if self.is_train:
            if valid_ratio == 0:
                self.data_file = self.train_file
            else:
                # load train data
                data_files = pd.read_csv(self.root / self.dataset_name / self.train_file, encoding='utf-8-sig')

                # train/valid split
                data, label, raw = data_files['full_text'], data_files['generated'], data_files
                seperated = train_val_split(range(len(data)), label, stratify=label, test_size=valid_ratio, random_state=seed)

                # save seperated data
                train_raw, valid_raw = raw.iloc[seperated[0]], raw.iloc[seperated[1]]
                train_file = self.train_file.replace("train", f"train_{1-valid_ratio:.2f}")
                valid_file = self.train_file.replace("train", f"valid_{valid_ratio:.2f}")
                train_raw.to_csv(self.root / self.dataset_name / train_file, index=False)
                valid_raw.to_csv(self.root / self.dataset_name / valid_file, index=False)
                self.data_file = valid_file if self.is_valid else train_file
        else:
            self.data_file = self.test_file

        data_files = pd.read_csv(self.root / self.dataset_name / self.data_file, encoding='utf-8-sig')
        if self.is_train:
            return data_files['full_text'].tolist(), data_files['generated'].tolist(), data_files
        else:
            return data_files['paragraph_text'].tolist(), [], data_files

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        return self.data[idx], (self.labels[idx] if self.is_train else -1)


class BalancedSWUnivDaconDataset(SWUnivDaconDataset):
    def __init__(self, root: str, force_download: bool = False, train: bool = True, valid: bool = False, valid_ratio: float = 0.2, balancing_ratio: float = 1.0):
        self.balancing_ratio = balancing_ratio
        super().__init__(root, force_download, train, valid, valid_ratio)

    def _load_data(self, valid_ratio=0.2, seed=None):
        if seed is None:
            seed = self.random_state

        data, labels, raw = super()._load_data(valid_ratio=valid_ratio, seed=seed)

        if self.is_train:
            ai_count = len(raw[raw['generated'] == 1])
            humans = raw[raw['generated'] == 0].sample(n=ai_count * self.balancing_ratio, random_state=seed)
            raw = pd.concat([humans, raw[raw['generated'] == 1]], ignore_index=False)
            return raw['full_text'].tolist(), raw['generated'].tolist(), raw
        else:
            return data, labels, raw


class AugmentedSWUnivDaconDataset(SWUnivDaconDataset):
    train_file = SWUnivDaconDataset.augmented_file

    def __init__(self, root: str, force_download: bool = False, train: bool = True, valid: bool = False, valid_ratio: float = 0.2, return_original: bool = False):
        self._download(root, force=force_download)

        self.root = Path(root)
        self.is_train = train
        self.is_valid = valid
        self.data_file = ""
        self.return_original = return_original

        self.data, self.original, self.labels, self.raw = self._load_data(valid_ratio=valid_ratio)

    def _load_data(self, valid_ratio=0.2, seed=None):
        if seed is None:
            seed = self.random_state

        if not os.path.exists(self.root / self.dataset_name / self.augmented_file):
            if os.path.exists(self.root / "../" / self.augmented_file):
                os.rename(self.root / "../" / self.augmented_file, self.root / self.dataset_name / self.augmented_file)
            else:
                raise FileNotFoundError(f"Augmented data file '{self.augmented_file}' not found at {self.root}. Please run augmentation.ipynb first.")

        data, labels, raw = super()._load_data(valid_ratio=valid_ratio, seed=seed)

        if self.is_train:
            return raw['paraphrased_text'].tolist(), data, labels, raw
        else:
            return data, None, labels, raw

    def __getitem__(self, idx):
        if self.return_original and self.is_train:
            return self.data[idx], self.original[idx], self.labels[idx]
        return self.data[idx], (self.labels[idx] if self.is_train else -1)
