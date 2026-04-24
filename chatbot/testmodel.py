from google import genai

client = genai.Client(api_key="AIzaSyCiiJ2ui7BFamR1s-X3Oub-QhizdpMU-OI")

models = client.models.list()

for m in models:
    print(m.name)

    #CHECK AVAILABLE MODELS