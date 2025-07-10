from .swuniv_dacon import SWUnivDaconDataset, BalancedSWUnivDaconDataset
from torch.utils.data import DataLoader


class BalancedDataLoader(DataLoader):
    """
    DataLoader that balances the dataset by sampling from each class equally.
    """
    def __init__(self, dataset, resample_function=lambda dt: dt.resample(), *args, **kwargs):
        super().__init__(dataset, *args, **kwargs)
        self.dataset = dataset
        self.resample_function = resample_function

    def __iter__(self):
        if self.resample_function is not None:
            self.resample_function(self.dataset)
        return super().__iter__()
