"""Twitter/X adapter for text and media publishing."""
import copy
from .base_adapter import BaseAdapter, Content, ContentType, PublishResult, Analytics


class TwitterAdapter(BaseAdapter):
    """Adapter for Twitter/X publishing."""

    platform = "twitter"
    content_types = [ContentType.TEXT, ContentType.VIDEO, ContentType.IMAGE]

    # Platform constraints
    MAX_TWEET_LENGTH = 280
    MAX_THREAD_LENGTH = 25
    MAX_VIDEO_DURATION = 140  # seconds

    async def authenticate(self) -> bool:
        """Authenticate with Twitter API."""
        # TODO: Implement with tweepy
        raise NotImplementedError("Twitter authentication not yet implemented")

    def adapt_content(self, content: Content) -> Content:
        """Adapt content for Twitter requirements."""
        content = copy.deepcopy(content)
        # Convert long text to thread
        if content.type == ContentType.TEXT and len(content.body) > self.MAX_TWEET_LENGTH:
            content.metadata = content.metadata or {}
            content.metadata["thread"] = self._split_into_thread(content.body)

        return content

    def _split_into_thread(self, text: str) -> list[str]:
        """Split long text into tweet-sized chunks."""
        tweets = []
        words = text.split()
        current_tweet = ""

        for word in words:
            # Reserve 5 chars for numbering (1/10)
            if len(current_tweet) + len(word) + 1 <= self.MAX_TWEET_LENGTH - 6:
                current_tweet += (" " if current_tweet else "") + word
            else:
                if current_tweet:
                    tweets.append(current_tweet)
                current_tweet = word

        if current_tweet:
            tweets.append(current_tweet)

        # Add numbering
        total = len(tweets)
        if total > 1:
            tweets = [f"{t} ({i+1}/{total})" for i, t in enumerate(tweets)]

        return tweets[:self.MAX_THREAD_LENGTH]

    def validate_content(self, content: Content) -> tuple[bool, list[str]]:
        """Validate content meets Twitter requirements."""
        errors = []

        if content.type == ContentType.VIDEO:
            # Would check video duration here
            pass

        if content.type == ContentType.TEXT:
            thread = content.metadata.get("thread") if content.metadata else None
            if not thread and len(content.body) > self.MAX_TWEET_LENGTH:
                errors.append(f"Tweet exceeds {self.MAX_TWEET_LENGTH} chars and wasn't split")

        return (len(errors) == 0, errors)

    async def publish(self, content: Content) -> PublishResult:
        """Publish to Twitter."""
        # TODO: Implement with tweepy
        # content = await self.pre_publish(content)
        # content = self.adapt_content(content)
        #
        # if content.metadata and "thread" in content.metadata:
        #     # Post as thread
        #     previous_id = None
        #     for tweet in content.metadata["thread"]:
        #         response = self.client.create_tweet(text=tweet, in_reply_to_tweet_id=previous_id)
        #         previous_id = response.data["id"]
        raise NotImplementedError("Twitter publishing not yet implemented")

    async def get_analytics(self, content_id: str) -> Analytics:
        """Fetch Twitter analytics for a tweet."""
        # TODO: Implement with Twitter API
        raise NotImplementedError("Twitter analytics not yet implemented")
