from enum import Enum


class EnvironmentAuthType(str, Enum):
    IBM_CLOUD_IAM = 'ibm_iam'
    MCSP = 'mcsp'
    MCSP_V1 = 'mcsp_v1'
    MCSP_V2 = 'mcsp_v2'
    CPD = 'cpd'

    def __str__(self):
        return self.value
