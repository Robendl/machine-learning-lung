import numpy as np
from sklearn.model_selection import GridSearchCV, KFold
from sklearn.base import BaseEstimator, ClassifierMixin
from network import UnetWithHeader
from unet import bce_loss, dice_loss, combined_loss

from unet import train
from test import test


class PyTorchWrapper(BaseEstimator, ClassifierMixin):
    def __init__(self, learning_rate, mode, loss_function):
        # Initialize your wrapper with hyperparameters
        self.model = UnetWithHeader(n_channels=3, n_classes=1, mode=mode)
        self.model.cuda()
        self.mode = mode
        self.learning_rate = learning_rate
        self.loss_function = loss_function
        self.path = "brain_tumour/train"

    def fit(self, X, y):
        num_epochs = 25
        print(self.learning_rate, self.loss_function.__name__, self.mode)
        train(self.model, X, learning_rate=self.learning_rate, loss_function=self.loss_function, num_epochs=num_epochs)

    def score(self, X, y, sample_weight=None):
        return test(self.model, X, self.path)


def gridsearch():
    # Create a hyperparameter grid to search
    param_grid = {
        'learning_rate': [0.001, 0.0001, 0.00001],
        'loss_function': [bce_loss, dice_loss, combined_loss]
    }

    # Create an instance of the PyTorch wrapper
    pytorch_wrapper = PyTorchWrapper(0.001, "mlp", bce_loss)

    # Use GridSearchCV with your PyTorch wrapper
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    grid_search = GridSearchCV(pytorch_wrapper, param_grid, cv=kf)

    total_images = 2757
    indices = np.arange(0, total_images)
    np.random.shuffle(indices)
    data_used = 2757
    indices = indices[:data_used]
    train_size = int(data_used * 0.9)
    train_indices = indices[:train_size]
    test_indices = indices[train_size:]

    grid_search.fit(train_indices, train_indices)

    # Access the best hyperparameters
    best_hyperparameters = grid_search.best_params_
    print(best_hyperparameters)

    best_model = grid_search.best_estimator_

    test_score = best_model.score(test_indices, test_indices)
    print("Best test score:", test_score)


if __name__ == '__main__':
    gridsearch()
