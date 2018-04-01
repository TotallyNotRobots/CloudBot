from abc import abstractmethod, ABC


class BaseHook(ABC):
    """
    :type function: function
    :type kwargs: dict[str, unknown]
    """

    def __init__(self, function):
        """
        :type function: function
        """
        self.function = function
        self.kwargs = {}

        self._setup()

    def _setup(self):
        pass

    def _add_hook(self, kwargs):
        """
        :type kwargs: dict[str, unknown]
        """
        # update kwargs, overwriting duplicates
        self.kwargs.update(kwargs)

    @classmethod
    @abstractmethod
    def get_type(cls):
        raise NotImplementedError

    @property
    def type(self):
        return self.get_type().type

    def make_full_hook(self, plugin):
        return self.get_type().full_hook(self, plugin)
