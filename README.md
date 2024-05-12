Meshtastic MQTT data visualisation.

This python script uses MQTT client to subscribe to MQTT output from Meshtatstic node 
The node is configued to publish data to a local broker - 192.168.0.251
When a packet received from radio it is published over MQTT in JSON format. 
The script categorises the packet by type and the submits the data to Influx DB online database.
Once the data in Influx DB it can be used by visualisation platforms ,, such as Grafana for visualising the data.
Examples of visualistion.
RSSI and SNR view. Shows every packets received (a coloured  dot) and its RSSI and SNR.

![image](https://github.com/slash-bit/meshtastic-mqtt-json-visualisation/assets/77391720/922a709c-913b-48d7-9caa-237e5bb0bcdf)
Visualisation by Packet Type. Show Bar chart of hourly received packets by their type.
![image](https://github.com/slash-bit/meshtastic-mqtt-json-visualisation/assets/77391720/5d182c57-70fc-4c11-bf0e-62aae4c80b17)
Time lime of packets received by each node, with their RSSI value
![image](https://github.com/slash-bit/meshtastic-mqtt-json-visualisation/assets/77391720/afc92cf2-870c-45df-b52f-bba60f52a93c)
