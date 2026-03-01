from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    "security_actions",
    bootstrap_servers='kafka:9092',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

for message in consumer:
    data = message.value
    
    if data["action"] == "block":
        print("Blocking threat:", data["text"])
    elif data["action"] == "alert":
        print("lerting user:", data["text"])
    else:
        print("Allowed:", data["text"])
