"""
Mock neodo_common module to satisfy imports.

This provides placeholder implementations for types imported in server/neodo/main.py
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional


# Command execution related types
@dataclass
class ExecuteCommandRequest:
    command: str
    timeout: Optional[float] = 30.0
    working_directory: Optional[str] = None
    environment: Optional[Dict[str, str]] = None


@dataclass
class ExecuteCommandResponse:
    output: str
    exit_code: int
    error: Optional[str] = None


# File system related types
@dataclass
class CheckFileExistenceRequest:
    path: str


@dataclass
class CheckFileExistenceResponse:
    exists: bool
    is_file: Optional[bool] = None
    is_directory: Optional[bool] = None


@dataclass
class CreateFileRequest:
    path: str
    content: Optional[str] = None
    permissions: Optional[int] = None
    create_parents: Optional[bool] = False


@dataclass
class CreateFileResponse:
    success: bool
    path: str
    error: Optional[str] = None


@dataclass
class ReadFileRequest:
    path: str
    max_size_bytes: Optional[int] = None
    encoding: Optional[str] = "utf-8"


@dataclass
class ReadFileResponse:
    content: str
    size_bytes: int
    encoding: str
    error: Optional[str] = None


@dataclass
class UpdateFileRequest:
    path: str
    content: str
    create_if_missing: Optional[bool] = False
    encoding: Optional[str] = "utf-8"


@dataclass
class UpdateFileResponse:
    success: bool
    path: str
    error: Optional[str] = None


@dataclass
class DeleteFileRequest:
    path: str
    force: Optional[bool] = False


@dataclass
class DeleteFileResponse:
    success: bool
    path: str
    error: Optional[str] = None


@dataclass
class ListDirectoryRequest:
    path: str
    recursive: Optional[bool] = False
    include_hidden: Optional[bool] = False
    pattern: Optional[str] = None


@dataclass
class ListDirectoryResponse:
    path: str
    entries: List[Dict[str, Any]]
    error: Optional[str] = None


@dataclass
class GetFileMetadataRequest:
    path: str


@dataclass
class GetFileMetadataResponse:
    path: str
    metadata: Dict[str, Any]
    error: Optional[str] = None


@dataclass
class ChangePermissionsRequest:
    path: str
    permissions: int
    recursive: Optional[bool] = False


@dataclass
class ChangePermissionsResponse:
    success: bool
    path: str
    error: Optional[str] = None


@dataclass
class CreateDirectoryRequest:
    path: str
    parents: Optional[bool] = True
    permissions: Optional[int] = None


@dataclass
class CreateDirectoryResponse:
    success: bool
    path: str
    error: Optional[str] = None


@dataclass
class SearchFilesRequest:
    directory: str
    pattern: str
    recursive: Optional[bool] = True
    max_results: Optional[int] = 100
    include_hidden: Optional[bool] = False


@dataclass
class SearchFilesResponse:
    matches: List[str]
    total_matches: int
    error: Optional[str] = None


@dataclass
class ExecuteScriptRequest:
    path: str
    arguments: Optional[List[str]] = None
    timeout: Optional[float] = 30.0
    working_directory: Optional[str] = None
    environment: Optional[Dict[str, str]] = None


@dataclass
class ExecuteScriptResponse:
    output: str
    exit_code: int
    error: Optional[str] = None 