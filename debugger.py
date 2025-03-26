#!/usr/bin/env python3

import cmd
import inspect
import json
import os
import pdb
import sys
import threading
import time
from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table
from rich.panel import Panel

console = Console()

class MCPDebugger(cmd.Cmd):
    """Interactive debugger for MCP tools"""
    
    intro = 'Welcome to MCP Debugger. Type help or ? to list commands.'
    prompt = '(mcp-debug) '
    
    def __init__(self, tool_registry: Dict[str, Any]):
        """Initialize the debugger with tool registry"""
        super().__init__()
        self.tool_registry = tool_registry
        self.current_tool = None
        self.breakpoints = {}
        self.watch_vars = {}
        self.history = []
        self.step_mode = False
        
    def do_list_tools(self, arg):
        """List all available tools"""
        table = Table(title="Available Tools")
        table.add_column("Tool Name")
        table.add_column("Description")
        
        for name, tool in self.tool_registry.items():
            table.add_row(name, tool.get('description', 'No description'))
            
        console.print(table)
        
    def do_inspect(self, arg):
        """Inspect a specific tool's implementation"""
        if not arg:
            console.print("[red]Please specify a tool name[/red]")
            return
            
        tool = self.tool_registry.get(arg)
        if not tool:
            console.print(f"[red]Tool '{arg}' not found[/red]")
            return
            
        func = tool.get('function')
        if not func:
            console.print("[red]Tool implementation not found[/red]")
            return
            
        source = inspect.getsource(func)
        syntax = Syntax(source, "python", theme="monokai")
        console.print(syntax)
        
    def do_break(self, arg):
        """Set a breakpoint in a tool"""
        if not arg:
            console.print("[red]Please specify: tool_name:line_number[/red]")
            return
            
        try:
            tool_name, line = arg.split(':')
            line = int(line)
        except ValueError:
            console.print("[red]Invalid format. Use: tool_name:line_number[/red]")
            return
            
        tool = self.tool_registry.get(tool_name)
        if not tool:
            console.print(f"[red]Tool '{tool_name}' not found[/red]")
            return
            
        if tool_name not in self.breakpoints:
            self.breakpoints[tool_name] = set()
        self.breakpoints[tool_name].add(line)
        console.print(f"[green]Breakpoint set in {tool_name} at line {line}[/green]")
        
    def do_watch(self, arg):
        """Watch a variable in a tool"""
        if not arg:
            console.print("[red]Please specify: tool_name:variable_name[/red]")
            return
            
        try:
            tool_name, var_name = arg.split(':')
        except ValueError:
            console.print("[red]Invalid format. Use: tool_name:variable_name[/red]")
            return
            
        tool = self.tool_registry.get(tool_name)
        if not tool:
            console.print(f"[red]Tool '{tool_name}' not found[/red]")
            return
            
        if tool_name not in self.watch_vars:
            self.watch_vars[tool_name] = set()
        self.watch_vars[tool_name].add(var_name)
        console.print(f"[green]Watching variable '{var_name}' in {tool_name}[/green]")
        
    def do_info(self, arg):
        """Show debugging information"""
        if not arg:
            self._show_general_info()
            return
            
        if arg == 'breakpoints':
            self._show_breakpoints()
        elif arg == 'watches':
            self._show_watches()
        elif arg == 'history':
            self._show_history()
        else:
            console.print(f"[red]Unknown info type: {arg}[/red]")
            
    def _show_general_info(self):
        """Show general debugging information"""
        info = Panel.fit(
            "\n".join([
                f"[bold]Active Tool:[/bold] {self.current_tool or 'None'}",
                f"[bold]Step Mode:[/bold] {'Enabled' if self.step_mode else 'Disabled'}",
                f"[bold]Breakpoints:[/bold] {sum(len(bp) for bp in self.breakpoints.values())}",
                f"[bold]Watches:[/bold] {sum(len(w) for w in self.watch_vars.values())}",
                f"[bold]History Entries:[/bold] {len(self.history)}"
            ]),
            title="Debugger Status"
        )
        console.print(info)
        
    def _show_breakpoints(self):
        """Show all breakpoints"""
        table = Table(title="Breakpoints")
        table.add_column("Tool")
        table.add_column("Line Numbers")
        
        for tool, lines in self.breakpoints.items():
            table.add_row(tool, ", ".join(str(line) for line in sorted(lines)))
            
        console.print(table)
        
    def _show_watches(self):
        """Show all watch variables"""
        table = Table(title="Watch Variables")
        table.add_column("Tool")
        table.add_column("Variables")
        
        for tool, vars in self.watch_vars.items():
            table.add_row(tool, ", ".join(sorted(vars)))
            
        console.print(table)
        
    def _show_history(self):
        """Show execution history"""
        table = Table(title="Execution History")
        table.add_column("Time")
        table.add_column("Tool")
        table.add_column("Event")
        table.add_column("Details")
        
        for entry in self.history[-10:]:  # Show last 10 entries
            table.add_row(
                entry['time'],
                entry['tool'],
                entry['event'],
                entry.get('details', '')
            )
            
        console.print(table)
        
    def do_step(self, arg):
        """Enable/disable step-by-step execution"""
        self.step_mode = not self.step_mode
        status = "enabled" if self.step_mode else "disabled"
        console.print(f"[green]Step-by-step execution {status}[/green]")
        
    def do_continue(self, arg):
        """Continue execution after a break"""
        if not self.current_tool:
            console.print("[yellow]No tool is currently being debugged[/yellow]")
            return
            
        self.step_mode = False
        console.print("[green]Continuing execution[/green]")
        
    def do_locals(self, arg):
        """Show local variables in current scope"""
        if not self.current_tool:
            console.print("[yellow]No tool is currently being debugged[/yellow]")
            return
            
        # This would be populated with actual local variables during debugging
        locals_dict = {}  # Placeholder
        
        table = Table(title="Local Variables")
        table.add_column("Name")
        table.add_column("Type")
        table.add_column("Value")
        
        for name, value in locals_dict.items():
            table.add_row(
                name,
                type(value).__name__,
                str(value)
            )
            
        console.print(table)
        
    def do_stack(self, arg):
        """Show the current call stack"""
        if not self.current_tool:
            console.print("[yellow]No tool is currently being debugged[/yellow]")
            return
            
        # This would be populated with actual stack frames during debugging
        frames = []  # Placeholder
        
        table = Table(title="Call Stack")
        table.add_column("Frame")
        table.add_column("Function")
        table.add_column("Line")
        table.add_column("File")
        
        for i, frame in enumerate(frames):
            table.add_row(
                str(i),
                frame.get('function', 'unknown'),
                str(frame.get('line', '?')),
                frame.get('file', 'unknown')
            )
            
        console.print(table)
        
    def do_quit(self, arg):
        """Exit the debugger"""
        return True
        
    def default(self, line):
        """Handle unknown commands"""
        console.print(f"[red]Unknown command: {line}[/red]")
        console.print("Type 'help' or '?' for a list of commands")
        
    def emptyline(self):
        """Handle empty lines"""
        pass
        
    def _log_event(self, tool: str, event: str, details: Optional[str] = None):
        """Log a debugging event"""
        self.history.append({
            'time': time.strftime('%H:%M:%S'),
            'tool': tool,
            'event': event,
            'details': details
        })
        
    def debug_tool(self, tool_name: str, *args, **kwargs):
        """Debug a tool execution"""
        tool = self.tool_registry.get(tool_name)
        if not tool:
            console.print(f"[red]Tool '{tool_name}' not found[/red]")
            return
            
        self.current_tool = tool_name
        self._log_event(tool_name, 'start', f"args: {args}, kwargs: {kwargs}")
        
        try:
            # This is where we'd integrate with the actual tool execution
            # For now, it's just a placeholder
            console.print(f"[green]Debugging tool: {tool_name}[/green]")
            self.cmdloop()
        finally:
            self._log_event(tool_name, 'end')
            self.current_tool = None

def create_debugger(tool_registry: Dict[str, Any]) -> MCPDebugger:
    """Create and return a debugger instance"""
    return MCPDebugger(tool_registry) 