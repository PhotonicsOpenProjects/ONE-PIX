from onepix_client import OnePixClient

client = OnePixClient("http://localhost:5000")
client.connect()

client.change_param("imaging_method", "FourierSplit")
spectro_scans2avg = client.read_param("spectro_scans2avg")
print("Largeur image :", spectro_scans2avg)

result = client.run_measure()
#print("Résultat brut :", result)

client.disconnect()
