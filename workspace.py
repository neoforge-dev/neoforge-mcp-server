#!/usr/bin/env python3

import json
import os
import shutil
import tempfile
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from rich.console import Console
from rich.table import Table

console = Console()

@dataclass
class WorkspaceConfig:
    """Configuration for a workspace"""
    name: str
    description: str
    created_at: str
    updated_at: str
    tools: List[str]
    environment: Dict[str, str]
    paths: Set[str]
    settings: Dict[str, any]

class WorkspaceManager:
    """Manages MCP workspaces"""
    
    def __init__(self, base_path: str = None):
        """Initialize workspace manager"""
        self.base_path = base_path or os.path.expanduser('~/.mcp/workspaces')
        self.current_workspace = None
        self._ensure_base_path()
        
    def _ensure_base_path(self):
        """Ensure base path exists"""
        os.makedirs(self.base_path, exist_ok=True)
        
    def create_workspace(self, name: str, description: str = "") -> WorkspaceConfig:
        """Create a new workspace"""
        workspace_path = os.path.join(self.base_path, name)
        if os.path.exists(workspace_path):
            raise ValueError(f"Workspace '{name}' already exists")
            
        # Create workspace structure
        os.makedirs(workspace_path)
        os.makedirs(os.path.join(workspace_path, 'tools'))
        os.makedirs(os.path.join(workspace_path, 'data'))
        os.makedirs(os.path.join(workspace_path, 'logs'))
        os.makedirs(os.path.join(workspace_path, 'temp'))
        
        # Create workspace config
        config = WorkspaceConfig(
            name=name,
            description=description,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            tools=[],
            environment={},
            paths=set(),
            settings={}
        )
        
        # Save config
        self._save_config(config)
        console.print(f"[green]Created workspace: {name}[/green]")
        return config
        
    def list_workspaces(self) -> List[WorkspaceConfig]:
        """List all workspaces"""
        workspaces = []
        for name in os.listdir(self.base_path):
            path = os.path.join(self.base_path, name)
            if os.path.isdir(path):
                try:
                    config = self._load_config(name)
                    workspaces.append(config)
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not load workspace '{name}': {e}[/yellow]")
        return workspaces
        
    def get_workspace(self, name: str) -> Optional[WorkspaceConfig]:
        """Get workspace by name"""
        try:
            return self._load_config(name)
        except FileNotFoundError:
            return None
            
    def delete_workspace(self, name: str):
        """Delete a workspace"""
        workspace_path = os.path.join(self.base_path, name)
        if not os.path.exists(workspace_path):
            raise ValueError(f"Workspace '{name}' does not exist")
            
        if self.current_workspace and self.current_workspace.name == name:
            self.current_workspace = None
            
        shutil.rmtree(workspace_path)
        console.print(f"[green]Deleted workspace: {name}[/green]")
        
    def activate_workspace(self, name: str) -> WorkspaceConfig:
        """Activate a workspace"""
        config = self._load_config(name)
        if not config:
            raise ValueError(f"Workspace '{name}' does not exist")
            
        self.current_workspace = config
        
        # Set environment variables
        os.environ.update(config.environment)
        
        # Add paths to Python path
        for path in config.paths:
            if path not in sys.path:
                sys.path.append(path)
                
        console.print(f"[green]Activated workspace: {name}[/green]")
        return config
        
    def deactivate_workspace(self):
        """Deactivate current workspace"""
        if not self.current_workspace:
            return
            
        # Remove environment variables
        for key in self.current_workspace.environment:
            if key in os.environ:
                del os.environ[key]
                
        # Remove paths from Python path
        for path in self.current_workspace.paths:
            if path in sys.path:
                sys.path.remove(path)
                
        name = self.current_workspace.name
        self.current_workspace = None
        console.print(f"[green]Deactivated workspace: {name}[/green]")
        
    def add_tool(self, name: str, tool_path: str):
        """Add a tool to current workspace"""
        if not self.current_workspace:
            raise RuntimeError("No workspace is active")
            
        if not os.path.exists(tool_path):
            raise ValueError(f"Tool path does not exist: {tool_path}")
            
        # Copy tool to workspace
        workspace_tool_path = os.path.join(
            self.base_path,
            self.current_workspace.name,
            'tools',
            os.path.basename(tool_path)
        )
        shutil.copy2(tool_path, workspace_tool_path)
        
        # Update config
        if name not in self.current_workspace.tools:
            self.current_workspace.tools.append(name)
            self._save_config(self.current_workspace)
            
        console.print(f"[green]Added tool '{name}' to workspace[/green]")
        
    def remove_tool(self, name: str):
        """Remove a tool from current workspace"""
        if not self.current_workspace:
            raise RuntimeError("No workspace is active")
            
        if name not in self.current_workspace.tools:
            raise ValueError(f"Tool '{name}' not found in workspace")
            
        # Remove tool file
        tool_path = os.path.join(
            self.base_path,
            self.current_workspace.name,
            'tools',
            name
        )
        if os.path.exists(tool_path):
            os.remove(tool_path)
            
        # Update config
        self.current_workspace.tools.remove(name)
        self._save_config(self.current_workspace)
        
        console.print(f"[green]Removed tool '{name}' from workspace[/green]")
        
    def set_environment(self, key: str, value: str):
        """Set environment variable in current workspace"""
        if not self.current_workspace:
            raise RuntimeError("No workspace is active")
            
        self.current_workspace.environment[key] = value
        os.environ[key] = value
        self._save_config(self.current_workspace)
        
        console.print(f"[green]Set environment variable: {key}[/green]")
        
    def add_path(self, path: str):
        """Add path to current workspace"""
        if not self.current_workspace:
            raise RuntimeError("No workspace is active")
            
        path = os.path.abspath(path)
        if not os.path.exists(path):
            raise ValueError(f"Path does not exist: {path}")
            
        self.current_workspace.paths.add(path)
        if path not in sys.path:
            sys.path.append(path)
        self._save_config(self.current_workspace)
        
        console.print(f"[green]Added path to workspace: {path}[/green]")
        
    def remove_path(self, path: str):
        """Remove path from current workspace"""
        if not self.current_workspace:
            raise RuntimeError("No workspace is active")
            
        path = os.path.abspath(path)
        if path in self.current_workspace.paths:
            self.current_workspace.paths.remove(path)
            if path in sys.path:
                sys.path.remove(path)
            self._save_config(self.current_workspace)
            
        console.print(f"[green]Removed path from workspace: {path}[/green]")
        
    def update_settings(self, settings: Dict[str, any]):
        """Update workspace settings"""
        if not self.current_workspace:
            raise RuntimeError("No workspace is active")
            
        self.current_workspace.settings.update(settings)
        self._save_config(self.current_workspace)
        
        console.print("[green]Updated workspace settings[/green]")
        
    def get_temp_dir(self) -> str:
        """Get temporary directory for current workspace"""
        if not self.current_workspace:
            raise RuntimeError("No workspace is active")
            
        temp_dir = os.path.join(
            self.base_path,
            self.current_workspace.name,
            'temp'
        )
        os.makedirs(temp_dir, exist_ok=True)
        return temp_dir
        
    def _load_config(self, name: str) -> WorkspaceConfig:
        """Load workspace configuration"""
        config_path = os.path.join(self.base_path, name, 'config.json')
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Workspace config not found: {config_path}")
            
        with open(config_path, 'r') as f:
            data = json.load(f)
            data['paths'] = set(data['paths'])
            return WorkspaceConfig(**data)
            
    def _save_config(self, config: WorkspaceConfig):
        """Save workspace configuration"""
        config_path = os.path.join(self.base_path, config.name, 'config.json')
        data = asdict(config)
        data['paths'] = list(data['paths'])
        data['updated_at'] = datetime.now().isoformat()
        
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2)
            
    def show_info(self):
        """Show information about current workspace"""
        if not self.current_workspace:
            console.print("[yellow]No workspace is active[/yellow]")
            return
            
        # Create workspace info table
        info_table = Table(title="Workspace Information")
        info_table.add_column("Property")
        info_table.add_column("Value")
        
        info_table.add_row("Name", self.current_workspace.name)
        info_table.add_row("Description", self.current_workspace.description)
        info_table.add_row("Created", self.current_workspace.created_at)
        info_table.add_row("Updated", self.current_workspace.updated_at)
        
        console.print(info_table)
        
        # Create tools table
        if self.current_workspace.tools:
            tools_table = Table(title="Tools")
            tools_table.add_column("Name")
            for tool in sorted(self.current_workspace.tools):
                tools_table.add_row(tool)
            console.print(tools_table)
            
        # Create environment table
        if self.current_workspace.environment:
            env_table = Table(title="Environment Variables")
            env_table.add_column("Key")
            env_table.add_column("Value")
            for key, value in sorted(self.current_workspace.environment.items()):
                env_table.add_row(key, value)
            console.print(env_table)
            
        # Create paths table
        if self.current_workspace.paths:
            paths_table = Table(title="Paths")
            paths_table.add_column("Path")
            for path in sorted(self.current_workspace.paths):
                paths_table.add_row(path)
            console.print(paths_table)
            
        # Create settings table
        if self.current_workspace.settings:
            settings_table = Table(title="Settings")
            settings_table.add_column("Key")
            settings_table.add_column("Value")
            for key, value in sorted(self.current_workspace.settings.items()):
                settings_table.add_row(key, str(value))
            console.print(settings_table)

def create_workspace_manager(base_path: Optional[str] = None) -> WorkspaceManager:
    """Create and return a workspace manager instance"""
    return WorkspaceManager(base_path) 