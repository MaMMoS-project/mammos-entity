from mammos_entity.base import Entity


def Ms(value, unit=None):
    return Entity("SpontaneousMagnetization", value, unit)


def A(value, unit=None):
    return Entity("ExchangeStiffnessConstant", value, unit)


def Ku(value, unit=None):
    return Entity("UniaxialAnisotropyConstant", value, unit)


def H(value, unit=None):
    return Entity("ExternalMagneticField", value, unit)
