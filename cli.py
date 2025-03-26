#!/usr/bin/env python3

import click
import json
import requests
import sys
import os
from typing import Dict, Any
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich.panel import Panel

console = Console()

class MCPClient:
    def __init__(self, host: str = "http://localhost", port: int = 7443):
        self.base_url = f"{host}:{port}"
        
    def call_tool(self, tool_name: str, **params) -> Dict[str, Any]:
        """Call an MCP tool with parameters"""
        try:
            response = requests.post(
                f"{self.base_url}/tools/{tool_name}",
                json=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error calling tool {tool_name}: {str(e)}[/red]")
            sys.exit(1)

@click.group()
def cli():
    """Terminal Command Runner MCP CLI"""
    pass

@cli.group()
def command():
    """Command execution and management"""
    pass

@command.command()
@click.argument('cmd')
@click.option('--timeout', '-t', default=10, help='Command timeout in seconds')
@click.option('--background/--no-background', default=True, help='Allow running in background')
def execute(cmd: str, timeout: int, background: bool):
    """Execute a command"""
    client = MCPClient()
    result = client.call_tool(
        'execute_command',
        command=cmd,
        timeout=timeout,
        allow_background=background
    )
    
    if result.get('error'):
        console.print(f"[red]Error: {result['error']}[/red]")
        return
    
    console.print(Panel.fit(
        f"[green]Command executed[/green]\n"
        f"PID: {result.get('pid')}\n"
        f"Exit code: {result.get('exit_code')}\n"
        f"Runtime: {result.get('runtime')}s"
    ))
    
    if result.get('stdout'):
        console.print("\n[bold]Output:[/bold]")
        console.print(result['stdout'])
    
    if result.get('stderr'):
        console.print("\n[bold red]Errors:[/bold red]")
        console.print(result['stderr'])

@command.command()
def list():
    """List active command sessions"""
    client = MCPClient()
    result = client.call_tool('list_sessions')
    
    if not result.get('sessions'):
        console.print("[yellow]No active sessions[/yellow]")
        return
    
    table = Table(title="Active Sessions")
    table.add_column("PID", justify="right")
    table.add_column("Command")
    table.add_column("Start Time")
    
    for session in result['sessions']:
        table.add_row(
            str(session['pid']),
            session['command'],
            session['start_time']
        )
    
    console.print(table)

@cli.group()
def file():
    """File operations"""
    pass

@file.command()
@click.argument('path')
def read(path: str):
    """Read file contents"""
    client = MCPClient()
    result = client.call_tool('read_file', path=path)
    
    if result.get('error'):
        console.print(f"[red]Error: {result['error']}[/red]")
        return
    
    syntax = Syntax(result['content'], "python", theme="monokai")
    console.print(syntax)

@file.command()
@click.argument('path')
@click.argument('content')
def write(path: str, content: str):
    """Write content to a file"""
    client = MCPClient()
    result = client.call_tool('write_file', path=path, content=content)
    
    if result.get('error'):
        console.print(f"[red]Error: {result['error']}[/red]")
        return
    
    console.print(f"[green]Successfully wrote to {path}[/green]")

@cli.group()
def system():
    """System operations"""
    pass

@system.command()
def info():
    """Get system information"""
    client = MCPClient()
    result = client.call_tool('system_info')
    
    if result.get('error'):
        console.print(f"[red]Error: {result['error']}[/red]")
        return
    
    console.print(Panel.fit(
        "\n".join([
            f"[bold]Platform:[/bold] {result.get('platform', 'Unknown')}",
            f"[bold]Python Version:[/bold] {result.get('python_version', 'Unknown')}",
            f"[bold]CPU Count:[/bold] {result.get('cpu_count', 'Unknown')}",
            f"[bold]Hostname:[/bold] {result.get('hostname', 'Unknown')}"
        ]),
        title="System Information"
    ))

@cli.group()
def dev():
    """Development tools"""
    pass

@dev.command()
@click.argument('path', default=".")
def analyze(path: str):
    """Analyze codebase"""
    client = MCPClient()
    result = client.call_tool('analyze_codebase', path=path)
    
    if result.get('error'):
        console.print(f"[red]Error: {result['error']}[/red]")
        return
    
    results = result.get('results', {})
    
    # Show complexity hotspots
    if results.get('complexity_hotspots'):
        table = Table(title="Complexity Hotspots")
        table.add_column("File")
        table.add_column("Score", justify="right")
        
        for hotspot in results['complexity_hotspots']:
            table.add_row(
                hotspot['file'],
                str(hotspot['complexity']['score'])
            )
        
        console.print(table)
    
    # Show security issues
    if results.get('security_issues'):
        table = Table(title="Security Issues")
        table.add_column("File")
        table.add_column("Line", justify="right")
        table.add_column("Type")
        table.add_column("Severity")
        
        for issue in results['security_issues']:
            table.add_row(
                issue['file'],
                str(issue['line']),
                issue['type'],
                issue['severity']
            )
        
        console.print(table)

@dev.command()
@click.argument('path', default=".")
@click.option('--fix/--no-fix', default=False, help='Automatically fix issues')
def lint(path: str, fix: bool):
    """Run code linting"""
    client = MCPClient()
    result = client.call_tool('lint_code', path=path, fix=fix)
    
    if result.get('error'):
        console.print(f"[red]Error: {result['error']}[/red]")
        return
    
    if not result.get('issues'):
        console.print("[green]No issues found![/green]")
        return
    
    table = Table(title="Linting Issues")
    table.add_column("File")
    table.add_column("Line", justify="right")
    table.add_column("Message")
    
    for issue in result['issues']:
        table.add_row(
            issue['file'],
            str(issue['line']),
            issue['message']
        )
    
    console.print(table)

if __name__ == '__main__':
    cli() 