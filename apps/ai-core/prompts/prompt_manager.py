import yaml
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from models.chat import ChatMessage
import logging

logger = logging.getLogger(__name__)


class PromptManager:
    """
    Manages prompt templates with hot-reload support

    Loads prompts from YAML files and provides methods to build
    prompts with dynamic context injection.
    """

    def __init__(self, prompts_dir: Optional[str] = None):
        if prompts_dir is None:
            # Default to prompts/ directory in the same location as this file
            prompts_dir = Path(__file__).parent

        self.prompts_dir = Path(prompts_dir)
        self.cache: Dict[str, Dict[str, Any]] = {}
        logger.info(f"PromptManager initialized with directory: {self.prompts_dir}")

    def get_prompt_config(self, prompt_name: str) -> Dict[str, Any]:
        """
        Load prompt configuration from YAML file with hot-reload support

        Args:
            prompt_name: Name of the prompt file (without .yaml extension)

        Returns:
            Dictionary containing the prompt configuration
        """
        filepath = self.prompts_dir / f"{prompt_name}.yaml"

        if not filepath.exists():
            raise FileNotFoundError(f"Prompt file not found: {filepath}")

        # Get file modification time for hot-reload
        mtime = os.path.getmtime(filepath)

        cache_key = prompt_name

        # Check if we need to reload (file changed or not in cache)
        if cache_key not in self.cache or self.cache[cache_key].get('mtime') != mtime:
            logger.info(f"Loading/reloading prompt: {prompt_name}")
            with open(filepath, 'r') as f:
                config = yaml.safe_load(f)

            self.cache[cache_key] = {
                'data': config,
                'mtime': mtime
            }

        return self.cache[cache_key]['data']

    def build_mentor_chat_prompt(
        self,
        message: str,
        conversation_history: List[ChatMessage],
        context: Dict[str, Any]
    ) -> str:
        """
        Build the mentor chat prompt using the YAML configuration

        Args:
            message: User's current message
            conversation_history: List of previous messages
            context: Context dictionary with entities and relationships

        Returns:
            Complete prompt string ready for Claude
        """
        config = self.get_prompt_config("mentor_chat")

        sections = []

        # Add system role
        sections.append(config['system_role'])

        # Build context sections dynamically
        sections.extend(self._build_context_sections(config, context, conversation_history))

        # Add current message
        sections.append(f"\n{config['message_header']}")
        sections.append(message)

        # Add instructions
        if config.get('instructions'):
            sections.append("\nINSTRUCTIONS:")
            for i, instruction in enumerate(config['instructions'], 1):
                sections.append(f"{i}. {instruction}")

        # Add critical guidelines
        if config.get('critical_guidelines'):
            sections.append("\nCRITICAL:")
            for guideline in config['critical_guidelines']:
                sections.append(f"- {guideline}")

        # Add final instruction
        sections.append(f"\n{config['final_instruction']}")

        return "\n".join(sections)

    def _build_context_sections(
        self,
        config: Dict[str, Any],
        context: Dict[str, Any],
        conversation_history: List[ChatMessage]
    ) -> List[str]:
        """Build all context sections based on configuration"""
        sections = []
        context_configs = config.get('context_sections', {})

        # Core identity
        if self._is_section_enabled(context_configs, 'core_identity') and context.get('core_identity'):
            sections.append(self._build_core_identity(
                context['core_identity'],
                context_configs['core_identity']
            ))

        # High priority
        if self._is_section_enabled(context_configs, 'high_priority') and context.get('high_priority'):
            sections.append(self._build_high_priority(
                context['high_priority'],
                context_configs['high_priority']
            ))

        # Active work
        if self._is_section_enabled(context_configs, 'active_work') and context.get('active_work'):
            sections.append(self._build_active_work(
                context['active_work'],
                context_configs['active_work']
            ))

        # Relevant entities
        if self._is_section_enabled(context_configs, 'relevant_entities') and context.get('relevant_entities'):
            sections.append(self._build_relevant_entities(
                context['relevant_entities'],
                context_configs['relevant_entities']
            ))

        # Relationships
        if self._is_section_enabled(context_configs, 'relationships') and context.get('relationships'):
            sections.append(self._build_relationships(
                context['relationships'],
                context_configs['relationships']
            ))

        # Conversation history
        if self._is_section_enabled(context_configs, 'conversation_history') and conversation_history:
            sections.append(self._build_conversation_history(
                conversation_history,
                context_configs['conversation_history']
            ))

        return sections

    def _is_section_enabled(self, configs: Dict, section_name: str) -> bool:
        """Check if a section is enabled in config"""
        return configs.get(section_name, {}).get('enabled', False)

    def _build_core_identity(self, entities: List, config: Dict) -> str:
        """Build core identity section"""
        max_items = config.get('max_items', 5)
        header = config.get('header', 'Core Identity:')
        format_str = config.get('format', '- {title}: {summary}')

        lines = [header]
        for entity in entities[:max_items]:
            lines.append(format_str.format(
                title=entity.title,
                summary=entity.summary or 'N/A',
                type=entity.type
            ))

        return "\n".join(lines)

    def _build_high_priority(self, entities: List, config: Dict) -> str:
        """Build high priority section"""
        max_items = config.get('max_items', 5)
        header = config.get('header', 'High Priority:')
        format_str = config.get('format', '- {title} ({type}, importance: {importance:.2f})')

        lines = [header]
        for entity in entities[:max_items]:
            signal = entity.signal
            importance = signal.importance if signal else 0
            lines.append(format_str.format(
                title=entity.title,
                type=entity.type,
                importance=importance,
                summary=entity.summary or 'N/A'
            ))

        return "\n".join(lines)

    def _build_active_work(self, entities: List, config: Dict) -> str:
        """Build active work section"""
        max_items = config.get('max_items', 5)
        header = config.get('header', 'Active Work:')
        format_str = config.get('format', '- {title} ({type}, recency: {recency:.2f})')

        lines = [header]
        for entity in entities[:max_items]:
            signal = entity.signal
            recency = signal.recency if signal else 0
            lines.append(format_str.format(
                title=entity.title,
                type=entity.type,
                recency=recency,
                summary=entity.summary or 'N/A'
            ))

        return "\n".join(lines)

    def _build_relevant_entities(self, entities: List, config: Dict) -> str:
        """Build relevant entities section"""
        max_items = config.get('max_items', 10)
        header = config.get('header', 'Relevant Entities:')
        format_str = config.get('format', '- {title} ({type}): {summary}')

        lines = [header]
        for entity in entities[:max_items]:
            lines.append(format_str.format(
                title=entity.title,
                type=entity.type,
                summary=entity.summary or 'N/A'
            ))

        return "\n".join(lines)

    def _build_relationships(self, relationships: List, config: Dict) -> str:
        """Build relationships section"""
        max_items = config.get('max_items', 8)
        header = config.get('header', 'Relationships:')
        format_str = config.get('format', '- {from_title} --[{edge_kind}]--> {to_title}')

        lines = [header]
        for rel in relationships[:max_items]:
            edge_kind = rel["edge"].kind if hasattr(rel["edge"], "kind") else "relates_to"
            from_title = rel["from"].title if hasattr(rel["from"], "title") else rel["from"]["title"]
            to_title = rel["to"].title if hasattr(rel["to"], "title") else rel["to"]["title"]
            lines.append(format_str.format(
                from_title=from_title,
                edge_kind=edge_kind,
                to_title=to_title
            ))

        return "\n".join(lines)

    def _build_conversation_history(self, history: List[ChatMessage], config: Dict) -> str:
        """Build conversation history section"""
        max_items = config.get('max_items', 5)
        header = config.get('header', 'Conversation History:')
        format_str = config.get('format', '{role_label}: {content}')

        lines = [header]
        for msg in history[-max_items:]:
            role_label = "User" if msg.role == "user" else "Mentor"
            lines.append(format_str.format(
                role_label=role_label,
                content=msg.content,
                role=msg.role
            ))

        return "\n".join(lines)


# Singleton instance
prompt_manager = PromptManager()
