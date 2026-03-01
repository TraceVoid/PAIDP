from kafka import KafkaConsumer, KafkaProducer
import json
import joblib

model = joblib.load("model_nlp.pkl")
vectorizer = joblib.load("vectorizer.pkl")

consumer = KafkaConsumer(
    "incoming_messages",
    bootstrap_servers='kafka:9092',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

producer = KafkaProducer(
    bootstrap_servers='kafka:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def predict(text):
    X = vectorizer.transform([text])
    prob = model.predict_proba(X)[0][1]
    return prob

for message in consumer:
    data = message.value
    score = predict(data["text"])
    
    producer.send("ai_scores", {
        "text": data["text"],
        "score": score
    })
    producer.flush()
