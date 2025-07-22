from enum import Enum

class EnvironmentType(str, Enum):
    DRAFT ='draft'
    LIVE = 'live'

    def __str__(self):
        return self.value
    

class ChannelType(str, Enum):
    WEBCHAT ='webchat'

    def __str__(self):
        return self.value


class RuntimeEnvironmentType(str, Enum):
    LOCAL = 'local'
    CPD = 'cpd'
    IBM_CLOUD = 'ibmcloud'
    AWS = 'aws'

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value