# Copyright (c) Microsoft. All rights reserved.
"""Workflow-based Foundry agent for Agent Framework Debug UI.

This demonstrates how to wrap a Foundry agent in a workflow executor, which provides:
- Structured workflow patterns with multiple processing stages
- Better orchestration for complex multi-step operations
- Ability to chain multiple agents or processing steps
- Enhanced error handling and state management
- Integration with workflow features like branching, fan-out/fan-in, etc.

Requirements:
- Microsoft Foundry project with a deployed model
- Azure authentication (run 'az login' before starting)
- Environment variables set for project endpoint and model deployment
"""

import os

from agent_framework import (
    ChatAgent,
    ChatMessage,
    Executor,
    WorkflowContext,
    handler,
)
from typing_extensions import Never

class AgentExecutor(Executor):
    """
    Workflow executor that wraps a Foundry agent.
    
    This executor pattern provides:
    - Structured workflow integration
    - Better orchestration for complex operations
    - Enhanced error handling and state management
    - Ability to chain with other executors
    """
    
    agent: ChatAgent
    conversation_history: list[ChatMessage]
    
    def __init__(
        self,
        agent: ChatAgent,
        id: str = "ExecutorAgent",
    ):
        """
        Initialize the executor with a Foundry agent.
        
        Args:
            agent: The ChatAgent instance from AzureAIProjectAgentProvider
            id: Executor ID for workflow tracking
        """
        self.agent = agent
        self.conversation_history = []
        super().__init__(id=id)
    
    @handler
    async def handle_message(self, message: ChatMessage | str, ctx: WorkflowContext[str, Never]) -> None:
        """
        Handle incoming messages and process through the agent.
        
        Args:
            message: User message (ChatMessage or string)
            ctx: Workflow context for yielding output
        """
        # Convert string to ChatMessage if needed
        if isinstance(message, str):
            chat_message = ChatMessage(role="user", text=message)
        else:
            chat_message = message
        
        # Add to conversation history
        self.conversation_history.append(chat_message)
        
        # Run the agent with full conversation context
        response = await self.agent.run(self.conversation_history)
        
        # Extract the response text
        response_text = response.messages[-1].contents[-1].text if response.messages else ""
        
        # Add agent response to history
        self.conversation_history.extend(response.messages)
        
        # Yield the final output
        await ctx.send_message(response_text) # type: ignore
