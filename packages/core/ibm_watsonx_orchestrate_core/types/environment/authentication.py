from enum import Enum


class EnvironmentAuthType(str, Enum):
    IBM_CLOUD_IAM = 'ibm_iam'
    MCSP = 'mcsp'
    MCSP_V1 = 'mcsp_v1'
    MCSP_V2 = 'mcsp_v2'
    CPD = 'cpd'
    K8S = 'k8s'

    @property
    def canonical(self) -> "EnvironmentAuthType":
        """Returns the auth type to use for logic dispatch.
        K8S reuses CPD authentication internally."""
        if self is EnvironmentAuthType.K8S:
            return EnvironmentAuthType.CPD
        return self

    @classmethod
    def is_cpd_like(cls, auth_type: "str | EnvironmentAuthType") -> bool:
        """Returns True if auth_type is CPD or K8S (which reuses CPD auth)."""
        try:
            return cls(auth_type) in {cls.CPD, cls.K8S}
        except ValueError:
            return False

    def __str__(self):
        return self.value

