#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------
from __future__ import annotations
from typing import TYPE_CHECKING

import logging
import sys
import re

if TYPE_CHECKING:
    from requests import Response

__all__ = [
    "ClientError",
    "MissingValue",
    "MissingMetaProp",
    "NotUrlNorID",
    "NoCredentialsProvided",
    "ApiRequestFailure",
    "UnexpectedType",
    "ForbiddenActionForPlan",
    "NoVirtualDeploymentSupportedForICP",
    "MissingArgument",
    "WrongEnvironmentVersion",
    "CannotAutogenerateBedrockUrl",
    "WrongMetaProps",
    "CannotSetProjectOrSpace",
    "ForbiddenActionForGitBasedProject",
    "CannotInstallLibrary",
    "DataStreamError",
    "WrongLocationProperty",
    "WrongFileLocation",
    "EmptyDataSource",
    "SpaceIDandProjectIDCannotBeNone",
    "ParamOutOfRange",
    "InvalidMultipleArguments",
    "ValidationError",
    "InvalidValue",
    "PromptVariablesError",
    "UnsupportedOperation",
    "MissingExtension",
    "InvalidCredentialsError",
]


class ClientError(Exception):
    def __init__(
        self,
        error_msg: str,
        reason: str | list | None = None,
        logg_messages: bool = True,
    ):
        # Check if URL contains `internal` or `private` in host part of URL and hide it
        pattern = (
            r"\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)"
            r"(?:[\w.-]*(internal|private)[^\s]*))"
        )
        self.error_msg = re.sub(
            pattern,
            lambda m: f"[{m.group(2).capitalize()} URL]",
            str(error_msg),
            re.IGNORECASE,
        )
        self.reason = reason
        if logg_messages:
            logging.getLogger(__name__).warning(self.__str__())
            logging.getLogger(__name__).debug(
                str(self.error_msg)
                + (
                    "\nReason: " + str(self.reason)
                    if sys.exc_info()[0] is not None
                    else ""
                )
            )

    def __str__(self) -> str:
        return str(self.error_msg) + (
            "\nReason: " + str(self.reason) if self.reason is not None else ""
        )


class MissingValue(ClientError, ValueError):
    def __init__(self, value_name: str, reason: str | None = None):
        ClientError.__init__(self, 'No "' + value_name + '" provided.', reason)


class MissingMetaProp(MissingValue):
    def __init__(self, name: str, reason: str | None = None):
        ClientError.__init__(
            self, "Missing meta_prop with name: '{}'.".format(name), reason
        )


class NotUrlNorID(ClientError, ValueError):
    def __init__(self, value_name: str, value: str, reason: str | None = None):
        ClientError.__init__(
            self,
            "Invalid value of '{}' - it is not url nor id: '{}'".format(
                value_name, value
            ),
            reason,
        )


class NoCredentialsProvided(MissingValue):
    def __init__(self, reason: str | None = None):
        MissingValue.__init__(self, "WML credentials", reason)


class ApiRequestFailure(ClientError):
    def __init__(self, error_msg: str, response: Response, reason: str | None = None):
        self.response = response
        if str(response.status_code) == "404" and "DOCTYPE" in str(response.content):
            raise MissingWMLComponent()

        elif str(
            response.status_code
        ) == "400" and "Invalid content. You cannot include any tags in the HTTP request." in str(
            response.content
        ):
            ClientError.__init__(
                self,
                f"Please check if any parameter that you provided include HTTP tag. "
                f"If yes, please remove it and try again.",
                reason=str(response.content),
            )

        else:
            ClientError.__init__(
                self,
                "{} ({} {})\nStatus code: {}, body: {}".format(
                    error_msg,
                    response.request.method,
                    response.request.url,
                    response.status_code,
                    (
                        response.text
                        if response.apparent_encoding is not None
                        else "[binary content, "
                        + str(len(response.content))
                        + " bytes]"
                    ),
                ),
                reason,
            )


class UnexpectedType(ClientError, ValueError):
    def __init__(self, el_name: str, expected_type: type, actual_type: type):
        ClientError.__init__(
            self,
            "Unexpected type of '{}', expected: {}, actual: '{}'.".format(
                el_name,
                (
                    "'{}'".format(expected_type)
                    if type(expected_type) == type
                    else expected_type
                ),
                actual_type,
            ),
        )


class ForbiddenActionForPlan(ClientError):
    def __init__(self, operation_name: str, expected_plans: list, actual_plan: str):
        ClientError.__init__(
            self,
            "Operation '{}' is available only for {} plan, while this instance has '{}' plan.".format(
                operation_name,
                (
                    (
                        "one of {} as".format(expected_plans)
                        if len(expected_plans) > 1
                        else "'{}'".format(expected_plans[0])
                    )
                    if type(expected_plans) is list
                    else "'{}'".format(expected_plans)
                ),
                actual_plan,
            ),
        )


class NoVirtualDeploymentSupportedForICP(MissingValue):
    def __init__(self, reason: str | None = None):
        MissingValue.__init__(self, "No Virtual deployment supported for ICP", reason)


class MissingArgument(ClientError, ValueError):
    def __init__(self, value_name: str, reason: str | None = None):
        ClientError.__init__(self, f"Argument: {value_name} missing.", reason)


class WrongEnvironmentVersion(ClientError, ValueError):
    def __init__(
        self, used_version: str, environment_name: str, supported_versions: tuple
    ):
        ClientError.__init__(
            self,
            "Version used in credentials not supported in this environment",
            reason=f"Version {used_version} isn't supported in "
            f"{environment_name} environment, "
            f"select from {supported_versions}",
        )


class CannotAutogenerateBedrockUrl(ClientError, ValueError):
    def __init__(self, e1: Exception, e2: Exception):
        ClientError.__init__(
            self,
            "Attempt of generating `bedrock_url` automatically failed. "
            "If iamintegration=True, please provide `bedrock_url` in credentials. "
            "If iamintegration=False, please validate your credentials.",
            reason=[e1, e2],
        )


class WrongMetaProps(MissingValue):
    def __init__(self, reason: str | None = None):
        ClientError.__init__(self, "Wrong metaprops.", reason)


class MissingWMLComponent(ClientError):
    def __init__(self) -> None:
        ClientError.__init__(
            self,
            f"Missing WML Component",
            reason=f"It appears that WML component is not installed on your environment. "
            f"Contact your cluster administrator.",
        )


class CannotSetProjectOrSpace(ClientError):
    def __init__(self, reason: str):
        ClientError.__init__(self, f"Cannot set Project or Space", reason=reason)


class ForbiddenActionForGitBasedProject(ClientError):
    def __init__(self, reason: str):
        ClientError.__init__(
            self, f"This action is not supported for git based project.", reason=reason
        )


class CannotInstallLibrary(ClientError, ValueError):
    def __init__(self, lib_name: str, reason: str):
        ClientError.__init__(
            self,
            f"Library '{lib_name}' cannot be installed! Please install it manually.",
            reason,
        )


class DataStreamError(ClientError, ConnectionError):
    def __init__(self, reason: str):
        ClientError.__init__(
            self, "Cannot fetch data via Flight Service. Try again.", reason
        )


class WrongLocationProperty(ClientError, ConnectionError):
    def __init__(self, reason: str):
        ClientError.__init__(
            self, "Cannot fetch data via Flight Service. Try again.", reason
        )


class WrongFileLocation(ClientError, ValueError):
    def __init__(self, reason: str):
        ClientError.__init__(
            self, "Cannot fetch data via Flight Service. Try again.", reason
        )


class EmptyDataSource(ClientError, ValueError):
    def __init__(self) -> None:
        ClientError.__init__(
            self,
            "Cannot fetch data via Flight Service. "
            "Verify if data were saved under data connection and try again.",
        )


class SpaceIDandProjectIDCannotBeNone(ClientError, ValueError):
    def __init__(self, reason: str):
        ClientError.__init__(self, f"Missing 'space_id' or 'project_id'.", reason)


class ParamOutOfRange(ClientError, ValueError):
    def __init__(
        self, param_name: str, value: int | float, min: int | float, max: int | float
    ):
        ClientError.__init__(
            self,
            f"Value of parameter `{param_name}`, {value}, is out of expected range - between {min} and {max}.",
        )


class InvalidMultipleArguments(ClientError, ValueError):
    def __init__(self, params_names_list: list, reason: str | None = None):
        ClientError.__init__(
            self, f"One of {params_names_list} parameters should be set.", reason
        )


class ValidationError(ClientError, KeyError):
    def __init__(self, key: str, additional_msg: str | None = None):
        msg = (
            f"Invalid prompt template; check for"
            f" mismatched or missing input variables."
            f" Missing input variable: {key}."
        )
        if additional_msg is not None:
            msg += "\n" + additional_msg
        ClientError.__init__(self, msg)


class PromptVariablesError(ClientError, KeyError):
    def __init__(self, key: str):
        ClientError.__init__(
            self,
            (
                f"Prompt template contains input variables."
                f" Missing {key} in `prompt_variables`"
            ),
        )


class InvalidValue(ClientError, ValueError):
    def __init__(self, value_name: str, reason: str | None = None):
        ClientError.__init__(
            self, 'Inappropriate value of "' + value_name + '"', reason
        )


class UnsupportedOperation(ClientError):
    def __init__(self, reason: str):
        ClientError.__init__(
            self, f"Operation is unsupported for this release.", reason
        )


class MissingExtension(ClientError, ImportError):
    def __init__(self, extension_name: str):
        ClientError.__init__(
            self,
            f"Could not import {extension_name}: Please install `{extension_name}` extension.",
        )


class InvalidCredentialsError(ClientError):
    def __init__(self, reason: str | Response, logg_messages: bool = True):
        ClientError.__init__(
            self,
            f"Attempt of authenticating connection to service failed, please validate your credentials. Error: {reason}",
            logg_messages=logg_messages,
        )
