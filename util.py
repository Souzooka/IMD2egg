from dataclasses import dataclass

@dataclass
class Vec4:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    w: float = 1.0

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
    