from typing import NamedTuple
class TimeoutConfig(NamedTuple):
    connect: float
    read: float
    @property
    def total(self): return self.connect + self.read
    @classmethod
    def default(cls): return cls(5.0, 10.0)
