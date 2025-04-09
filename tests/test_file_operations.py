"""Tests for file operation functionality."""

import os
import sys
import pytest
import json
from unittest.mock import patch

# Import the server module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Updated import to get functions directly from utils
from server.utils.file_operations import (
    read_file,
    write_file,
    create_directory,
    list_directory,
    move_file,
    search_files,
    get_file_info
)
# import server # No longer needed


def test_read_file(sample_text_file):
    """Test reading file contents."""
    # Test with a valid file
    result = read_file(sample_text_file)
    
    # Verify result
    assert result["success"] is True
    assert "This is a sample test file." in result["content"]
    assert "Third line." in result["content"]
    assert result["size"] > 0
    
    # Test with a non-existent file
    result = read_file("/path/to/nonexistent/file")
    assert result["success"] is False
    assert "error" in result


def test_read_file_max_size(temp_dir):
    """Test file size limit when reading files."""
    # Create a large file
    large_file_path = os.path.join(temp_dir, "large.txt")
    with open(large_file_path, "w") as f:
        # Write ~1MB of data
        f.write("x" * 1_000_000)
    
    # Test with a small size limit (100KB)
    result = read_file(large_file_path, max_size_mb=0.1)
    
    # Should fail due to size limit
    assert result["success"] is False
    assert "size limit" in result["error"].lower()
    
    # Test with a larger size limit (2MB)
    result = read_file(large_file_path, max_size_mb=2)
    
    # Should succeed
    assert result["success"] is True
    assert len(result["content"]) > 0


def test_write_file(temp_dir):
    """Test writing content to a file."""
    test_file_path = os.path.join(temp_dir, "test_write.txt")
    test_content = "Hello, this is a test file content.\nSecond line."
    
    # Write to file
    result = write_file(test_file_path, test_content)
    
    # Verify result
    assert result["success"] is True
    assert os.path.exists(test_file_path)
    
    # Verify file content
    with open(test_file_path, "r") as f:
        content = f.read()
        assert content == test_content


def test_write_file_create_dirs(temp_dir):
    """Test writing to a file with directory creation."""
    nested_file_path = os.path.join(temp_dir, "nested", "dir", "test.txt")
    test_content = "File in nested directory."
    
    # Write to file with directory creation
    result = write_file(nested_file_path, test_content, create_dirs=True)
    
    # Verify result
    assert result["success"] is True
    assert os.path.exists(nested_file_path)
    
    # Verify file content
    with open(nested_file_path, "r") as f:
        content = f.read()
        assert content == test_content


def test_create_directory(temp_dir):
    """Test creating a directory."""
    new_dir_path = os.path.join(temp_dir, "new_directory")
    
    # Create directory
    result = create_directory(new_dir_path)
    
    # Verify result
    assert result["success"] is True
    assert os.path.exists(new_dir_path)
    assert os.path.isdir(new_dir_path)
    
    # Test creating a directory that already exists
    result = create_directory(new_dir_path)
    assert result["success"] is False  # Should fail
    
    # Test creating a nested directory
    nested_dir_path = os.path.join(temp_dir, "nested", "directory")
    result = create_directory(nested_dir_path)
    assert result["success"] is True
    assert os.path.exists(nested_dir_path)


def test_list_directory(temp_dir):
    """Test listing directory contents."""
    # Create some test files and directories
    os.mkdir(os.path.join(temp_dir, "test_dir"))
    with open(os.path.join(temp_dir, "test1.txt"), "w") as f:
        f.write("Test file 1")
    with open(os.path.join(temp_dir, "test2.txt"), "w") as f:
        f.write("Test file 2")
    with open(os.path.join(temp_dir, ".hidden"), "w") as f:
        f.write("Hidden file")
    
    # List directory without showing hidden files
    result = list_directory(temp_dir, show_hidden=False)
    
    # Verify result
    assert result["success"] is True
    assert len(result["contents"]) == 3  # test_dir, test1.txt, test2.txt
    assert not any(item["name"] == ".hidden" for item in result["contents"])
    
    # List directory showing hidden files
    result = list_directory(temp_dir, show_hidden=True)
    
    # Verify result
    assert result["success"] is True
    assert len(result["contents"]) == 4  # test_dir, test1.txt, test2.txt, .hidden
    assert any(item["name"] == ".hidden" for item in result["contents"])
    
    # Verify directory info
    dir_item = next(item for item in result["contents"] if item["name"] == "test_dir")
    assert dir_item["type"] == "directory"
    
    # Verify file info
    file_item = next(item for item in result["contents"] if item["name"] == "test1.txt")
    assert file_item["type"] == "file"
    assert file_item["size"] > 0


def test_move_file(temp_dir):
    """Test moving/renaming a file."""
    # Create a test file
    source_path = os.path.join(temp_dir, "source.txt")
    with open(source_path, "w") as f:
        f.write("Test file content")
    
    # Move the file
    destination_path = os.path.join(temp_dir, "destination.txt")
    result = move_file(source_path, destination_path)
    
    # Verify result
    assert result["success"] is True
    assert not os.path.exists(source_path)
    assert os.path.exists(destination_path)
    
    # Verify file content
    with open(destination_path, "r") as f:
        content = f.read()
        assert content == "Test file content"
    
    # Test moving a non-existent file
    result = move_file("/path/to/nonexistent/file", destination_path)
    assert result["success"] is False


def test_search_files(temp_dir):
    """Test searching for files matching a pattern."""
    # Create test files
    os.makedirs(os.path.join(temp_dir, "subdir"))
    files = [
        "test1.txt",
        "test2.log",
        "hello.txt",
        "subdir/nested.txt",
        "subdir/data.csv"
    ]
    
    for file_path in files:
        full_path = os.path.join(temp_dir, file_path)
        with open(full_path, "w") as f:
            f.write(f"Content of {file_path}")
    
    # Search for .txt files
    result = search_files(temp_dir, "*.txt", recursive=True)
    
    # Verify result
    assert result["success"] is True
    assert len(result["matches"]) == 3  # test1.txt, hello.txt, subdir/nested.txt
    
    # Search with non-recursive
    result = search_files(temp_dir, "*.txt", recursive=False)
    
    # Verify result - should only find files in the top directory
    assert result["success"] is True
    assert len(result["matches"]) == 2  # test1.txt, hello.txt
    
    # Search with limited results
    result = search_files(temp_dir, "*.*", recursive=True, max_results=2)
    
    # Verify result - should be limited to 2 results
    assert result["success"] is True
    assert len(result["matches"]) == 2


def test_get_file_info(sample_text_file):
    """Test getting file information."""
    # Get info for a regular file
    result = get_file_info(sample_text_file)
    
    # Verify result
    assert result["success"] is True
    assert result["exists"] is True
    assert result["type"] == "file"
    assert result["size"] > 0
    assert "modified" in result
    assert "permissions" in result
    
    # Get info for a directory
    dir_path = os.path.dirname(sample_text_file)
    result = get_file_info(dir_path)
    
    # Verify result
    assert result["success"] is True
    assert result["exists"] is True
    assert result["type"] == "directory"
    
    # Get info for a non-existent file
    result = get_file_info("/path/to/nonexistent/file")
    
    # Verify result
    assert result["success"] is True  # The operation succeeded even though file doesn't exist
    assert result["exists"] is False 