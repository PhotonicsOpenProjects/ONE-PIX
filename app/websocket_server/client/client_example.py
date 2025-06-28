from onepix_client import OnePixClient

client = OnePixClient("http://localhost:5000")
client.connect()

client.change_param("imaging_method", "FourierSplit")
width = client.read_param("max_width")
print("Largeur image :", width)

result = client.run_measure()
print("Résultat brut :", result)

client.disconnect()
