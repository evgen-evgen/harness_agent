from __future__ import annotations

import json
from typing import Any

from harness_agent.cache import CacheRegistry, CacheStore, default_cache_registry
from harness_agent.config import AgentConfig, RuntimeSettings
from harness_agent.context import ContextBuilder
from harness_agent.guardrails import Guardrail, GuardrailRegistry, default_guardrail_registry
from harness_agent.llm import ChatClient, LiteLLMChatClient
from harness_agent.memory import MemoryPolicy, MemoryRegistry, MemoryStore, default_memory_registry
from harness_agent.messages import AgentResult, ChatMessage
from harness_agent.metrics import JsonlMetricsSink, RunMetrics
from harness_agent.observability import Tracer
from harness_agent.run_context import RunContext, reset_run_context, set_run_context
from harness_agent.sessions import SessionMessage, SessionRegistry, SessionStore, default_session_registry
from harness_agent.skills import SkillRegistry, default_skill_registry
from harness_agent.tools import ToolExecutor, ToolRegistry, default_tool_registry, tool_to_litellm_tool


class AgentRunner:
    def __init__(
        self,
        config: AgentConfig,
        *,
        chat_client: ChatClient | None = None,
        tool_registry: ToolRegistry | None = None,
        skill_registry: SkillRegistry | None = None,
        guardrail_registry: GuardrailRegistry | None = None,
        cache_registry: CacheRegistry | None = None,
        memory_registry: MemoryRegistry | None = None,
        session_registry: SessionRegistry | None = None,
        cache_store: CacheStore | None = None,
        memory_store: MemoryStore | None = None,
        session_store: SessionStore | None = None,
        memory_policy: MemoryPolicy | None = None,
        tool_executor: ToolExecutor | None = None,
        guardrails: list[Guardrail] | None = None,
        settings: RuntimeSettings | None = None,
    ) -> None:
        self.config = config
        self.settings = settings or RuntimeSettings()
        self.chat_client = chat_client or LiteLLMChatClient(settings=self.settings)
        self.tool_registry = tool_registry or default_tool_registry(config, self.settings)
        self.skill_registry = skill_registry or default_skill_registry()
        self.guardrail_registry = guardrail_registry or default_guardrail_registry()
        self.cache_registry = cache_registry or default_cache_registry()
        self.memory_registry = memory_registry or default_memory_registry()
        self.session_registry = session_registry or default_session_registry()
        self.cache_store = cache_store or self.cache_registry.create(config.cache, self.settings)
        self.memory_store = memory_store or self.memory_registry.create(config.memory, self.settings)
        self.session_store = session_store or self.session_registry.create(config.session, self.settings)
        self.memory_policy = memory_policy or MemoryPolicy(config.memory_max_chars)
        self.context_builder = ContextBuilder(config)
        self.guardrails = guardrails or self.guardrail_registry.select(config.guardrails)
        self.tool_executor = tool_executor or ToolExecutor(
            config=config,
            tool_registry=self.tool_registry,
            cache_store=self.cache_store,
            guardrails=self.guardrails,
        )

    async def run(
        self,
        user_input: str,
        *,
        session_id: str = "default",
        channel_id: str | None = None,
        conversation_id: str | None = None,
        user_id: str | None = None,
    ) -> AgentResult:
        context_token = set_run_context(
            RunContext(
                session_id=session_id,
                channel_id=channel_id,
                conversation_id=conversation_id,
                user_id=user_id,
            )
        )
        metrics = RunMetrics(
            JsonlMetricsSink(self.settings.metrics_path),
            agent_name=self.config.name,
            model=self.config.model,
        )
        try:
            return await self._run_with_context(user_input, session_id=session_id, metrics=metrics)
        finally:
            reset_run_context(context_token)

    async def _run_with_context(
        self,
        user_input: str,
        *,
        session_id: str,
        metrics: RunMetrics,
    ) -> AgentResult:
        tracer = Tracer(metrics)
        metrics.event("run_started", session_id=session_id)

        with tracer.span("guardrails.input"):
            for guardrail in self.guardrails:
                decision = guardrail.check_user_input(user_input)
                if not decision.allowed:
                    metrics.event("guardrail_blocked_input", guardrail=guardrail.id, reason=decision.reason)
                    return AgentResult(
                        final=f"Request blocked by guardrail: {decision.reason}",
                        messages=[],
                        iterations=0,
                        metrics=metrics.finish_payload(),
                    )

        skills = self.skill_registry.select(self.config.skills)
        tool_names = sorted(set(self.config.tools + [tool for skill in skills for tool in skill.tools]))
        tools = self.tool_registry.select(tool_names)
        with tracer.span("memory.search", limit=self.config.memory_top_k):
            memory_records = await self.memory_store.search(user_input, self.config.memory_top_k)
        if memory_records:
            metrics.event("memory_loaded", count=len(memory_records))
        with tracer.span("session.load", session_id=session_id, limit=self.config.session_history_limit):
            session_messages = await self.session_store.recent(
                session_id,
                self.config.session_history_limit,
            )
        if session_messages:
            metrics.event("session_loaded", count=len(session_messages), session_id=session_id)
        with tracer.span("context.build"):
            context = self.context_builder.build(
                user_input=user_input,
                skills=skills,
                memory_records=memory_records,
                session_messages=session_messages,
            )
        metrics.event(
            "context_built",
            total_chars=context.total_chars,
            memory_used=context.memory_used,
            memory_dropped=context.memory_dropped,
            session_used=context.session_used,
            session_dropped=context.session_dropped,
        )
        messages = context.messages

        for iteration in range(1, self.config.max_iterations + 1):
            metrics.llm_calls += 1
            with tracer.span("llm.complete", iteration=iteration):
                response = await self.chat_client.complete(
                    model=self.config.model,
                    messages=messages,
                    tools=[tool_to_litellm_tool(tool) for tool in tools],
                    temperature=self.config.temperature,
                )
            choice = response.choices[0]
            assistant_message = choice.message
            content = assistant_message.get("content") if isinstance(assistant_message, dict) else assistant_message.content
            tool_calls = assistant_message.get("tool_calls") if isinstance(assistant_message, dict) else getattr(assistant_message, "tool_calls", None)

            messages.append(
                ChatMessage(
                    role="assistant",
                    content=content or "",
                    tool_calls=self._serialize_tool_calls(tool_calls) if tool_calls else None,
                )
            )

            if not tool_calls:
                return await self._finish(
                    final=content or "",
                    user_input=user_input,
                    session_id=session_id,
                    messages=messages,
                    iterations=iteration,
                    metrics=metrics,
                )

            for call in tool_calls:
                tool_call = self._normalize_tool_call(call)
                tool_name = tool_call["name"]
                arguments = tool_call["arguments"]
                if tool_name == "final_answer":
                    metrics.event("final_answer_tool_called")
                    return await self._finish(
                        final=str(arguments.get("answer", "")),
                        user_input=user_input,
                        session_id=session_id,
                        messages=messages,
                        iterations=iteration,
                        metrics=metrics,
                    )
                tool_result = await self.tool_executor.execute(
                    tool_name=tool_name,
                    arguments=arguments,
                    metrics=metrics,
                    tracer=tracer,
                )

                messages.append(
                    ChatMessage(
                        role="tool",
                        tool_call_id=tool_call["id"],
                        name=tool_name,
                        content=tool_result.content,
                    )
                )

        payload = metrics.finish_payload()
        metrics.event(
            "run_stopped_max_iterations",
            duration_ms=payload["duration_ms"],
            tool_calls=payload["tool_calls"],
            llm_calls=payload["llm_calls"],
        )
        return AgentResult(
            final="Stopped: max_iterations reached before a final answer.",
            messages=messages,
            iterations=self.config.max_iterations,
            metrics=payload,
        )

    async def _finish(
        self,
        *,
        final: str,
        user_input: str,
        session_id: str,
        messages: list[ChatMessage],
        iterations: int,
        metrics: RunMetrics,
    ) -> AgentResult:
        for guardrail in self.guardrails:
            decision = guardrail.check_output(final)
            if decision.replacement is not None:
                final = decision.replacement
        await self.session_store.append(
            session_id,
            SessionMessage(role="user", content=user_input),
        )
        await self.session_store.append(
            session_id,
            SessionMessage(role="assistant", content=final),
        )
        memory_text = self.memory_policy.prepare_dialogue_memory(user_input, final)
        if memory_text:
            await self.memory_store.add(
                memory_text,
                metadata={
                    "agent": self.config.name,
                    "kind": "dialogue",
                    "session_id": session_id,
                },
            )
        payload = metrics.finish_payload()
        metrics.event(
            "run_finished",
            duration_ms=payload["duration_ms"],
            tool_calls=payload["tool_calls"],
            llm_calls=payload["llm_calls"],
            iterations=iterations,
        )
        return AgentResult(final=final, messages=messages, iterations=iterations, metrics=payload)

    @staticmethod
    def _normalize_tool_call(call: Any) -> dict[str, Any]:
        if isinstance(call, dict):
            function = call["function"]
            raw_arguments = function.get("arguments") or "{}"
            return {
                "id": call["id"],
                "name": function["name"],
                "arguments": json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments,
            }
        function = call.function
        raw_arguments = function.arguments or "{}"
        return {
            "id": call.id,
            "name": function.name,
            "arguments": json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments,
        }

    @classmethod
    def _serialize_tool_calls(cls, tool_calls: Any) -> list[dict[str, Any]]:
        serialized: list[dict[str, Any]] = []
        for call in tool_calls:
            normalized = cls._normalize_tool_call(call)
            serialized.append(
                {
                    "id": normalized["id"],
                    "type": "function",
                    "function": {
                        "name": normalized["name"],
                        "arguments": json.dumps(normalized["arguments"], ensure_ascii=False),
                    },
                }
            )
        return serialized
