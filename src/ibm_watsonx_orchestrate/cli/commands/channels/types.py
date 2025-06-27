from enum import Enum

class  EnvironmentType(str, Enum):
    DRAFT ='draft'
    LIVE = 'live'

    def __str__(self):
        return self.value
    

class  ChannelType(str, Enum):
    WEBCHAT ='webchat'

    def __str__(self):
        return self.value