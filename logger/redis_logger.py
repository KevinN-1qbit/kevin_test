import logging


class RedisHandler(logging.Handler):
    def __init__(self, redis_client, redis_topic, ttl_seconds=None):
        super().__init__()
        self.redis_client = redis_client
        self.redis_topic = redis_topic
        self.ttl_seconds = ttl_seconds

        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(funcName)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.setFormatter(formatter)
        self.level = logging.DEBUG

    def emit(self, record):
        log_message = self.format(record)
        self.redis_client.rpush(self.redis_topic, log_message)

        # Get the current time to live of the redis topic
        current_ttl = self.redis_client.ttl(self.redis_topic)
        if current_ttl == -1:
            # The key does not have a time to live
            if self.ttl_seconds is not None:
                set_ttl = self.redis_client.expire(self.redis_topic, self.ttl_seconds)
                if not set_ttl:
                    logging.error("Failed to set the time to live of the redis topic.")
                else:
                    logging.debug(
                        f"Successfully set the time to live of the redis topic: "
                        f"{self.redis_topic} to {self.ttl_seconds} seconds."
                    )
            else:
                logging.error("Can not set topic's time to live to none.")