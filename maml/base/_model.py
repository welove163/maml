"""
MAML models base classes
"""
from typing import Any, Union, List, Optional
import joblib

import numpy as np

from maml.base import DummyDescriber, BaseDescriber
from maml.utils import get_full_args, to_array


class BaseModel:
    """
    Abstract Base class for a Model. Basically, it usually wraps around a deep
    learning package, e.g., the Sequential Model in Keras, but provides for
    transparent conversion of arbitrary input and outputs.
    """
    def __init__(self, model: Any,
                 describer: Optional[BaseDescriber] = None, **kwargs):
        """
        Args:
            model (Any): ML models, for example, sklearn models or keras models
            describer (BaseDescriber): Describer that converts object into features
        """
        if describer is None:
            describer = DummyDescriber()
        self.describer = describer
        self.model = model

    def fit(self, features: Union[List, np.ndarray],
            targets: Optional[Union[List, np.ndarray]] = None,
            val_features: Optional[Union[List, np.ndarray]] = None,
            val_targets: Optional[Union[List, np.ndarray]] = None,
            **kwargs) -> "BaseModel":
        """
        Args:
            features (list or np.ndarray): Numerical input feature list or
                numpy array with dim (m, n) where m is the number of data and
                n is the feature dimension.
            targets (list or np.ndarray): Numerical output target list, or
                numpy array with dim (m, ).
            val_features (list or np.ndarray): validation features
            val_targets (list or np.ndarray): validation targets

        Returns:
            self
        """
        self.model.fit(features, targets, **kwargs)  # type: ignore
        return self

    def train(self,
              objs: Union[List, np.ndarray],
              targets: Optional[Union[List, np.ndarray]] = None,
              val_objs: Optional[Union[List, np.ndarray]] = None,
              val_targets: Optional[Union[List, np.ndarray]] = None,
              **kwargs) -> "BaseModel":
        """
        Train the models from object, target pairs

        Args:
            objs (list of objects): List of objects
            targets (list): list of float or np.ndarray
            val_objs (list of objects): list of validation objects
            val_targets (list): list of validation targets
            **kwargs:

        Returns: self

        """
        features = to_array(self.describer.fit_transform(objs))
        targets = to_array(targets)

        if (val_objs is None) and (val_targets is not None):
            raise ValueError("training objects are none, but the targets are not")
        if val_objs is not None:
            val_features = to_array(self.describer.transform(val_objs))
            val_targets = to_array(val_targets)
        else:
            val_features = None
            val_targets = None
        return self.fit(features=features,
                        targets=targets,
                        val_features=val_features,
                        val_targets=val_targets, **kwargs)

    def _predict(self, features: np.ndarray, **kwargs) -> np.ndarray:
        """
        Predict the values given a set of inputs based on fitted models.

        Args:
            features (np.ndarray): array-like input features.

        Returns:
            List of output objects.
        """
        return self.model.predict(features, **kwargs)  # type: ignore

    def predict_objs(self, objs: Union[List, np.ndarray]) -> np.ndarray:
        """
        Predict the values given a set of objects. Usually Pymatgen
            Structure objects.
        """
        return self._predict(self.describer.transform(objs))

    def evaluate(self, eval_objs: Union[List, np.ndarray],
                 eval_targets: Union[List, np.ndarray]) -> np.ndarray:
        """
        Evaluate objs, targets

        Args:
            eval_objs (list): objs for evaluation
            eval_targets (list): target list for the corresponding objects
        """

        eval_features = self.describer.transform(eval_objs)
        return self.model.evaluate(to_array(eval_features),  # type: ignore
                                   to_array(eval_targets))


class SklearnMixin:
    """
    Sklearn models save and load functionality
    """
    def save(self, filename: str):
        """Save the models and describers

        Arguments:
            filename (str): filename for save
        """
        joblib.dump({"models": self.model,
                     "describers": self.describer}, filename)

    def load(self, filename: str):
        """
        Load models parameters from filename
        Args:
            filename (str): models file name

        Returns: None

        """
        m = joblib.load(filename)
        self.model = m["models"]
        self.describer = m["describers"]

    @classmethod
    def from_file(cls, filename: str, **kwargs):
        """
        Load the models from file
        Args:
            filename (str): filename
            **kwargs:

        Returns: object instance

        """
        instance = cls(**kwargs)  # type: ignore
        instance.load(filename)
        return instance


class KerasMixin:
    """
    keras models mixin with save and load functionality
    """
    def save(self, filename: str):
        """Save the models and describers

        Arguments:
            filename (str): filename for save
        """
        joblib.dump(self.describer, filename)
        self.model.save(filename + '.hdf5')

    def load(self, filename: str):
        """
        Load models parameters from filename
        Args:
            filename (str): models file name

        Returns: None

        """
        import tensorflow as tf
        self.describer = joblib.load(filename)
        self.model = tf.keras.models.load_model(filename + '.hdf5')

    @classmethod
    def from_file(cls, filename: str, **kwargs):
        """
        Load the models from file
        Args:
            filename (str): filename
            **kwargs:

        Returns: object instance

        """
        instance = cls(**kwargs)  # type: ignore
        instance.load(filename)
        return instance

    @staticmethod
    def get_input_dim(describer: Optional[BaseDescriber] = None,
                      input_dim: Optional[int] = None) -> Union[int, None]:
        """
        Get feature dimension/input_dim from describers or input_dim

        Args:
            describer (Describer): describers
            input_dim (int): optional input dim int
        """
        if input_dim is not None:
            feature_size: Union[int, None] = input_dim
        elif describer is not None:
            feature_size = describer.feature_dim
        else:
            feature_size = None
        return feature_size


class SKLModel(BaseModel, SklearnMixin):
    """MAML models with sklearn models as estimator
    """
    def __init__(self, model: Any,
                 describer: Optional[BaseDescriber] = None, **kwargs):
        """
        Args:
            model (Any): ML models, for example, sklearn models or keras models
            describer (BaseDescriber): Describer that converts object into features
        """
        super().__init__(model=model, describer=describer, **kwargs)


class KerasModel(BaseModel, KerasMixin):
    """MAML models with keras models as estimators
    """
    def __init__(self, model: Any,
                 describer: Optional[BaseDescriber] = None, **kwargs):
        """
        Args:
            model (Any): ML models, for example, sklearn models or keras models
            describer (BaseDescriber): Describer that converts object into features
        """
        super().__init__(model=model, describer=describer, **kwargs)

    def fit(self, features: Union[List, np.ndarray],
            targets: Optional[Union[List, np.ndarray]] = None,
            val_features: Optional[Union[List, np.ndarray]] = None,
            val_targets: Optional[Union[List, np.ndarray]] = None,
            **kwargs) -> "BaseModel":
        """
        Args:
            features (list or np.ndarray): Numerical input feature list or
                numpy array with dim (m, n) where m is the number of data and
                n is the feature dimension.
            targets (list or np.ndarray): Numerical output target list, or
                numpy array with dim (m, ).
            val_features (list or np.ndarray): validation features
            val_targets (list or np.ndarray): validation targets

        Returns:
            self
        """
        if (val_features is None) and (val_targets is not None):
            raise ValueError("Validation data incorrect")

        fit_args = get_full_args(self.model.fit)  # type: ignore

        # construct validation data for keras models
        val_kwargs = {}
        kw_remove = []
        for kw in kwargs:
            if kw not in fit_args:
                val_kwargs.update({kw: kwargs.get(kw)})
                kw_remove.append(kw)

        for kw in kw_remove:
            kwargs.pop(kw)

        if val_features is not None:
            validation_data = self._get_validation_data(val_features, val_targets, **val_kwargs)
        else:
            validation_data = None
        self.model.fit(features, targets, validation_data=validation_data, **kwargs)  # type: ignore
        return self

    def _get_validation_data(self, val_features, val_targets, **val_kwargs):
        """
        construct validation data, the default is just returning a list of
        val_features and val_targets
        """
        return [val_features, val_targets]
