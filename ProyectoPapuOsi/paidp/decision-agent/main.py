from kafka import KafkaConsumer, KafkaProducer
import json

consumer = KafkaConsumer(
    "ai_scores",
    bootstrap_servers='kafka:9092',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

producer = KafkaProducer(
    bootstrap_servers='kafka:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def decide(score):
    if score > 0.7:
        return "block"
    elif score > 0.4:
        return "alert"
    else:
        return "allow"

for message in consumer:
    data = message.value
    action = decide(data["score"])
    
    producer.send("security_actions", {
        "text": data["text"],
        "score": data["score"],
        "action": action
    })
    producer.flush()
