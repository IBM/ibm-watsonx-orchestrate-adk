from enum import Enum


class EnvironmentAuthType(str, Enum):
    IBM_CLOUD_IAM = 'ibm_iam'
    MCSP = 'mcsp'
    MCSP_V1 = 'mcsp_v1'
    MCSP_V2 = 'mcsp_v2'
    CPD = 'cpd'
    EKS = 'eks'
    CNCF = 'cncf'

    @property
    def canonical(self) -> "EnvironmentAuthType":
        """Returns the auth type to use for logic dispatch.
        EKS reuses CPD authentication internally."""
        if self == EnvironmentAuthType.EKS:
            return EnvironmentAuthType.CPD
        return self

    def __str__(self):
        return self.value
