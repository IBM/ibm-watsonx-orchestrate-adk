from enum import Enum


class EnvironmentAuthType(str, Enum):
    IBM_CLOUD_IAM = 'ibm_iam'
    MCSP = 'mcsp'

    def __str__(self):
        return self.value