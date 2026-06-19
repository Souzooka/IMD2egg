from dataclasses import dataclass

@dataclass
class Vec4:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    w: float = 1.0

    def __iter__(self):
        return _VecIter(self)
    
    def __len__(self):
        return 4
    
    def __getitem__(self, key: int) -> float:
        match key:
            case 0:
                return self.x
            case 1:
                return self.y
            case 2:
                return self.z
            case 3:
                return self.w
            case _:
                raise IndexError()

class _VecIter:
    def __init__(self, vec: Vec4) -> None:
        self.__vec = vec
        self.__num = 0
    
    def __next__(self) -> float:
        if self.__num >= len(self.__vec):
            raise StopIteration
        value = self.__vec[self.__num]
        self.__num += 1
        return value


@dataclass
class Color4(Vec4):

    @property
    def r(self):
        return self.x
    @r.setter
    def r(self, value: float):
        self.x = value

    @property
    def g(self):
        return self.y
    @g.setter
    def g(self, value: float):
        self.g = value

    @property
    def b(self):
        return self.z
    @b.setter
    def b(self, value: float):
        self.b = value

    @property
    def a(self):
        return self.w
    @a.setter
    def a(self, value: float):
        self.w = value
    