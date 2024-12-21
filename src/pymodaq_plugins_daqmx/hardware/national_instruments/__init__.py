from aenum import extend_enum
from types import MethodType
from nidaqmx.constants import UsageTypeAI, Edge, TerminalConfiguration, ThermocoupleType


def members(classref):
    """
    Return the list of the members of cls.__members__.items()
    """
    return list(classref._member_map_.values())


def names(classref):
    """
    Return the list of the names of the enum members
    """
    return classref._member_names_


extend_enum(UsageTypeAI, "Thermocouple", UsageTypeAI.TEMPERATURE_THERMOCOUPLE.value)


extend_enum(TerminalConfiguration, "Auto", TerminalConfiguration.DEFAULT.value)


UsageTypeAI.members = MethodType(members, UsageTypeAI)


UsageTypeAI.names = MethodType(names, UsageTypeAI)


Edge.members = MethodType(members, Edge)


Edge.names = MethodType(names, Edge)


TerminalConfiguration.members = MethodType(members, TerminalConfiguration)


TerminalConfiguration.names = MethodType(names, TerminalConfiguration)


ThermocoupleType.members = MethodType(members, ThermocoupleType)


ThermocoupleType.names = MethodType(names, ThermocoupleType)
