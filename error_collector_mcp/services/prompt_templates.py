"""Prompt templates for AI summarization."""

import json
from typing import List, Dict, Any
from ..models import BaseError, BrowserError, TerminalError, ErrorCategory


class PromptTemplates:
    """Collection of prompt templates for different error types and scenarios."""
    
    @staticmethod
    def get_system_prompt() -> str:
        """Get the main system prompt for error analysis."""
        return """You are an expert software developer and debugging assistant with deep knowledge of:
- JavaScript/TypeScript and web development
- Command-line tools and system administration
- Common programming patterns and anti-patterns
- Error handling best practices
- Debugging methodologies

Your task is to analyze programming errors and provide helpful, actionable summaries.

When analyzing errors, focus on:
1. **Root Cause**: Identify the fundamental issue causing the error
2. **Impact Assessment**: Evaluate how this affects the application/system
3. **Solutions**: Provide specific, implementable fixes
4. **Prevention**: Suggest ways to avoid similar issues

Always respond with a JSON object containing:
- "root_cause": Clear explanation of what caused the error
- "impact_assessment": How this error affects the application
- "suggested_solutions": Array of specific, actionable solutions (3-5 items)
- "confidence_score": Your confidence in the analysis (0.0 to 1.0)

Be concise but thorough. Prioritize practical solutions that developers can implement immediately."""
    
    @staticmethod
    def get_browser_error_prompt(error: BrowserError) -> str:
        """Get specialized prompt for browser errors."""
        context_info = []
        
        if error.url:
            context_info.append(f"Page URL: {error.url}")
        if error.user_agent:
            context_info.append(f"Browser: {error.user_agent}")
        if error.page_title:
            context_info.append(f"Page Title: {error.page_title}")
        
        location_info = ""
        if error.line_number and error.column_number:
            location_info = f"Location: Line {error.line_number}, Column {error.column_number}"
        elif error.line_number:
            location_info = f"Location: Line {error.line_number}"
        
        stack_trace_info = ""
        if error.stack_trace:
            # Truncate very long stack traces
            stack_trace = error.stack_trace
            if len(stack_trace) > 1000:
                stack_trace = stack_trace[:1000] + "... [truncated]"
            stack_trace_info = f"Stack Trace:\n{stack_trace}"
        
        prompt = f"""Analyze this JavaScript/Browser error:

**Error Details:**
- Type: {error.error_type}
- Message: {error.message}
- Category: {error.category.value}
- Severity: {error.severity.value}
{location_info}

**Context:**
{chr(10).join(context_info) if context_info else "No additional context available"}

{stack_trace_info}

**Analysis Focus:**
- Is this a common JavaScript error pattern?
- What browser compatibility issues might be involved?
- Are there modern JavaScript features that could prevent this?
- What debugging tools would help identify the issue?

Provide your analysis as a JSON object."""
        
        return prompt
    
    @staticmethod
    def get_terminal_error_prompt(error: TerminalError) -> str:
        """Get specialized prompt for terminal errors."""
        command_context = ""
        if error.working_directory:
            command_context += f"Working Directory: {error.working_directory}\n"
        
        if error.environment:
            # Include relevant environment variables
            relevant_env = {k: v for k, v in error.environment.items() 
                          if k in ['PATH', 'NODE_ENV', 'PYTHON_PATH', 'JAVA_HOME', 'HOME']}
            if relevant_env:
                env_str = ", ".join([f"{k}={v[:50]}..." if len(v) > 50 else f"{k}={v}" 
                                   for k, v in relevant_env.items()])
                command_context += f"Environment: {env_str}\n"
        
        output_info = ""
        if error.stderr_output:
            stderr = error.stderr_output
            if len(stderr) > 1500:
                stderr = stderr[:1500] + "... [truncated]"
            output_info += f"Error Output:\n{stderr}\n"
        
        if error.stdout_output and len(error.stdout_output.strip()) > 0:
            stdout = error.stdout_output
            if len(stdout) > 500:
                stdout = stdout[:500] + "... [truncated]"
            output_info += f"Standard Output:\n{stdout}\n"
        
        prompt = f"""Analyze this command-line/terminal error:

**Command Details:**
- Command: {error.command}
- Exit Code: {error.exit_code}
- Category: {error.category.value}
- Severity: {error.severity.value}

**Context:**
{command_context.strip() if command_context else "No additional context available"}

**Output:**
{output_info.strip() if output_info else "No output captured"}

**Analysis Focus:**
- What does this exit code typically indicate?
- Are there permission or dependency issues?
- What are common causes for this type of command failure?
- What diagnostic steps would help identify the root cause?

Provide your analysis as a JSON object."""
        
        return prompt
    
    @staticmethod
    def get_multi_error_prompt(errors: List[BaseError]) -> str:
        """Get prompt for analyzing multiple related errors."""
        error_summaries = []
        
        for i, error in enumerate(errors, 1):
            summary = f"**Error {i}:**\n"
            summary += f"- Source: {error.source.value}\n"
            summary += f"- Category: {error.category.value}\n"
            summary += f"- Severity: {error.severity.value}\n"
            summary += f"- Message: {error.message}\n"
            
            if isinstance(error, BrowserError):
                summary += f"- Type: {error.error_type}\n"
                if error.url:
                    summary += f"- URL: {error.url}\n"
                if error.line_number:
                    summary += f"- Line: {error.line_number}\n"
            
            elif isinstance(error, TerminalError):
                summary += f"- Command: {error.command}\n"
                summary += f"- Exit Code: {error.exit_code}\n"
                if error.working_directory:
                    summary += f"- Directory: {error.working_directory}\n"
            
            summary += f"- Timestamp: {error.timestamp.isoformat()}\n"
            error_summaries.append(summary)
        
        # Analyze error patterns
        sources = [error.source for error in errors]
        categories = [error.category for error in errors]
        severities = [error.severity for error in errors]
        
        pattern_analysis = f"""
**Pattern Analysis:**
- Sources: {', '.join(set(s.value for s in sources))}
- Categories: {', '.join(set(c.value for c in categories))}
- Severities: {', '.join(set(s.value for s in severities))}
- Time Range: {min(e.timestamp for e in errors).isoformat()} to {max(e.timestamp for e in errors).isoformat()}
"""
        
        prompt = f"""Analyze these {len(errors)} related errors that occurred in sequence:

{chr(10).join(error_summaries)}

{pattern_analysis}

**Analysis Focus:**
- What is the common root cause linking these errors?
- Is this a cascading failure or independent issues?
- What is the likely sequence of events that led to these errors?
- Which error should be addressed first to resolve the others?
- Are there systemic issues indicated by this error pattern?

Provide a comprehensive analysis as a JSON object that addresses the collective impact and provides solutions that tackle the root cause."""
        
        return prompt
    
    @staticmethod
    def get_category_specific_prompt(category: ErrorCategory, errors: List[BaseError]) -> str:
        """Get category-specific analysis prompt."""
        category_prompts = {
            ErrorCategory.SYNTAX: """
**Syntax Error Analysis Focus:**
- What syntax rules are being violated?
- Is this due to language version compatibility?
- Are there linting rules that would catch this?
- What IDE/editor features would prevent this error?
""",
            ErrorCategory.RUNTIME: """
**Runtime Error Analysis Focus:**
- What runtime conditions trigger this error?
- Are there type checking or validation gaps?
- What defensive programming techniques would help?
- How can this be caught earlier in the development cycle?
""",
            ErrorCategory.NETWORK: """
**Network Error Analysis Focus:**
- Is this a connectivity, configuration, or protocol issue?
- Are there timeout or retry mechanisms needed?
- What network debugging tools would help diagnose this?
- Are there fallback or offline strategies to implement?
""",
            ErrorCategory.PERMISSION: """
**Permission Error Analysis Focus:**
- What specific permissions are missing?
- Is this a file system, API, or system-level permission issue?
- How can permissions be properly configured?
- What security best practices should be followed?
""",
            ErrorCategory.RESOURCE: """
**Resource Error Analysis Focus:**
- What resource is being exhausted (memory, disk, CPU, network)?
- Are there resource leaks or inefficient usage patterns?
- What monitoring and alerting should be in place?
- How can resource usage be optimized?
""",
            ErrorCategory.LOGIC: """
**Logic Error Analysis Focus:**
- What business logic or algorithmic assumptions are incorrect?
- Are there edge cases not being handled?
- What testing strategies would catch these issues?
- How can the logic be made more robust and predictable?
"""
        }
        
        base_prompt = PromptTemplates.get_multi_error_prompt(errors) if len(errors) > 1 else PromptTemplates.get_single_error_prompt(errors[0])
        category_focus = category_prompts.get(category, "")
        
        return base_prompt + "\n" + category_focus
    
    @staticmethod
    def get_single_error_prompt(error: BaseError) -> str:
        """Get prompt for a single error based on its type."""
        if isinstance(error, BrowserError):
            return PromptTemplates.get_browser_error_prompt(error)
        elif isinstance(error, TerminalError):
            return PromptTemplates.get_terminal_error_prompt(error)
        else:
            return PromptTemplates.get_generic_error_prompt(error)
    
    @staticmethod
    def get_generic_error_prompt(error: BaseError) -> str:
        """Get generic prompt for base errors."""
        prompt = f"""Analyze this error:

**Error Details:**
- Source: {error.source.value}
- Category: {error.category.value}
- Severity: {error.severity.value}
- Message: {error.message}
- Timestamp: {error.timestamp.isoformat()}

**Context:**
{json.dumps(error.context, indent=2) if error.context else "No additional context available"}

**Stack Trace:**
{error.stack_trace if error.stack_trace else "No stack trace available"}

**Analysis Focus:**
- What type of error is this and what typically causes it?
- What are the immediate and long-term impacts?
- What debugging approaches would be most effective?
- What preventive measures can be implemented?

Provide your analysis as a JSON object."""
        
        return prompt
    
    @staticmethod
    def get_solution_enhancement_prompt(existing_summary: Dict[str, Any]) -> str:
        """Get prompt for enhancing existing solutions."""
        return f"""Based on this error analysis, provide additional specific solutions:

**Current Analysis:**
- Root Cause: {existing_summary.get('root_cause', 'Unknown')}
- Impact: {existing_summary.get('impact_assessment', 'Unknown')}
- Current Solutions: {', '.join(existing_summary.get('suggested_solutions', []))}

**Request:**
Provide 3-5 additional specific, actionable solutions focusing on:

1. **Prevention Strategies**: How to avoid this error in the future
2. **Alternative Approaches**: Different ways to implement the same functionality
3. **Debugging Techniques**: Tools and methods to diagnose similar issues
4. **Best Practices**: Industry standards that would prevent this class of errors
5. **Monitoring & Alerting**: How to detect and respond to similar issues quickly

**Format:**
Return as a simple list, one solution per line, starting with "- "
Each solution should be specific and implementable within a reasonable timeframe.
Focus on practical, real-world solutions that developers can act on immediately."""
    
    @staticmethod
    def get_confidence_assessment_prompt(error_data: Dict[str, Any]) -> str:
        """Get prompt for assessing confidence in error analysis."""
        return f"""Assess the confidence level for this error analysis:

**Available Information:**
- Error message clarity: {'High' if len(error_data.get('message', '')) > 20 else 'Low'}
- Stack trace available: {'Yes' if error_data.get('stack_trace') else 'No'}
- Context information: {'Rich' if error_data.get('context') else 'Limited'}
- Error type specificity: {'High' if error_data.get('error_type') else 'Low'}

**Analysis Quality Factors:**
- How specific and actionable are the suggested solutions?
- How well does the root cause explanation match the error symptoms?
- Are there any ambiguities or assumptions in the analysis?
- How common/well-documented is this type of error?

Return a confidence score between 0.0 and 1.0, where:
- 0.9-1.0: Very confident, clear error with well-known solutions
- 0.7-0.8: Confident, good understanding with solid solutions
- 0.5-0.6: Moderate confidence, some uncertainty in analysis
- 0.3-0.4: Low confidence, limited information or unclear error
- 0.0-0.2: Very low confidence, insufficient data for reliable analysis

Provide only the numeric score (e.g., 0.8)."""