from abc import ABC
from typing import List, Dict

from rai.agentic.ai_tools.image_tools.r_tools import rImageTools
from rai.agentic.ai_tools.text_tools.r_tools import rTextTools
from rai.assistant.connectors import rAI
from rai.ingest.utilities.TextUtils import TextProcessor


from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Any
import uuid



class RaiGentData(BaseModel):
    text: Optional[str] = None
    image: Optional[str] = None
    audio: Optional[str] = None
    video: Optional[str] = None


class RaiGentResults(BaseModel):
    text: Optional[Any] = None
    image: Optional[Any] = None
    audio: Optional[Any] = None
    video: Optional[Any] = None


class RaiGent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent: str
    user_prompt: Optional[str] = None
    system_prompt: Optional[str] = None
    data: RaiGentData = Field(default_factory=RaiGentData)
    runs: int = 1
    output: str = "append"  # e.g., "append" or "overwrite"
    date_added: datetime = Field(default_factory=datetime.utcnow)
    date_run: Optional[datetime] = None
    results: Optional[RaiGentResults] = None



class RaiAgentQueue(ABC, rAI, TextProcessor):
    def __init__(self):
        super().__init__()
        self.pending: List[RaiGent] = []
        # Registries to store agent configurations and results by agent ID
        self.agents: Dict[str, RaiGent] = {}
        self.text_results: Dict[str, Any] = {}
        self.image_results: Dict[str, Any] = {}
        self.audio_results: Dict[str, Any] = {}
        self.video_results: Dict[str, Any] = {}

    @classmethod
    def execute(cls, raigent: RaiGent):
        instance = cls()
        instance.run(raigent)
        return instance.get_results(raigent.id)

    def add_to_queue(self, raigent: RaiGent):
        self.pending.append(raigent)

    def process_queue(self):
        while self.pending:
            config = self.pending.pop(0)
            self.run(config)

    def run(self, raigent: RaiGent):
        """
        Execute the agent for the given configuration and organize the results by its ID.
        """
        agent_id = raigent.id
        agent_name = raigent.agent
        user_prompt = raigent.user_prompt
        system_prompt = raigent.system_prompt

        # Register the agent configuration
        self.agents[agent_id] = raigent

        # Process text if a prompt is provided
        if user_prompt is not None:
            responses = []
            for _ in range(raigent.runs):
                response = self.text(name=agent_name, user_prompt=user_prompt, system_prompt=system_prompt)
                responses.append(response)
            if raigent.output == "append":
                self.text_results.setdefault(agent_id, []).extend(responses)
            else:
                self.text_results[agent_id] = responses[-1]

        # Process image if image data is provided
        if raigent.data.image is not None:
            responses = []
            for _ in range(raigent.runs):
                response = self.image(name=agent_name, image=raigent.data.image)
                responses.append(response)
            if raigent.output == "append":
                self.image_results.setdefault(agent_id, []).extend(responses)
            else:
                self.image_results[agent_id] = responses[-1]

        # Process audio if audio data is provided (placeholder implementation)
        if raigent.data.audio is not None:
            responses = []
            for _ in range(raigent.runs):
                response = self.audio(name=agent_name, audio=raigent.data.audio)
                responses.append(response)
            if raigent.output == "append":
                self.audio_results.setdefault(agent_id, []).extend(responses)
            else:
                self.audio_results[agent_id] = responses[-1]

        # Process video if video data is provided (placeholder implementation)
        if raigent.data.video is not None:
            responses = []
            for _ in range(raigent.runs):
                response = self.video(name=agent_name, video=raigent.data.video)
                responses.append(response)
            if raigent.output == "append":
                self.video_results.setdefault(agent_id, []).extend(responses)
            else:
                self.video_results[agent_id] = responses[-1]

    @staticmethod
    def text(name: str, user_prompt: str, system_prompt: str):
        return rTextTools.tool(name=name, user_prompt=user_prompt, system_prompt=system_prompt)

    @staticmethod
    def image(name: str, image: str):
        return rImageTools.tool(name=name, image=image)

    @staticmethod
    def audio(name: str, audio: str):
        raise NotImplementedError("Audio agent integration not implemented.")

    @staticmethod
    def video(name: str, video: str):
        raise NotImplementedError("Video agent integration not implemented.")

    def get_results(self, agent_id: str) -> Dict[str, Any]:
        return {
            "text": self.text_results.get(agent_id),
            "image": self.image_results.get(agent_id),
            "audio": self.audio_results.get(agent_id),
            "video": self.video_results.get(agent_id),
        }


# ------------------------------------------------------------------
# New Class: RaiAgentQueueRedis
# ------------------------------------------------------------------
class RaiAgentQueueRedis(RaiAgentQueue):
    use_redis: bool = False
    redis_db: int = 0
    queue_name: str = "rai_agent_queue"

    def setup_cache(self):
        self.use_redis = True
        self.redis_cache = None
        if self.use_redis:
            try:
                # Initialize the Redis extension client.
                self.redis_cache = PluginAgentCache(db=self.redis_db, queue_name=self.queue_name)
                if not self.redis_cache.is_redis_available():
                    print("Redis not available; falling back to local queue only.")
                    self.redis_cache = None
            except Exception as e:
                print("Error initializing Redis client; falling back to local queue only:", e)
                self.redis_cache = None

    def _serialize_config(self, raigent: RaiGent) -> dict:
        """Convert a RaiGent instance to a serializable dictionary."""
        return {
            'id': raigent.id,
            'agent': raigent.agent,
            'user_prompt': raigent.user_prompt,
            'system_prompt': raigent.system_prompt,
            'runs': raigent.runs,
            'output': raigent.output,
            'data': {
                'text': raigent.data.text,
                'image': raigent.data.image,
                'audio': raigent.data.audio,
                'video': raigent.data.video,
            }
        }

    def _deserialize_config(self, data: dict) -> RaiGent:
        """Reconstruct a RaiGent instance from its dictionary representation."""
        data_obj = RaiGentData(
            text=data.get('data', {}).get('text'),
            image=data.get('data', {}).get('image'),
            audio=data.get('data', {}).get('audio'),
            video=data.get('data', {}).get('video')
        )
        return RaiGent(
            agent=data.get('agent'),
            user_prompt=data.get('user_prompt'),
            system_prompt=data.get('system_prompt'),
            data=data_obj,
            runs=data.get('runs', 1),
            output=data.get('output', "append"),
            id=data.get('id')
        )

    def add_to_queue(self, raigent: RaiGent):
        """Add a configuration to both local and Redis queues."""
        # Add to the local pending queue.
        super().add_to_queue(raigent)
        # Also push to the Redis queue if available.
        if self.redis_cache and self.redis_cache.is_redis_available():
            try:
                config_dict = self._serialize_config(raigent)
                self.redis_cache.add_agent_config_to_queue(config_dict)
            except Exception as e:
                print("Failed to add config to Redis queue:", e)

    def process_queue(self):
        """Process agent configurations from the Redis queue (if available) then local queue."""
        # First, process any configs from the Redis queue.
        if self.redis_cache and self.redis_cache.is_redis_available():
            while True:
                config = self.redis_cache.pop_agent_config_from_queue()
                if config is None:
                    break
                try:
                    raigent = self._deserialize_config(config)
                    self.run(raigent)
                except Exception as e:
                    print("Error processing config from Redis queue:", e)
        # Next, process any local pending configurations.
        super().process_queue()

    def cache_response(self, agent_id, agent_type, responses):
        # Cache the text responses in Redis.
        if self.redis_cache and self.redis_cache.is_redis_available():
            for response in responses:
                self.redis_cache.cache_agent_response(agent_id, agent_type, response)

    def run(self, raigent: RaiGent):
        """
        Execute the agent for the given configuration,
        cache its responses in Redis (if available), and organize the results.
        """
        agent_id = raigent.id
        agent_name = raigent.agent
        user_prompt = raigent.user_prompt
        system_prompt = raigent.system_prompt

        # Register the agent configuration.
        self.agents[agent_id] = raigent

        # Process text if a prompt is provided.
        if user_prompt is not None:
            responses = []
            for _ in range(raigent.runs):
                response = self.text(name=agent_name, user_prompt=user_prompt, system_prompt=system_prompt)
                responses.append(response)
            if raigent.output == "append":
                self.text_results.setdefault(agent_id, []).extend(responses)
            else:
                self.text_results[agent_id] = responses[-1]
            self.cache_response(agent_id, "text", responses)

        # Process image if image data is provided.
        if raigent.data.image is not None:
            responses = []
            for _ in range(raigent.runs):
                response = self.image(name=agent_name, image=raigent.data.image)
                responses.append(response)
            if raigent.output == "append":
                self.image_results.setdefault(agent_id, []).extend(responses)
            else:
                self.image_results[agent_id] = responses[-1]
            # Cache the image responses.
            self.cache_response(agent_id, "image", responses)

        # Process audio if audio data is provided (placeholder implementation).
        if raigent.data.audio is not None:
            responses = []
            for _ in range(raigent.runs):
                response = self.audio(name=agent_name, audio=raigent.data.audio)
                responses.append(response)
            if raigent.output == "append":
                self.audio_results.setdefault(agent_id, []).extend(responses)
            else:
                self.audio_results[agent_id] = responses[-1]
            # Cache audio responses.
            self.cache_response(agent_id, "audio", responses)

        # Process video if video data is provided (placeholder implementation).
        if raigent.data.video is not None:
            responses = []
            for _ in range(raigent.runs):
                response = self.video(name=agent_name, video=raigent.data.video)
                responses.append(response)
            if raigent.output == "append":
                self.video_results.setdefault(agent_id, []).extend(responses)
            else:
                self.video_results[agent_id] = responses[-1]
            # Cache video responses.
            self.cache_response(agent_id, "video", responses)