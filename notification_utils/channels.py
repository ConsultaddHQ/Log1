"""Notification channels for django-notifs."""

import pika
import json
from notifications.channels import BaseNotificationChannel


class BroadCastWebSocketChannel(BaseNotificationChannel):
    """Fan-out notification for RabbitMQ."""

    def _connect(self):
        """Connect to the RabbitMQ server."""
        credentials = pika.PlainCredentials('guest', 'guest')
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost', credentials=credentials, port=5672)
        )
        channel = connection.channel()
        return connection, channel

    def construct_message(self):
        """Construct the message to be sent."""
        extra_data = self.notification_kwargs['extra_data']

        return json.dumps(extra_data['message'])

    def notify(self, message):
        """put the message of the RabbitMQ queue."""
        connection, channel = self._connect()
        uri = self.notification_kwargs['extra_data']['uri']
        channel.exchange_declare(exchange=str(uri), exchange_type='fanout')
        channel.basic_publish(exchange=str(uri), routing_key='', body=message)
        connection.close()
