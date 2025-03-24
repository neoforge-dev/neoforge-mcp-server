import os
import tempfile
import shutil
import sys
import json

# Import the server module
import server

def test_read_file():
    """Test reading file contents."""
    # Create a temporary directory and file
    temp_dir = tempfile.mkdtemp()
    try:
        # Create a sample file
        sample_file = os.path.join(temp_dir, "sample.txt")
        with open(sample_file, "w") as f:
            f.write("This is a sample test file.\nIt has multiple lines.\nThird line.")
        
        # Test with a valid file
        result = server.read_file(sample_file)
        print(f"Read file result: {result}")
        
        assert result["success"] is True
        assert "This is a sample test file." in result["content"]
        assert "Third line." in result["content"]
        assert result["size"] > 0
        
        # Test with a non-existent file
        result = server.read_file("/path/to/nonexistent/file")
        print(f"Read non-existent file result: {result}")
        assert result["success"] is False
        assert "error" in result
        
        print("read_file test passed!")
    finally:
        # Clean up
        shutil.rmtree(temp_dir)

def test_write_file():
    """Test writing content to a file."""
    temp_dir = tempfile.mkdtemp()
    try:
        test_file_path = os.path.join(temp_dir, "test_write.txt")
        test_content = "Hello, this is a test file content.\nSecond line."
        
        # Write to file
        result = server.write_file(test_file_path, test_content)
        print(f"Write file result: {result}")
        
        # Verify result
        assert result["success"] is True
        assert os.path.exists(test_file_path)
        
        # Verify file content
        with open(test_file_path, "r") as f:
            content = f.read()
            assert content == test_content
        
        print("write_file test passed!")
    finally:
        # Clean up
        shutil.rmtree(temp_dir)

def test_create_directory():
    """Test creating a directory."""
    temp_dir = tempfile.mkdtemp()
    try:
        new_dir_path = os.path.join(temp_dir, "new_directory")
        
        # Create directory
        result = server.create_directory(new_dir_path)
        print(f"Create directory result: {result}")
        
        # Verify result
        assert result["success"] is True
        assert os.path.exists(new_dir_path)
        assert os.path.isdir(new_dir_path)
        
        # Test creating a directory that already exists
        result = server.create_directory(new_dir_path)
        print(f"Create existing directory result: {result}")
        assert result["success"] is False  # Should fail
        
        print("create_directory test passed!")
    finally:
        # Clean up
        shutil.rmtree(temp_dir)

def test_list_directory():
    """Test listing directory contents."""
    temp_dir = tempfile.mkdtemp()
    try:
        # Create some test files and directories
        os.mkdir(os.path.join(temp_dir, "test_dir"))
        with open(os.path.join(temp_dir, "test1.txt"), "w") as f:
            f.write("Test file 1")
        with open(os.path.join(temp_dir, "test2.txt"), "w") as f:
            f.write("Test file 2")
        with open(os.path.join(temp_dir, ".hidden"), "w") as f:
            f.write("Hidden file")
        
        # List directory without showing hidden files
        result = server.list_directory(temp_dir, show_hidden=False)
        print(f"List directory (no hidden) result: {result}")
        
        # Verify result
        assert result["success"] is True
        assert len(result["contents"]) == 3  # test_dir, test1.txt, test2.txt
        assert not any(item["name"] == ".hidden" for item in result["contents"])
        
        # List directory showing hidden files
        result = server.list_directory(temp_dir, show_hidden=True)
        print(f"List directory (with hidden) result: {result}")
        
        # Verify result
        assert result["success"] is True
        assert len(result["contents"]) == 4  # test_dir, test1.txt, test2.txt, .hidden
        assert any(item["name"] == ".hidden" for item in result["contents"])
        
        print("list_directory test passed!")
    finally:
        # Clean up
        shutil.rmtree(temp_dir)

def test_move_file():
    """Test moving/renaming a file."""
    temp_dir = tempfile.mkdtemp()
    try:
        # Create a test file
        source_path = os.path.join(temp_dir, "source.txt")
        with open(source_path, "w") as f:
            f.write("Test file content")
        
        # Move the file
        destination_path = os.path.join(temp_dir, "destination.txt")
        result = server.move_file(source_path, destination_path)
        print(f"Move file result: {result}")
        
        # Verify result
        assert result["success"] is True
        assert not os.path.exists(source_path)
        assert os.path.exists(destination_path)
        
        # Verify file content
        with open(destination_path, "r") as f:
            content = f.read()
            assert content == "Test file content"
        
        print("move_file test passed!")
    finally:
        # Clean up
        shutil.rmtree(temp_dir)

def test_search_files():
    """Test searching for files matching a pattern."""
    temp_dir = tempfile.mkdtemp()
    try:
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
        
        # Search for .txt files recursively
        result = server.search_files(temp_dir, "*.txt", recursive=True)
        print(f"Search files result (recursive): {result}")
        
        # Verify result
        assert result["success"] is True
        assert len(result["matches"]) == 3  # test1.txt, hello.txt, subdir/nested.txt
        
        # Search with non-recursive
        result = server.search_files(temp_dir, "*.txt", recursive=False)
        print(f"Search files result (non-recursive): {result}")
        
        # Verify result - should only find files in the top directory
        assert result["success"] is True
        assert len(result["matches"]) == 2  # test1.txt, hello.txt
        
        print("search_files test passed!")
    finally:
        # Clean up
        shutil.rmtree(temp_dir)

def test_get_file_info():
    """Test getting file information."""
    temp_dir = tempfile.mkdtemp()
    try:
        # Create a sample file
        sample_file = os.path.join(temp_dir, "sample.txt")
        with open(sample_file, "w") as f:
            f.write("This is a sample test file.")
        
        # Get info for a regular file
        result = server.get_file_info(sample_file)
        print(f"Get file info result: {result}")
        
        # Verify result
        assert result["success"] is True
        assert result["exists"] is True
        assert result["type"] == "file"
        assert result["size"] > 0
        assert "modified" in result
        assert "permissions" in result
        
        # Get info for a directory
        result = server.get_file_info(temp_dir)
        print(f"Get directory info result: {result}")
        
        # Verify result
        assert result["success"] is True
        assert result["exists"] is True
        assert result["type"] == "directory"
        
        # Get info for a non-existent file
        result = server.get_file_info("/path/to/nonexistent/file")
        print(f"Get non-existent file info result: {result}")
        
        # Verify result
        assert result["success"] is True  # The operation succeeded even though file doesn't exist
        assert result["exists"] is False
        
        print("get_file_info test passed!")
    finally:
        # Clean up
        shutil.rmtree(temp_dir)

def run_tests():
    """Run all tests"""
    tests = [
        test_read_file,
        test_write_file,
        test_create_directory,
        test_list_directory,
        test_move_file,
        test_search_files,
        test_get_file_info
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            print(f"\nRunning test: {test.__name__}")
            test()
            passed += 1
        except Exception as e:
            print(f"Test {test.__name__} failed: {e}")
            failed += 1
    
    print(f"\nTest Results: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 